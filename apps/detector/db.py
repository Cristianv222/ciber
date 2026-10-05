"""Lectura directa de flujos pendientes desde PostgreSQL (rápido).

El detector LEE de la BD directamente, pero ESCRIBE vía la API REST (ver api.py)
para que el signal post_save dispare la retransmisión por WebSocket."""

import logging

import psycopg2
import psycopg2.extras

log = logging.getLogger("detector.db")

# Columnas de identidad que se envían al DecisionAgent junto con el veredicto
META_COLUMNS = ["src_ip", "src_port", "dst_ip", "dst_port", "protocol"]


class FlowReader:
    def __init__(self, host, port, dbname, user, password, feature_columns):
        self._kwargs = dict(host=host, port=port, dbname=dbname, user=user, password=password)
        self.features = feature_columns
        self.conn = None
        self._connect()

    def _connect(self):
        self.conn = psycopg2.connect(**self._kwargs)
        self.conn.autocommit = True

    def fetch_unlabeled(self, limit=100):
        """Devuelve [(id, meta_dict, feature_dict), ...] de flujos sin clasificar."""
        cols = META_COLUMNS + self.features
        col_sql = ", ".join(cols)
        sql = (f"SELECT id, {col_sql} FROM flows "
               f"WHERE label = 'unlabeled' ORDER BY id ASC LIMIT %s")
        try:
            with self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(sql, (limit,))
                rows = cur.fetchall()
        except Exception as exc:  # noqa: BLE001
            log.warning("Fallo al leer flujos, reconectando: %s", exc)
            self._connect()
            return []

        result = []
        for row in rows:
            fid = row["id"]
            meta = {c: row[c] for c in META_COLUMNS}
            feat = {c: row[c] for c in self.features}
            result.append((fid, meta, feat))
        return result

    def close(self):
        try:
            if self.conn:
                self.conn.close()
        except Exception:  # noqa: BLE001
            pass
