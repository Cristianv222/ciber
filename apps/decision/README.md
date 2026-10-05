# apps/decision — Agente de decisión SPADE (Fase 4)

Recibe las alertas de amenaza del **DetectorAgent** por XMPP, calcula la severidad
**CVSS v4.0** del ataque, actualiza `cvss_score` vía la API REST y, si la puntuación
supera el umbral, ordena el bloqueo al **ResponseAgent** (Fase 5).

## Flujo
1. Recibe `Message` XMPP (ontology `threat_alert`) del detector.
2. `compute_cvss(attack_type)` → vector CVSS v4.0 + puntuación base (librería `cvss`).
3. `PATCH /api/flows/{id}/` con `cvss_score` → WebSocket (`flow_updated`).
4. Si `cvss_score >= CVSS_BLOCK_THRESHOLD` → `Message` XMPP (ontology `block_order`)
   a `response@ejabberd` con la IP a bloquear.

## Mapeo de severidad
`cvss_calc.py` traduce cada categoría de ataque (DoS/DDoS, escaneo, fuerza bruta,
web, bot, infiltración, Heartbleed, anomalía) a un **vector base CVSS v4.0**
realista; la puntuación la calcula la librería oficial `cvss`. Si la librería no
está, usa una tabla de respaldo (documentada en el propio archivo).

## Levantar
```bash
docker compose --profile agents up -d --build decision
docker compose logs -f decision
```

## Parámetros (env)
| Env | Def. | Descripción |
|-----|------|-------------|
| `CVSS_BLOCK_THRESHOLD` | `7.0` | CVSS mínimo para ordenar bloqueo (7.0 = High) |
| `DECISION_JID` / `RESPONSE_JID` | `decision@ejabberd` / `response@ejabberd` | JIDs XMPP |
| `API_BASE_URL` | `http://backend:8000` | base de la API |
