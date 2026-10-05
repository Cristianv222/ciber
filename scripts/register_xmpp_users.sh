#!/usr/bin/env bash
# Registra los usuarios XMPP de los agentes en Prosody (dominio "ejabberd").
# Lee las contraseñas de .env. Idempotente: si el usuario existe, lo indica.
#
# Uso:  ./scripts/register_xmpp_users.sh
set -euo pipefail
cd "$(dirname "$0")/.."

set -a; . ./.env; set +a

for u in admin detector decision response; do
  var="XMPP_$(echo "$u" | tr '[:lower:]' '[:upper:]')_PASSWORD"
  pw="${!var}"
  docker compose exec -T xmpp prosodyctl register "$u" ejabberd "$pw" \
    && echo "registrado: $u@ejabberd" \
    || echo "aviso: $u@ejabberd ya existía o no se pudo registrar"
done

echo "--- usuarios en el host 'ejabberd' ---"
docker compose exec -T xmpp prosodyctl shell 2>/dev/null <<'EOF' || true
EOF
