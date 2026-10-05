"""Aplicación de reglas de bloqueo con iptables/ip6tables.

SEGURIDAD: la IP procede de un mensaje XMPP, por lo que se valida SIEMPRE con
`ipaddress` antes de usarla, y los comandos se ejecutan con `subprocess` en forma
de lista (nunca con shell) para evitar inyección de comandos.

DRY_RUN=true (desarrollo local): no ejecuta iptables, solo registra la acción."""

import ipaddress
import logging
import subprocess

log = logging.getLogger("response.firewall")

_BLOCK_CHAINS = ("INPUT", "FORWARD")
_blocked = set()   # memoria de IPs ya bloqueadas (evita reglas duplicadas)


def is_blocked(ip):
    return ip in _blocked


def _run(cmd, args):
    return subprocess.run([cmd, *args], capture_output=True, text=True)


def apply_block(ip, dry_run=True, chains=_BLOCK_CHAINS):
    """Bloquea una IP con iptables (o ip6tables si es IPv6).

    Devuelve una cadena corta (<=100) describiendo la acción, apta para
    almacenarse en la columna `action_taken`. Lanza ValueError si la IP es
    inválida."""
    ipobj = ipaddress.ip_address(ip)          # ValueError si no es una IP válida
    cmd = "ip6tables" if ipobj.version == 6 else "iptables"

    if ip in _blocked:
        return f"ya bloqueada {ip}"[:100]

    if dry_run:
        _blocked.add(ip)
        for ch in chains:
            log.info("DRY_RUN: %s -I %s -s %s -j DROP", cmd, ch, ip)
        return f"DRY_RUN: bloqueo simulado de {ip}"[:100]

    for ch in chains:
        # -C comprueba si la regla ya existe (idempotencia entre reinicios)
        check = _run(cmd, ["-C", ch, "-s", ip, "-j", "DROP"])
        if check.returncode != 0:
            add = _run(cmd, ["-I", ch, "-s", ip, "-j", "DROP"])
            if add.returncode != 0:
                err = (add.stderr or "").strip()
                log.error("%s falló para %s en %s: %s", cmd, ip, ch, err)
                return f"ERROR al bloquear {ip}: {err}"[:100]

    _blocked.add(ip)
    log.warning("IP %s BLOQUEADA con %s DROP", ip, cmd)
    return f"bloqueada {ip} ({cmd} DROP en {'/'.join(chains)})"[:100]
