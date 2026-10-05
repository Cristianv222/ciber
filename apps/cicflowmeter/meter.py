"""Gestor de sesiones de flujo: mantiene los flujos vivos, los cierra por
FIN/RST o por timeout, y entrega cada flujo terminado al sumidero."""

import logging

from flow import Flow, parse_packet, flow_key

log = logging.getLogger("cicflowmeter.meter")


class FlowMeter:
    def __init__(self, sink, flow_timeout=120.0, sweep_every=200):
        self.sink = sink
        self.flow_timeout = flow_timeout
        self.sweep_every = sweep_every
        self.flows = {}
        self._counter = 0
        self.exported = 0

    def process_packet(self, pkt):
        p = parse_packet(pkt)
        if p is None:
            return

        key = flow_key(p)
        flow = self.flows.get(key)
        if flow is None:
            flow = Flow(p)
            self.flows[key] = flow

        closed = flow.add_packet(p)
        if closed:
            self._export(key)

        # Barrido periódico de flujos expirados por inactividad (usa el reloj del
        # propio tráfico: p['ts']). Funciona igual en modo live y en modo pcap.
        self._counter += 1
        if self._counter % self.sweep_every == 0:
            self._expire(now=p['ts'])

    def _export(self, key):
        flow = self.flows.pop(key, None)
        if flow is None:
            return
        try:
            self.sink.write(flow.get_data())
            self.exported += 1
        except Exception as exc:  # noqa: BLE001
            log.warning("No se pudo exportar el flujo %s: %s", key, exc)

    def _expire(self, now):
        expired = [k for k, f in self.flows.items()
                   if (now - f.last_ts) > self.flow_timeout]
        for k in expired:
            self._export(k)

    def flush_all(self):
        """Exporta todos los flujos que queden abiertos (fin de pcap / apagado)."""
        for k in list(self.flows.keys()):
            self._export(k)
        log.info("Flujos exportados en total: %d", self.exported)
