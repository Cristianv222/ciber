"""Cálculo de severidad CVSS v4.0 a partir del tipo de ataque.

Cada categoría de ataque se mapea a un vector base CVSS v4.0 realista, y la
puntuación se calcula con la librería oficial `cvss` (tablas v4.0). Si la librería
no estuviera disponible, se usa una tabla de severidad de respaldo (documentada).
"""

import logging
import re

log = logging.getLogger("decision.cvss")

_PREFIX = "CVSS:4.0/"

# Vectores base CVSS v4.0 por categoría de ataque.
# Métricas: AV(Vector) AC(Complej.) AT(Requisitos) PR(Privilegios) UI(Interacción)
#           VC/VI/VA (impacto en sistema vulnerable) SC/SI/SA (sistema subsecuente)
_ATTACK_VECTORS = {
    # Denegación de servicio: alto impacto en disponibilidad
    "dos": "AV:N/AC:L/AT:N/PR:N/UI:N/VC:N/VI:N/VA:H/SC:N/SI:N/SA:H",
    # Reconocimiento / escaneo: bajo impacto (fuga de información menor)
    "scan": "AV:N/AC:L/AT:N/PR:N/UI:N/VC:L/VI:N/VA:N/SC:N/SI:N/SA:N",
    # Fuerza bruta de credenciales: compromiso de confidencialidad e integridad
    "brute": "AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:H/VA:N/SC:N/SI:N/SA:N",
    # Ataques web (SQLi/XSS/etc.)
    "web": "AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:H/VA:L/SC:L/SI:L/SA:N",
    # Botnet / C2: compromiso total del host
    "bot": "AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:H/VA:H/SC:H/SI:H/SA:H",
    # Infiltración / movimiento lateral
    "infiltration": "AV:N/AC:L/AT:P/PR:L/UI:N/VC:H/VI:H/VA:H/SC:H/SI:H/SA:H",
    # Heartbleed: fuga de confidencialidad
    "heartbleed": "AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:N/VA:N/SC:N/SI:N/SA:N",
    # Anomalía / desconocido: severidad media por defecto
    "default": "AV:N/AC:L/AT:N/PR:N/UI:N/VC:L/VI:L/VA:L/SC:N/SI:N/SA:N",
}

# Puntuaciones de respaldo si la librería `cvss` no está disponible
_FALLBACK_SCORES = {
    "dos": 8.2, "scan": 5.3, "brute": 8.1, "web": 8.7, "bot": 9.3,
    "infiltration": 9.4, "heartbleed": 7.5, "default": 6.0,
}


def _category(attack_type):
    a = re.sub(r"[^a-z0-9]", "", str(attack_type or "").lower())
    if "ddos" in a or "dos" in a:
        return "dos"
    if "scan" in a or "portscan" in a:
        return "scan"
    if "patator" in a or "brute" in a or "force" in a:
        return "brute"
    if "web" in a or "sql" in a or "xss" in a:
        return "web"
    if "bot" in a:
        return "bot"
    if "infiltr" in a:
        return "infiltration"
    if "heartbleed" in a:
        return "heartbleed"
    return "default"


def compute_cvss(attack_type):
    """Devuelve (base_score: float, vector: str) para el tipo de ataque dado."""
    cat = _category(attack_type)
    vector = _PREFIX + _ATTACK_VECTORS[cat]
    try:
        from cvss import CVSS4
        c = CVSS4(vector)
        score = float(getattr(c, "base_score", None) or c.scores()[0])
        return score, vector
    except Exception as exc:  # noqa: BLE001
        score = _FALLBACK_SCORES[cat]
        log.warning("Librería cvss no disponible (%s); uso puntuación de respaldo %.1f", exc, score)
        return score, vector
