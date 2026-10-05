"""Escritura vía la API REST del backend (PATCH /api/flows/{id}/)."""

import logging

import requests

log = logging.getLogger("response.api")


class ApiClient:
    def __init__(self, base_url, timeout=5.0):
        self.base = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()

    def patch_flow(self, flow_id, payload):
        url = f"{self.base}/api/flows/{flow_id}/"
        try:
            r = self.session.patch(url, json=payload, timeout=self.timeout)
            if r.status_code >= 400:
                log.warning("API rechazó PATCH del flujo %s (%s): %s",
                            flow_id, r.status_code, r.text[:200])
                return False
            return True
        except Exception as exc:  # noqa: BLE001
            log.warning("No se pudo actualizar el flujo %s: %s", flow_id, exc)
            return False

    def close(self):
        try:
            self.session.close()
        except Exception:  # noqa: BLE001
            pass
