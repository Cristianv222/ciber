"""Punto de entrada del módulo de ingesta (Capa 2).

Captura tráfico de una interfaz (SPAN, en la máquina de la U) o lee un archivo
.pcap (desarrollo local, p. ej. en Mac), extrae las ~80 características por flujo
y las escribe en la tabla `flows` vía la API REST o directamente en PostgreSQL.

Configuración por variables de entorno (con equivalentes por línea de comandos):
    CAPTURE_MODE      live | pcap            (--mode)
    SPAN_INTERFACE    interfaz a capturar    (--interface)
    PCAP_FILE         ruta al .pcap          (--pcap)
    INGEST_MODE       api | db               (--sink)
    API_BASE_URL      http://localhost:8000  (--api-url)
    POSTGRES_HOST/PORT/DB/USER/PASSWORD      (para --sink db)
    FLOW_TIMEOUT      segundos (def. 120)
    ACTIVITY_TIMEOUT  segundos (def. 5)

Ejemplos:
    # Desarrollo local sobre un pcap, escribiendo vía API (WebSocket en vivo):
    python main.py --mode pcap --pcap /data/pcap/muestra.pcap --sink api

    # En la U, capturando el puerto SPAN e insertando directo en BD:
    CAPTURE_MODE=live SPAN_INTERFACE=eth1 INGEST_MODE=db python main.py
"""

import argparse
import logging
import os
import signal
import sys

import flow as flow_mod
from meter import FlowMeter
from sinks import build_sink

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("cicflowmeter")


def _env(name, default=None):
    v = os.environ.get(name)
    return v if v not in (None, "") else default


def parse_args():
    p = argparse.ArgumentParser(description="Ingesta de flujos estilo CIC-IDS")
    p.add_argument("--mode", default=_env("CAPTURE_MODE", "live"),
                   choices=["live", "pcap"])
    p.add_argument("--interface", default=_env("SPAN_INTERFACE", "eth0"))
    p.add_argument("--pcap", default=_env("PCAP_FILE"))
    p.add_argument("--sink", default=_env("INGEST_MODE", "api"),
                   choices=["api", "db"])
    p.add_argument("--api-url", default=_env("API_BASE_URL", "http://localhost:8000"))
    p.add_argument("--flow-timeout", type=float,
                   default=float(_env("FLOW_TIMEOUT", "120")))
    p.add_argument("--activity-timeout", type=float,
                   default=float(_env("ACTIVITY_TIMEOUT", "5")))
    return p.parse_args()


def build_sink_cfg(args):
    return {
        "api_base_url": args.api_url,
        "db_host": _env("POSTGRES_HOST", "localhost"),
        "db_port": _env("POSTGRES_PORT", "5432"),
        "db_name": _env("POSTGRES_DB", "netflows"),
        "db_user": _env("POSTGRES_USER", "tesis"),
        "db_password": _env("POSTGRES_PASSWORD", ""),
    }


def run_pcap(handle, path):
    from scapy.utils import PcapReader
    if not path or not os.path.exists(path):
        log.error("Archivo pcap no encontrado: %s", path)
        sys.exit(1)
    log.info("Leyendo pcap: %s", path)
    with PcapReader(path) as reader:
        for pkt in reader:
            handle(pkt)


def run_live(handle, iface):
    from scapy.sendrecv import sniff
    log.info("Capturando en la interfaz: %s (Ctrl+C para detener)", iface)
    sniff(iface=iface, prn=handle, store=False)


def main():
    args = parse_args()

    # Propaga el umbral de actividad al módulo de features
    flow_mod.ACTIVITY_TIMEOUT = args.activity_timeout

    sink = build_sink(args.sink, build_sink_cfg(args))
    meter = FlowMeter(sink, flow_timeout=args.flow_timeout)

    # Captura de navegación web (SNI/DNS/HTTP) — opcional
    web_extractor = None
    web_sink = None
    if _env("WEB_CAPTURE", "true").lower() in ("1", "true", "yes", "on"):
        from web import WebExtractor
        from sinks import WebApiSink
        web_sink = WebApiSink(_env("API_BASE_URL", "http://localhost:8000"))
        web_extractor = WebExtractor(web_sink, dedup_window=float(_env("WEB_DEDUP_WINDOW", "15")))
        log.info("Captura de navegación web activada (SNI/DNS/HTTP).")

    def handle(pkt):
        meter.process_packet(pkt)
        if web_extractor is not None:
            web_extractor.process(pkt)

    def _shutdown(signum, frame):
        log.info("Señal recibida, vaciando flujos pendientes…")
        meter.flush_all()
        sink.close()
        if web_sink:
            web_sink.close()
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    try:
        if args.mode == "pcap":
            run_pcap(handle, args.pcap)
        else:
            run_live(handle, args.interface)
    finally:
        meter.flush_all()
        sink.close()
        if web_sink:
            web_sink.close()


if __name__ == "__main__":
    main()
