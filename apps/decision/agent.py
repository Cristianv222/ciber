"""Agente SPADE de decisión.

Recibe alertas de amenaza del DetectorAgent por XMPP, calcula la severidad
CVSS v4.0, actualiza `cvss_score` vía la API REST y, si la puntuación supera el
umbral configurado, ordena el bloqueo al ResponseAgent."""

import asyncio
import json
import logging

from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.message import Message

from cvss_calc import compute_cvss
from api import ApiClient

log = logging.getLogger("decision.agent")


class DecisionAgent(Agent):
    def __init__(self, jid, password, *, config, **kwargs):
        super().__init__(jid, password, **kwargs)
        self.config = config

    async def setup(self):
        c = self.config
        self.api = ApiClient(c["api_base_url"])
        self.response_jid = c["response_jid"]
        self.block_threshold = c["block_threshold"]
        self.add_behaviour(self.EvaluateBehaviour())
        await self.web.start(hostname="0.0.0.0", port=c["web_port"])
        log.info("DecisionAgent listo. Umbral de bloqueo CVSS>=%.1f, órdenes → %s. Web en :%s",
                 self.block_threshold, self.response_jid, c["web_port"])

    async def stop(self):
        try:
            if getattr(self, "api", None):
                self.api.close()
        finally:
            await super().stop()

    class EvaluateBehaviour(CyclicBehaviour):
        async def run(self):
            msg = await self.receive(timeout=10)
            if not msg:
                return
            try:
                data = json.loads(msg.body)
            except (ValueError, TypeError):
                log.warning("Alerta con cuerpo no-JSON, ignorada: %s", msg.body[:120])
                return

            flow_id = data.get("flow_id")
            attack_type = data.get("attack_type") or "unknown"
            score, vector = compute_cvss(attack_type)
            log.info("Flujo %s (%s): CVSS v4.0 = %.1f", flow_id, attack_type, score)

            if flow_id is not None:
                await asyncio.to_thread(self.agent.api.patch_flow, flow_id,
                                        {"cvss_score": score})

            if score >= self.agent.block_threshold:
                await self._order_block(data, score, vector)
            else:
                log.info("Flujo %s por debajo del umbral (%.1f < %.1f): sin bloqueo",
                         flow_id, score, self.agent.block_threshold)

        async def _order_block(self, data, score, vector):
            msg = Message(to=self.agent.response_jid)
            msg.set_metadata("performative", "request")
            msg.set_metadata("ontology", "block_order")
            msg.body = json.dumps({
                "flow_id": data.get("flow_id"),
                "src_ip": data.get("src_ip"),
                "dst_ip": data.get("dst_ip"),
                "src_port": data.get("src_port"),
                "dst_port": data.get("dst_port"),
                "protocol": data.get("protocol"),
                "attack_type": data.get("attack_type"),
                "cvss_score": score,
                "cvss_vector": vector,
            })
            await self.send(msg)
            log.warning("ORDEN DE BLOQUEO enviada para %s (CVSS %.1f)",
                        data.get("src_ip"), score)
