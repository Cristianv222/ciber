"""Geolocalización offline de IPs con DB-IP City Lite (geoip2).

No realiza ninguna consulta externa: lee la base de datos .mmdb local."""

import ipaddress
import logging
import os

log = logging.getLogger('flows.geo')

_reader = None


def _get_reader():
    global _reader
    if _reader is None:
        import geoip2.database
        path = os.environ.get('GEOIP_DB', '/geoip/dbip-city-lite.mmdb')
        _reader = geoip2.database.Reader(path)
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
        if r.location.latitude is None:
            return None
        return {
            'country': r.country.name,
            'country_code': r.country.iso_code,
            'city': r.city.name,
            'lat': float(r.location.latitude),
            'lon': float(r.location.longitude),
        }
    except Exception:  # noqa: BLE001
        return None
