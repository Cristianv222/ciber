# apps/response — Agente de respuesta SPADE (Fase 5)

Recibe las órdenes de bloqueo del **DecisionAgent** por XMPP, aplica la regla
**iptables** (respetando `DRY_RUN` en desarrollo) y registra `action_taken` vía la
API REST.

## Flujo
1. Recibe `Message` XMPP (ontology `block_order`) con la IP atacante (`src_ip`).
2. Valida la IP (`ipaddress`) y aplica `iptables -I INPUT/FORWARD -s <ip> -j DROP`
   (o `ip6tables` si es IPv6). Idempotente (comprueba con `-C` antes de insertar).
3. `PATCH /api/flows/{id}/` con `action_taken` → WebSocket (`flow_updated`).

## Seguridad
- La IP proviene de un mensaje XMPP → se **valida siempre** con `ipaddress` y los
  comandos se ejecutan con `subprocess` en forma de lista (**nunca shell**), lo que
  evita inyección de comandos.
- `DRY_RUN=true` (por defecto en local): **no** ejecuta iptables, solo registra la
  acción simulada. Ponlo en `false` únicamente en la máquina de la U.

## Requisitos de despliegue
- Servicio con `cap_add: [NET_ADMIN]` y el paquete `iptables` (incluido en la imagen).
- ⚠️ Con la red *bridge* por defecto, las reglas afectan al **namespace del
  contenedor**. Para hacer cumplir el bloqueo a nivel del **host/gateway** en la U,
  ejecuta el contenedor con `network_mode: host` (y apunta `API_BASE_URL` /
  `XMPP_SERVER` a los puertos publicados en el host). En local con `DRY_RUN=true`
  esto es indiferente.

## Levantar
```bash
docker compose --profile agents up -d --build response
docker compose logs -f response
```

## Parámetros (env)
| Env | Def. | Descripción |
|-----|------|-------------|
| `DRY_RUN` | `true` | `true` simula el bloqueo; `false` ejecuta iptables |
| `RESPONSE_JID` | `response@ejabberd` | JID XMPP del agente |
| `API_BASE_URL` | `http://backend:8000` | base de la API |
