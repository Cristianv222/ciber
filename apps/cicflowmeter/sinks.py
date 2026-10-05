"""Sumideros de flujos: dónde se escriben los flujos extraídos.

- ApiSink  (recomendado): POST /api/flows/ → pasa por el ORM de Django → dispara
  el signal post_save → el WebSocket retransmite el flujo nuevo en vivo.
- DbSink   (alto rendimiento): INSERT directo en PostgreSQL con psycopg2. Más
  rápido, pero NO dispara el signal, así que los flujos nuevos no salen por el
  WebSocket (solo se verían vía Grafana, que consulta la BD directamente).
"""

import logging

log = logging.getLogger("cicflowmeter.sinks")


class ApiSink:
    def __init__(self, base_url, timeout=5.0):
        import requests
        self.url = base_url.rstrip('/') + '/api/flows/'
        self.timeout = timeout
        self.session = requests.Session()

    def write(self, data):
        try:
            r = self.session.post(self.url, json=data, timeout=self.timeout)
            if r.status_code >= 400:
                log.warning("API rechazó el flujo (%s): %s", r.status_code, r.text[:300])
        except Exception as exc:  # noqa: BLE001
            log.warning("No se pudo enviar el flujo a la API: %s", exc)

    def close(self):
        try:
            self.session.close()
        except Exception:  # noqa: BLE001
            pass


class DbSink:
    def __init__(self, host, port, dbname, user, password):
        self._conn_kwargs = dict(host=host, port=port, dbname=dbname,
                                 user=user, password=password)
        self.conn = None
        self._connect()

    def _connect(self):
        import psycopg2
        self.conn = psycopg2.connect(**self._conn_kwargs)
        self.conn.autocommit = True

    def write(self, data):
        cols = list(data.keys())
        placeholders = ', '.join(['%s'] * len(cols))
        sql = f"INSERT INTO flows ({', '.join(cols)}) VALUES ({placeholders})"
        values = [data[c] for c in cols]
        try:
            with self.conn.cursor() as cur:
                cur.execute(sql, values)
        except Exception as exc:  # noqa: BLE001
            log.warning("Fallo al insertar en BD, reintentando conexión: %s", exc)
            try:
                self._connect()
                with self.conn.cursor() as cur:
                    cur.execute(sql, values)
            except Exception as exc2:  # noqa: BLE001
                log.error("Inserción en BD falló definitivamente: %s", exc2)

    def close(self):
        try:
            if self.conn:
                self.conn.close()
        except Exception:  # noqa: BLE001
            pass


def build_sink(mode, cfg):
    if mode == 'db':
        log.info("Sumidero: INSERT directo en PostgreSQL %s:%s", cfg['db_host'], cfg['db_port'])
        return DbSink(cfg['db_host'], cfg['db_port'], cfg['db_name'],
                      cfg['db_user'], cfg['db_password'])
    log.info("Sumidero: API REST %s (los flujos nuevos saldrán por el WebSocket)", cfg['api_base_url'])
    return ApiSink(cfg['api_base_url'])
