"""Agente SPADE de respuesta.

Recibe órdenes de bloqueo del DecisionAgent por XMPP, aplica la regla iptables
(respetando DRY_RUN en local) y registra `action_taken` vía la API REST."""

import asyncio
import json
import logging

from spade.agent import Agent
from spade.behaviour import CyclicBehaviour

from firewall import apply_block
from api import ApiClient

log = logging.getLogger("response.agent")


class ResponseAgent(Agent):
    def __init__(self, jid, password, *, config, **kwargs):
        super().__init__(jid, password, **kwargs)
        self.config = config

    async def setup(self):
        c = self.config
        self.api = ApiClient(c["api_base_url"])
        self.dry_run = c["dry_run"]
        self.add_behaviour(self.MitigateBehaviour())
        await self.web.start(hostname="0.0.0.0", port=c["web_port"])
        log.info("ResponseAgent listo. DRY_RUN=%s. Web en :%s", self.dry_run, c["web_port"])

    async def stop(self):
        try:
            if getattr(self, "api", None):
                self.api.close()
        finally:
            await super().stop()

    class MitigateBehaviour(CyclicBehaviour):
        async def run(self):
            msg = await self.receive(timeout=10)
            if not msg:
                return
            try:
                data = json.loads(msg.body)
            except (ValueError, TypeError):
                log.warning("Orden con cuerpo no-JSON, ignorada: %s", msg.body[:120])
                return

            flow_id = data.get("flow_id")
            ip = data.get("src_ip")
            if not ip:
                log.warning("Orden sin src_ip (flujo %s), ignorada", flow_id)
                return

            try:
                action = await asyncio.to_thread(apply_block, ip, self.agent.dry_run)
            except ValueError:
                action = f"IP inválida, sin acción: {ip}"[:100]
                log.warning("IP inválida en orden de bloqueo: %s", ip)

            log.info("Flujo %s -> %s", flow_id, action)
            if flow_id is not None:
                await asyncio.to_thread(self.agent.api.patch_flow, flow_id,
                                        {"action_taken": action})
