-- =============================================================================
-- CONFIGURACIÓN DE PROSODY — Servidor XMPP para los agentes SPADE
-- Proyecto de Tesis - Sistema Autónomo de Monitoreo de Red
-- =============================================================================
-- Se usa Prosody (Lua puro) en lugar de ejabberd porque ejabberd/ecs no publica
-- imagen arm64 y su NIF nativo de TLS (fast_tls) falla bajo emulación en Apple
-- Silicon. Prosody funciona igual en arm64 y amd64.
--
-- El dominio XMPP se mantiene como "ejabberd" (alias de red del contenedor) para
-- no cambiar los JIDs de los agentes: detector@ejabberd, decision@ejabberd, etc.
-- =============================================================================

admins = { "admin@ejabberd" }

modules_enabled = {
    "roster";
    "saslauth";
    "tls";
    "disco";
    "private";
    "vcard4";
    "vcard_legacy";
    "version";
    "uptime";
    "time";
    "ping";
    "admin_adhoc";
}

-- Registro deshabilitado (los usuarios se crean con prosodyctl).
allow_registration = false

-- Comunicación en texto plano dentro de la red interna de Docker (sin TLS).
c2s_require_encryption = false
s2s_require_encryption = false
allow_unencrypted_plain_auth = true

authentication = "internal_hashed"

pidfile = "/var/lib/prosody/prosody.pid"

log = {
    info = "*console";
}

VirtualHost "ejabberd"
