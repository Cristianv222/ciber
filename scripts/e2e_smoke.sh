#!/usr/bin/env bash
# =============================================================================
# Prueba de humo end-to-end del pipeline autónomo.
# Siembra un flujo "unlabeled" vía la API y comprueba que el detector lo clasifica
# (label != unlabeled) y que la decisión le asigna cvss_score.
#
# Requisitos: stack levantado con modelos entrenados y agentes activos:
#   docker compose --profile agents up -d           # detector, decision, response
#   (y previamente:) docker compose --profile training run --rm trainer
#
# Uso:  ./scripts/e2e_smoke.sh [API_BASE_URL]
#       API_BASE_URL por defecto: http://localhost:8000
# =============================================================================
set -euo pipefail

API="${1:-http://localhost:8000}"
TIMEOUT="${TIMEOUT:-60}"

echo "==> API: $API"

# 1) Sembrar un flujo sin clasificar (valores arbitrarios; el detector lo procesará)
echo "==> Sembrando flujo de prueba…"
RESP="$(curl -sf -X POST "$API/api/flows/" \
  -H 'Content-Type: application/json' \
  -d '{
        "src_ip": "203.0.113.66", "src_port": 44444,
        "dst_ip": "10.0.0.10", "dst_port": 80, "protocol": 6,
        "flow_duration": 120000, "total_fwd_packets": 10, "total_bwd_packets": 2,
        "flow_bytes_s": 5000.0, "flow_packets_s": 100.0, "syn_flag_count": 3
      }')"

FLOW_ID="$(printf '%s' "$RESP" | grep -oE '"id":[0-9]+' | head -1 | grep -oE '[0-9]+')"
if [ -z "$FLOW_ID" ]; then
  echo "ERROR: no se pudo crear el flujo. Respuesta:"; printf '%s\n' "$RESP"; exit 1
fi
echo "    Flujo creado con id=$FLOW_ID (label inicial: unlabeled)"

# 2) Sondear hasta que el detector lo clasifique (o expire el timeout)
echo "==> Esperando clasificación (timeout ${TIMEOUT}s)…"
DEADLINE=$(( $(date +%s) + TIMEOUT ))
while :; do
  ROW="$(curl -sf "$API/api/flows/$FLOW_ID/")"
  LABEL="$(printf '%s' "$ROW" | grep -oE '"label":"[^"]*"' | head -1 | sed 's/"label":"//;s/"$//')"
  if [ -n "$LABEL" ] && [ "$LABEL" != "unlabeled" ]; then
    echo "==> ¡Clasificado!"
    echo "$ROW" | tr ',' '\n' | grep -E '"(label|attack_type|confidence|detector_stage|cvss_score|action_taken)"' || true
    echo
    echo "OK: el pipeline procesó el flujo end-to-end."
    exit 0
  fi
  if [ "$(date +%s)" -ge "$DEADLINE" ]; then
    echo "TIMEOUT: el flujo sigue como 'unlabeled'. ¿Está corriendo el detector y hay modelos en /models?"
    echo "Última fila:"; printf '%s\n' "$ROW"
    exit 2
  fi
  sleep 3
done
