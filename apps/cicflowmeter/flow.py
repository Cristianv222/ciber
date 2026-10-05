"""Extracción de características de flujos de red al estilo CIC-IDS.

Agrupa paquetes en flujos bidireccionales (5-tupla) y calcula el mismo conjunto
de ~80 métricas que almacena la tabla `flows`. Los nombres de las claves del
diccionario devuelto por `Flow.get_data()` coinciden EXACTAMENTE con las columnas
de la tabla / el modelo Django, de modo que la inserción no necesita mapeos.

Convenciones (iguales a CICFlowMeter):
- Duraciones e IAT se expresan en microsegundos.
- "packet length" = longitud total del paquete IP.
- "segment size" (payload) = bytes por encima de la cabecera de transporte.
- Dirección FORWARD = la del primer paquete del flujo (iniciador).
"""

import statistics
from enum import Enum

from scapy.layers.inet import IP, TCP, UDP

try:  # IPv6 es opcional pero lo soportamos si está disponible
    from scapy.layers.inet6 import IPv6
except Exception:  # pragma: no cover
    IPv6 = None


# --- Umbrales (segundos) ---
ACTIVITY_TIMEOUT = 5.0   # separación que marca fin de una ráfaga activa / inicio de idle
CLUMP_TIMEOUT = 1.0      # separación máxima dentro de un "clump" para subflujos y bulk
BULK_BOUND = 4           # nº mínimo de paquetes seguidos para considerarse transferencia bulk


class Direction(Enum):
    FORWARD = 0
    BACKWARD = 1


def _mean(x):
    return float(statistics.fmean(x)) if x else 0.0


def _std(x):
    return float(statistics.pstdev(x)) if len(x) > 1 else 0.0


def _var(x):
    return float(statistics.pvariance(x)) if len(x) > 1 else 0.0


def _max(x):
    return float(max(x)) if x else 0.0


def _min(x):
    return float(min(x)) if x else 0.0


def parse_packet(pkt):
    """Extrae de un paquete scapy los campos que necesita el flujo.

    Devuelve un dict o None si el paquete no es IP + (TCP|UDP)."""
    if IP in pkt:
        ip = pkt[IP]
        src, dst, proto = ip.src, ip.dst, int(ip.proto)
        # ihl/len pueden venir sin calcular en paquetes construidos en memoria;
        # en capturas reales (pcap/interfaz) siempre están presentes.
        ip_hdr_len = int(ip.ihl) * 4 if ip.ihl is not None else 20
        total_len = int(ip.len) if ip.len is not None else len(bytes(ip))
    elif IPv6 is not None and IPv6 in pkt:
        ip6 = pkt[IPv6]
        src, dst, proto = ip6.src, ip6.dst, int(ip6.nh)
        plen = int(ip6.plen) if ip6.plen is not None else len(bytes(ip6.payload))
        ip_hdr_len, total_len = 40, plen + 40
    else:
        return None

    if TCP in pkt:
        t = pkt[TCP]
        sport, dport = int(t.sport), int(t.dport)
        transport_hdr_len = int(t.dataofs) * 4 if t.dataofs is not None else 20
        window = int(t.window)
        f = int(t.flags)
        flags = {
            'FIN': bool(f & 0x01), 'SYN': bool(f & 0x02), 'RST': bool(f & 0x04),
            'PSH': bool(f & 0x08), 'ACK': bool(f & 0x10), 'URG': bool(f & 0x20),
            'ECE': bool(f & 0x40), 'CWR': bool(f & 0x80),
        }
        payload_len = len(t.payload)
    elif UDP in pkt:
        u = pkt[UDP]
        sport, dport = int(u.sport), int(u.dport)
        transport_hdr_len = 8
        window = 0
        flags = {k: False for k in ('FIN', 'SYN', 'RST', 'PSH', 'ACK', 'URG', 'ECE', 'CWR')}
        payload_len = len(u.payload)
    else:
        return None

    return {
        'ts': float(pkt.time),
        'src': src, 'dst': dst, 'proto': proto,
        'sport': sport, 'dport': dport,
        'ip_len': total_len,
        'header_len': ip_hdr_len + transport_hdr_len,
        'payload_len': payload_len,
        'window': window,
        'flags': flags,
    }


def flow_key(p):
    """Clave canónica bidireccional (independiente del sentido)."""
    a = (p['src'], p['sport'])
    b = (p['dst'], p['dport'])
    lo, hi = sorted((a, b))
    return (p['proto'], lo, hi)


def _bulk_stats(payload_packets):
    """Estadísticas de transferencias 'bulk' en una dirección.

    payload_packets: lista ordenada de (ts_segundos, payload_bytes) con payload > 0.
    Sigue la heurística de CICFlowMeter: agrupa paquetes consecutivos separados
    por <= CLUMP_TIMEOUT; un grupo de >= BULK_BOUND paquetes cuenta como un bulk.
    Devuelve (avg_bytes_bulk, avg_packets_bulk, avg_bulk_rate)."""
    num_bulks = total_pkts = total_bytes = 0
    total_duration = 0.0
    i, n = 0, len(payload_packets)
    while i < n:
        j = i + 1
        while j < n and (payload_packets[j][0] - payload_packets[j - 1][0]) <= CLUMP_TIMEOUT:
            j += 1
        clump = payload_packets[i:j]
        if len(clump) >= BULK_BOUND:
            num_bulks += 1
            total_pkts += len(clump)
            total_bytes += sum(p[1] for p in clump)
            total_duration += (clump[-1][0] - clump[0][0])
        i = j
    if num_bulks == 0:
        return 0.0, 0.0, 0.0
    avg_bytes = total_bytes / num_bulks
    avg_pkts = total_pkts / num_bulks
    avg_rate = (total_bytes / total_duration) if total_duration > 0 else 0.0
    return avg_bytes, avg_pkts, avg_rate


class Flow:
    def __init__(self, first_packet):
        self.src_ip = first_packet['src']
        self.src_port = first_packet['sport']
        self.dst_ip = first_packet['dst']
        self.dst_port = first_packet['dport']
        self.protocol = first_packet['proto']

        self.start_ts = first_packet['ts']
        self.last_ts = first_packet['ts']

        # Timestamps por dirección y globales (para IAT, active/idle, subflow, bulk)
        self.all_ts = []
        self.fwd_ts = []
        self.bwd_ts = []

        # Longitudes de paquete (IP) por dirección
        self.fwd_lengths = []
        self.bwd_lengths = []

        # Cabeceras
        self.fwd_header_bytes = 0
        self.bwd_header_bytes = 0
        self.fwd_header_lengths = []  # para min_seg_size_forward

        # Payloads (segment sizes) para bulk / act_data_pkt
        self.fwd_payloads = []  # (ts, payload_len) con payload>0
        self.bwd_payloads = []
        self.act_data_pkt_fwd = 0

        # Ventanas iniciales
        self.init_win_fwd = None
        self.init_win_bwd = None

        # Flags por dirección
        self.fwd_psh = self.bwd_psh = 0
        self.fwd_urg = self.bwd_urg = 0

        # Conteos globales de flags
        self.flag_counts = {k: 0 for k in ('FIN', 'SYN', 'RST', 'PSH', 'ACK', 'URG', 'ECE', 'CWR')}

        # Estado de cierre
        self.fin_fwd = self.fin_bwd = False
        self.rst = False

    def direction_of(self, p):
        if p['src'] == self.src_ip and p['sport'] == self.src_port:
            return Direction.FORWARD
        return Direction.BACKWARD

    def add_packet(self, p):
        """Añade un paquete al flujo. Devuelve True si el flujo debe cerrarse."""
        d = self.direction_of(p)
        ts = p['ts']
        self.last_ts = ts
        self.all_ts.append(ts)

        for k, v in p['flags'].items():
            if v:
                self.flag_counts[k] += 1

        if d is Direction.FORWARD:
            self.fwd_ts.append(ts)
            self.fwd_lengths.append(p['ip_len'])
            self.fwd_header_bytes += p['header_len']
            self.fwd_header_lengths.append(p['header_len'])
            if self.init_win_fwd is None:
                self.init_win_fwd = p['window']
            if p['payload_len'] > 0:
                self.act_data_pkt_fwd += 1
                self.fwd_payloads.append((ts, p['payload_len']))
            if p['flags']['PSH']:
                self.fwd_psh += 1
            if p['flags']['URG']:
                self.fwd_urg += 1
            if p['flags']['FIN']:
                self.fin_fwd = True
        else:
            self.bwd_ts.append(ts)
            self.bwd_lengths.append(p['ip_len'])
            self.bwd_header_bytes += p['header_len']
            if self.init_win_bwd is None:
                self.init_win_bwd = p['window']
            if p['payload_len'] > 0:
                self.bwd_payloads.append((ts, p['payload_len']))
            if p['flags']['PSH']:
                self.bwd_psh += 1
            if p['flags']['URG']:
                self.bwd_urg += 1
            if p['flags']['FIN']:
                self.fin_bwd = True

        if p['flags']['RST']:
            self.rst = True

        return self.rst or (self.fin_fwd and self.fin_bwd)

    @staticmethod
    def _iat_us(timestamps):
        """Lista de tiempos entre arribos (microsegundos) de una serie ordenada."""
        return [(timestamps[i] - timestamps[i - 1]) * 1e6 for i in range(1, len(timestamps))]

    def _active_idle(self):
        ts = self.all_ts
        if len(ts) < 2:
            return [0.0], [0.0]
        active, idle = [], []
        burst_start = ts[0]
        prev = ts[0]
        for cur in ts[1:]:
            gap = cur - prev
            if gap > ACTIVITY_TIMEOUT:
                active.append((prev - burst_start) * 1e6)
                idle.append(gap * 1e6)
                burst_start = cur
            prev = cur
        active.append((prev - burst_start) * 1e6)
        return (active or [0.0]), (idle or [0.0])

    def _subflow_count(self):
        count = 1
        for i in range(1, len(self.all_ts)):
            if (self.all_ts[i] - self.all_ts[i - 1]) > CLUMP_TIMEOUT:
                count += 1
        return count

    def get_data(self):
        duration_s = max(self.last_ts - self.start_ts, 0.0)
        duration_us = duration_s * 1e6

        tot_fwd = len(self.fwd_lengths)
        tot_bwd = len(self.bwd_lengths)
        total_pkts = tot_fwd + tot_bwd
        totlen_fwd = sum(self.fwd_lengths)
        totlen_bwd = sum(self.bwd_lengths)
        total_bytes = totlen_fwd + totlen_bwd
        all_lengths = self.fwd_lengths + self.bwd_lengths

        flow_iat = self._iat_us(self.all_ts)
        fwd_iat = self._iat_us(self.fwd_ts)
        bwd_iat = self._iat_us(self.bwd_ts)
        active, idle = self._active_idle()
        subflows = self._subflow_count()

        f_bulk_bytes, f_bulk_pkts, f_bulk_rate = _bulk_stats(self.fwd_payloads)
        b_bulk_bytes, b_bulk_pkts, b_bulk_rate = _bulk_stats(self.bwd_payloads)

        rate = (lambda x: x / duration_s if duration_s > 0 else 0.0)

        return {
            'src_ip': self.src_ip,
            'src_port': self.src_port,
            'dst_ip': self.dst_ip,
            'dst_port': self.dst_port,
            'protocol': self.protocol,
            'label': 'unlabeled',

            'flow_duration': int(duration_us),
            'total_fwd_packets': tot_fwd,
            'total_bwd_packets': tot_bwd,
            'total_length_of_fwd_packets': totlen_fwd,
            'total_length_of_bwd_packets': totlen_bwd,

            'fwd_packet_length_max': _max(self.fwd_lengths),
            'fwd_packet_length_min': _min(self.fwd_lengths),
            'fwd_packet_length_mean': _mean(self.fwd_lengths),
            'fwd_packet_length_std': _std(self.fwd_lengths),

            'bwd_packet_length_max': _max(self.bwd_lengths),
            'bwd_packet_length_min': _min(self.bwd_lengths),
            'bwd_packet_length_mean': _mean(self.bwd_lengths),
            'bwd_packet_length_std': _std(self.bwd_lengths),

            'flow_bytes_s': rate(total_bytes),
            'flow_packets_s': rate(total_pkts),

            'flow_iat_mean': _mean(flow_iat),
            'flow_iat_std': _std(flow_iat),
            'flow_iat_max': _max(flow_iat),
            'flow_iat_min': _min(flow_iat),

            'fwd_iat_total': float(sum(fwd_iat)),
            'fwd_iat_mean': _mean(fwd_iat),
            'fwd_iat_std': _std(fwd_iat),
            'fwd_iat_max': _max(fwd_iat),
            'fwd_iat_min': _min(fwd_iat),

            'bwd_iat_total': float(sum(bwd_iat)),
            'bwd_iat_mean': _mean(bwd_iat),
            'bwd_iat_std': _std(bwd_iat),
            'bwd_iat_max': _max(bwd_iat),
            'bwd_iat_min': _min(bwd_iat),

            'fwd_psh_flags': self.fwd_psh,
            'bwd_psh_flags': self.bwd_psh,
            'fwd_urg_flags': self.fwd_urg,
            'bwd_urg_flags': self.bwd_urg,

            'fwd_header_length': self.fwd_header_bytes,
            'bwd_header_length': self.bwd_header_bytes,
            'fwd_packets_s': rate(tot_fwd),
            'bwd_packets_s': rate(tot_bwd),

            'min_packet_length': _min(all_lengths),
            'max_packet_length': _max(all_lengths),
            'packet_length_mean': _mean(all_lengths),
            'packet_length_std': _std(all_lengths),
            'packet_length_variance': _var(all_lengths),

            'fin_flag_count': self.flag_counts['FIN'],
            'syn_flag_count': self.flag_counts['SYN'],
            'rst_flag_count': self.flag_counts['RST'],
            'psh_flag_count': self.flag_counts['PSH'],
            'ack_flag_count': self.flag_counts['ACK'],
            'urg_flag_count': self.flag_counts['URG'],
            'ece_flag_count': self.flag_counts['ECE'],
            'cwr_flag_count': self.flag_counts['CWR'],

            'down_up_ratio': (tot_bwd / tot_fwd) if tot_fwd > 0 else 0.0,
            'average_packet_size': _mean(all_lengths),
            'avg_fwd_segment_size': _mean(self.fwd_lengths),
            'avg_bwd_segment_size': _mean(self.bwd_lengths),

            'fwd_avg_bytes_bulk': f_bulk_bytes,
            'fwd_avg_packets_bulk': f_bulk_pkts,
            'fwd_avg_bulk_rate': f_bulk_rate,
            'bwd_avg_bytes_bulk': b_bulk_bytes,
            'bwd_avg_packets_bulk': b_bulk_pkts,
            'bwd_avg_bulk_rate': b_bulk_rate,

            'subflow_fwd_packets': tot_fwd // subflows,
            'subflow_fwd_bytes': totlen_fwd // subflows,
            'subflow_bwd_packets': tot_bwd // subflows,
            'subflow_bwd_bytes': totlen_bwd // subflows,

            'init_win_bytes_forward': self.init_win_fwd if self.init_win_fwd is not None else 0,
            'init_win_bytes_backward': self.init_win_bwd if self.init_win_bwd is not None else 0,
            'act_data_pkt_fwd': self.act_data_pkt_fwd,
            'min_seg_size_forward': int(_min(self.fwd_header_lengths)),

            'active_mean': _mean(active),
            'active_std': _std(active),
            'active_max': _max(active),
            'active_min': _min(active),
            'idle_mean': _mean(idle),
            'idle_std': _std(idle),
            'idle_max': _max(idle),
            'idle_min': _min(idle),
        }
