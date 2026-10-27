"""Punto de entrada del agente de respuesta (Fase 5)."""

import logging
import os

import spade

from agent import ResponseAgent

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("response")


def _env(name, default=None):
    v = os.environ.get(name)
    return v if v not in (None, "") else default


def _bool(v):
    return str(v).strip().lower() in ("1", "true", "yes", "on")


def _maybe_disable_tls():
    import slixmpp
    _orig = slixmpp.ClientXMPP.connect

    def _connect(self, *a, **kw):
        host = kw.pop("host", None)
        port = kw.pop("port", 5222)
        address = kw.pop("address", None)
        if address is None and host is not None:
            address = (host, int(port) if port is not None else 5222)
        if _bool(_env("XMPP_DISABLE_TLS", "true")):
            kw["disable_starttls"] = True
            kw["use_ssl"] = False
        return _orig(self, address=address, *a, **kw)

    slixmpp.ClientXMPP.connect = _connect



def build_config():
    return {
        "api_base_url": _env("API_BASE_URL", "http://backend:8000"),
        "dry_run": _bool(_env("DRY_RUN", "true")),
        "web_port": int(_env("WEB_PORT", "10002")),
    }


async def _main():
    jid = _env("RESPONSE_JID", "response@ejabberd")
    password = _env("XMPP_RESPONSE_PASSWORD")
    if not password:
        raise SystemExit("Falta XMPP_RESPONSE_PASSWORD en el entorno")

    _maybe_disable_tls()
    agent = ResponseAgent(jid, password, config=build_config(), verify_security=False)
    await agent.start(auto_register=False)
    log.info("Response conectado como %s", jid)
    await spade.wait_until_finished(agent)


if __name__ == "__main__":
    spade.run(_main())
