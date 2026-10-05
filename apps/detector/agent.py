"""Agente SPADE del detector.

Cada `POLL_INTERVAL` segundos: lee flujos sin clasificar de PostgreSQL, aplica la
cascada, escribe el veredicto vía la API REST y, si es amenaza, envía una alerta
XMPP al DecisionAgent."""

import asyncio
import json
import logging
from datetime import datetime, timezone

from spade.agent import Agent
from spade.behaviour import PeriodicBehaviour
from spade.message import Message

from classifier import Cascade
from db import FlowReader
from api import ApiClient

log = logging.getLogger("detector.agent")


class DetectorAgent(Agent):
    def __init__(self, jid, password, *, config, **kwargs):
        super().__init__(jid, password, **kwargs)
        self.config = config

    async def setup(self):
        c = self.config
        # Carga de modelos (falla rápido si faltan artefactos → revisar Fase 2)
        self.cascade = Cascade(c["models_dir"], c["thresholds"])
        self.reader = FlowReader(
            c["db_host"], c["db_port"], c["db_name"], c["db_user"], c["db_password"],
            feature_columns=self.cascade.features,
        )
        self.api = ApiClient(c["api_base_url"])
        self.decision_jid = c["decision_jid"]

        self.add_behaviour(self.DetectBehaviour(period=c["poll_interval"]))
        await self.web.start(hostname="0.0.0.0", port=c["web_port"])
        log.info("DetectorAgent listo. Poll cada %ss, lote=%s, alertas → %s. Web en :%s",
                 c["poll_interval"], c["batch_size"], self.decision_jid, c["web_port"])

    async def stop(self):
        try:
            if getattr(self, "reader", None):
                self.reader.close()
            if getattr(self, "api", None):
                self.api.close()
        finally:
            await super().stop()

    class DetectBehaviour(PeriodicBehaviour):
        async def run(self):
            agent = self.agent
            rows = await asyncio.to_thread(agent.reader.fetch_unlabeled,
                                           agent.config["batch_size"])
            if not rows:
                return

            threats = 0
            for flow_id, meta, feat in rows:
                verdict = agent.cascade.classify(feat)
                payload = {
                    "label": verdict["label"],
                    "attack_type": verdict["attack_type"],
                    "confidence": verdict["confidence"],
                    "detector_stage": verdict["detector_stage"],
                    "processed_at": datetime.now(timezone.utc).isoformat(),
                }
                ok = await asyncio.to_thread(agent.api.patch_flow, flow_id, payload)
                if ok and verdict["is_threat"]:
                    threats += 1
                    await self._alert_decision(flow_id, meta, verdict)

            log.info("Procesados %d flujos (%d amenazas).", len(rows), threats)

        async def _alert_decision(self, flow_id, meta, verdict):
            msg = Message(to=self.agent.decision_jid)
            msg.set_metadata("performative", "inform")
            msg.set_metadata("ontology", "threat_alert")
            msg.body = json.dumps({
                "flow_id": flow_id,
                "src_ip": str(meta.get("src_ip")),
                "src_port": meta.get("src_port"),
                "dst_ip": str(meta.get("dst_ip")),
                "dst_port": meta.get("dst_port"),
                "protocol": meta.get("protocol"),
                "attack_type": verdict["attack_type"],
                "confidence": verdict["confidence"],
                "detector_stage": verdict["detector_stage"],
            })
            await self.send(msg)
