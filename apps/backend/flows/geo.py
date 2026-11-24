"""Geolocalización offline de IPs con DB-IP City Lite / GeoLite2 (geoip2).

No realiza ninguna consulta externa: lee la base de datos .mmdb local oficial."""

import ipaddress
import logging
import os

log = logging.getLogger('flows.geo')

_reader = None

# Nombres oficiales (es) que conviene acortar para las etiquetas del mapa
_SHORTEN = {
    'Estados Unidos de América': 'Estados Unidos',
    'Reino Unido de Gran Bretaña e Irlanda del Norte': 'Reino Unido',
    'Rusia, Federación de': 'Rusia',
    'Corea, República de': 'Corea del Sur',
    'Corea, República Popular Democrática de': 'Corea del Norte',
    'Irán, República Islámica de': 'Irán',
    'Taiwán (Provincia de China)': 'Taiwán',
    'Moldavia, República de': 'Moldavia',
    'Tanzania, República Unida de': 'Tanzania',
    'Venezuela, República Bolivariana de': 'Venezuela',
    'Bolivia, Estado Plurinacional de': 'Bolivia',
    'Macedonia del Norte': 'Macedonia del Norte',
    'Viet Nam': 'Vietnam',
    'Siria, República Árabe': 'Siria',
    'Palestina, Estado de': 'Palestina',
}


def _clean(name):
    """Quita sufijos entre paréntesis ('(los)', '(Provincia de China)') y acorta
    los nombres oficiales largos para que quepan como etiqueta."""
    if not name:
        return name
    name = name.strip()
    name = _SHORTEN.get(name, name)
    # elimina un sufijo entre paréntesis al final, p. ej. "Países Bajos (los)"
    i = name.rfind(' (')
    if i > 0 and name.endswith(')'):
        name = name[:i].strip()
    return _SHORTEN.get(name, name)


def _get_reader():
    global _reader
    if _reader is None:
        import geoip2.database
        path = os.environ.get('GEOIP_DB', '/geoip/dbip-city-lite.mmdb')
        # Prioriza nombres en español; cae a inglés si falta la traducción
        _reader = geoip2.database.Reader(path, locales=['es', 'en'])
    return _reader


def _is_public(ip):
    try:
        obj = ipaddress.ip_address(ip)
        return obj.is_global and not obj.is_private
    except ValueError:
        return False


def locate(ip):
    """Devuelve {country, country_code, city, lat, lon} o None si no se puede ubicar
    (IP privada, reservada o sin datos)."""
    if not _is_public(ip):
        return None
    try:
        r = _get_reader().city(ip)
        if r.location.latitude is not None and r.location.longitude is not None:
            return {
                'country': _clean(r.country.name) or 'Desconocido',
                'country_code': r.country.iso_code or 'XX',
                'city': _clean(r.city.name) or '',
                'lat': float(r.location.latitude),
                'lon': float(r.location.longitude),
            }
    except Exception as exc:  # noqa: BLE001
        log.debug("No se pudo ubicar IP %s: %s", ip, exc)
    return None
