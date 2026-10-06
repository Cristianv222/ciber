#!/usr/bin/env bash
# Registra los usuarios XMPP de los agentes (dominio "ejabberd").
# Funciona tanto si el servicio corre ejabberd (producción) como Prosody (local).
# Lee las contraseñas de .env. Idempotente.
#
# Nota: en producción con ejabberd los usuarios se auto-registran en el primer
# arranque (CTL_ON_CREATE); este script sirve para registrarlos a mano si hace falta.
#
# Uso:  ./scripts/register_xmpp_users.sh
set -euo pipefail
cd "$(dirname "$0")/.."

set -a; . ./.env; set +a

for u in admin detector decision response; do
  var="XMPP_$(echo "$u" | tr '[:lower:]' '[:upper:]')_PASSWORD"
  pw="${!var}"
  docker compose exec -T ejabberd sh -c \
    "command -v prosodyctl >/dev/null 2>&1 && prosodyctl register '$u' ejabberd '$pw' \
     || ejabberdctl register '$u' ejabberd '$pw'" \
    && echo "registrado: $u@ejabberd" \
    || echo "aviso: $u@ejabberd ya existía o no se pudo registrar"
done
