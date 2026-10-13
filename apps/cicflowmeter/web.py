"""Extracción de navegación web SIN descifrar TLS.

- SNI del handshake TLS (HTTPS)  -> dominio
- Consultas DNS                  -> dominio
- Peticiones HTTP en claro       -> dominio (Host) + ruta + método

Deduplica por (origen, dominio) en una ventana corta para no inundar la BD, y
envía cada visita a la API (POST /api/web-visits/), que la retransmite por WebSocket.
"""

import logging
import time

from scapy.layers.inet import IP, TCP, UDP

try:
    from scapy.layers.inet6 import IPv6
except Exception:  # pragma: no cover
    IPv6 = None
try:
    from scapy.layers.dns import DNS
except Exception:  # pragma: no cover
    DNS = None

log = logging.getLogger("cicflowmeter.web")

_HTTP_METHODS = (b"GET ", b"POST ", b"PUT ", b"HEAD ", b"DELETE ", b"OPTIONS ", b"PATCH ")


def _ip_fields(pkt):
    if IP in pkt:
        return pkt[IP].src, pkt[IP].dst
    if IPv6 is not None and IPv6 in pkt:
        return pkt[IPv6].src, pkt[IPv6].dst
    return None, None


def parse_tls_sni(data):
    """Extrae el server_name (SNI) de un TLS ClientHello. Devuelve str o None."""
    try:
        if len(data) < 45 or data[0] != 0x16:   # 0x16 = handshake
            return None
        if data[5] != 0x01:                      # 0x01 = ClientHello
            return None
        idx = 43                                 # salta record(5)+hs(4)+ver(2)+random(32)
        sid_len = data[idx]; idx += 1 + sid_len
        cs_len = int.from_bytes(data[idx:idx + 2], "big"); idx += 2 + cs_len
        comp_len = data[idx]; idx += 1 + comp_len
        if idx + 2 > len(data):
            return None
        ext_total = int.from_bytes(data[idx:idx + 2], "big"); idx += 2
        end = min(len(data), idx + ext_total)
        while idx + 4 <= end:
            etype = int.from_bytes(data[idx:idx + 2], "big")
            elen = int.from_bytes(data[idx + 2:idx + 4], "big")
            idx += 4
            if etype == 0x0000:                  # server_name
                # server_name_list(2) + name_type(1) + name_len(2) + name
                p = idx + 2 + 1
                nlen = int.from_bytes(data[p:p + 2], "big"); p += 2
                host = data[p:p + nlen].decode("idna", "ignore") if nlen else None
                return host or None
            idx += elen
    except Exception:  # noqa: BLE001
        return None
    return None


def parse_http(data):
    """Extrae (método, ruta, host) de una petición HTTP en claro, o None."""
    try:
        if not data.startswith(_HTTP_METHODS):
            return None
        head = data[:2048].split(b"\r\n")
        request_line = head[0].split(b" ")
        if len(request_line) < 2:
            return None
        method = request_line[0].decode("ascii", "ignore")
        path = request_line[1].decode("ascii", "ignore")
        host = None
        for line in head[1:]:
            if line[:5].lower() == b"host:":
                host = line[5:].strip().decode("ascii", "ignore")
                break
        if not host:
            return None
        return method, path, host
    except Exception:  # noqa: BLE001
        return None


class WebExtractor:
    def __init__(self, sink, dedup_window=15.0):
        self.sink = sink
        self.window = dedup_window
        self._seen = {}
        self.emitted = 0

    def _should_emit(self, src, domain):
        key = (src, domain)
        now = time.time()
        last = self._seen.get(key, 0)
        if now - last < self.window:
            return False
        self._seen[key] = now
        if len(self._seen) > 50000:              # poda básica de memoria
            self._seen = {k: v for k, v in self._seen.items() if now - v < self.window}
        return True

    def process(self, pkt):
        src, dst = _ip_fields(pkt)
        if not src:
            return

        # DNS (consultas)
        if DNS is not None and UDP in pkt and pkt.haslayer(DNS):
            dns = pkt[DNS]
            if getattr(dns, "qr", 1) == 0 and dns.qdcount and dns.qd is not None:
                try:
                    domain = dns.qd.qname.decode("idna", "ignore").rstrip(".")
                except Exception:  # noqa: BLE001
                    domain = None
                if domain and self._should_emit(src, domain):
                    self._emit(src, dst, 53, "dns", domain, None, None)
            return

        if TCP not in pkt:
            return
        dport = int(pkt[TCP].dport)
        payload = bytes(pkt[TCP].payload)
        if not payload:
            return

        # HTTPS (SNI) en 443
        if dport == 443 or payload[:1] == b"\x16":
            domain = parse_tls_sni(payload)
            if domain and self._should_emit(src, domain):
                self._emit(src, dst, dport, "tls", domain, None, None)
            return

        # HTTP en claro
        if dport == 80 or payload.startswith(_HTTP_METHODS):
            parsed = parse_http(payload)
            if parsed:
                method, path, host = parsed
                if self._should_emit(src, host + path[:40]):
                    self._emit(src, dst, dport, "http", host, path, method)

    def _emit(self, src, dst, dport, source, domain, path, method):
        data = {
            "src_ip": src, "dst_ip": dst, "dst_port": dport,
            "source": source, "domain": domain[:255],
            "url_path": path, "method": method,
        }
        try:
            self.sink.write(data)
            self.emitted += 1
        except Exception as exc:  # noqa: BLE001
            log.debug("No se pudo enviar visita web: %s", exc)
