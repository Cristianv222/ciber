"""Punto de entrada del agente detector (Fase 3)."""

import logging
import os

import spade

from agent import DetectorAgent

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("detector")


def _env(name, default=None):
    v = os.environ.get(name)
    return v if v not in (None, "") else default


def _maybe_disable_tls():
    """Conecta en texto plano si XMPP_DISABLE_TLS está activo (ejabberd corre sin
    TLS en la red interna de Docker; el NIF fast_tls es inestable bajo emulación
    amd64 en Apple Silicon). En la U con amd64 nativo puede desactivarse."""
    if str(_env("XMPP_DISABLE_TLS", "true")).lower() in ("1", "true", "yes", "on"):
        import slixmpp
        _orig = slixmpp.ClientXMPP.connect

        def _connect(self, *a, **kw):
            kw.setdefault("disable_starttls", True)
            return _orig(self, *a, **kw)

        slixmpp.ClientXMPP.connect = _connect


def build_config():
    return {
        "models_dir": _env("MODELS_DIR", "/models"),
        "db_host": _env("POSTGRES_HOST", "postgres"),
        "db_port": _env("POSTGRES_PORT", "5432"),
        "db_name": _env("POSTGRES_DB", "netflows"),
        "db_user": _env("POSTGRES_USER", "tesis"),
        "db_password": _env("POSTGRES_PASSWORD", ""),
        "api_base_url": _env("API_BASE_URL", "http://backend:8000"),
        "decision_jid": _env("DECISION_JID", "decision@ejabberd"),
        "poll_interval": float(_env("POLL_INTERVAL", "5")),
        "batch_size": int(_env("BATCH_SIZE", "100")),
        "web_port": int(_env("WEB_PORT", "10000")),
        "thresholds": {
            "xgb_attack": float(_env("XGB_ATTACK_THRESHOLD", "0.6")),
            "xgb_benign": float(_env("XGB_BENIGN_THRESHOLD", "0.8")),
            "cnn": float(_env("CNN_THRESHOLD", "0.5")),
        },
    }


async def _main():
    jid = _env("DETECTOR_JID", "detector@ejabberd")
    password = _env("XMPP_DETECTOR_PASSWORD")
    if not password:
        raise SystemExit("Falta XMPP_DETECTOR_PASSWORD en el entorno")

    _maybe_disable_tls()
    agent = DetectorAgent(jid, password, config=build_config(), verify_security=False)
    await agent.start(auto_register=False)
    log.info("Detector conectado como %s", jid)
    await spade.wait_until_finished(agent)


if __name__ == "__main__":
    spade.run(_main())
