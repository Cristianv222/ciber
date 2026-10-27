"""Punto de entrada del agente de decisión (Fase 4)."""

import logging
import os

import spade

from agent import DecisionAgent

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("decision")


def _env(name, default=None):
    v = os.environ.get(name)
    return v if v not in (None, "") else default


def _maybe_disable_tls():
    import slixmpp
    _orig = slixmpp.ClientXMPP.connect

    def _connect(self, *a, **kw):
        host = kw.pop("host", None)
        port = kw.pop("port", 5222)
        address = kw.pop("address", None)
        if address is None and host is not None:
            address = (host, int(port) if port is not None else 5222)
        if str(_env("XMPP_DISABLE_TLS", "true")).lower() in ("1", "true", "yes", "on"):
            kw["disable_starttls"] = True
            kw["use_ssl"] = False
        return _orig(self, address=address, *a, **kw)

    slixmpp.ClientXMPP.connect = _connect



def build_config():
    return {
        "api_base_url": _env("API_BASE_URL", "http://backend:8000"),
        "response_jid": _env("RESPONSE_JID", "response@ejabberd"),
        "block_threshold": float(_env("CVSS_BLOCK_THRESHOLD", "7.0")),
        "web_port": int(_env("WEB_PORT", "10001")),
    }


async def _main():
    jid = _env("DECISION_JID", "decision@ejabberd")
    password = _env("XMPP_DECISION_PASSWORD")
    if not password:
        raise SystemExit("Falta XMPP_DECISION_PASSWORD en el entorno")

    _maybe_disable_tls()
    agent = DecisionAgent(jid, password, config=build_config(), verify_security=False)
    await agent.start(auto_register=False)
    log.info("Decision conectado como %s", jid)
    await spade.wait_until_finished(agent)


if __name__ == "__main__":
    spade.run(_main())
