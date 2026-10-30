"""Clasificador por LOTES del histórico de flujos (offline, directo a la BD).

Clasifica millones de flujos 'unlabeled' de forma eficiente, SIN pasar por la API
ni por XMPP: lee bloques grandes, predice vectorizado con la cascada y hace UPDATE
masivo en PostgreSQL. Pensado para etiquetar un dataset histórico grande (p. ej.
2 semanas de captura) en horas en vez de semanas.

Conserva todos los datos: solo rellena label / attack_type / confidence /
detector_stage / processed_at de los flujos que estaban sin clasificar.

Uso (en el servidor):
    docker compose run --rm detector python classify_batch.py
    # o con un tamaño de lote distinto:
    docker compose run --rm -e CLASSIFY_BATCH_SIZE=20000 detector python classify_batch.py
"""

import logging
import os
import time

import numpy as np
import psycopg2
import psycopg2.extras

from classifier import Cascade, decide

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("classify_batch")


def _env(name, default=None):
    v = os.environ.get(name)
    return v if v not in (None, "") else default


def main():
    models_dir = _env("MODELS_DIR", "/models")
    thresholds = {
        "xgb_attack": float(_env("XGB_ATTACK_THRESHOLD", "0.6")),
        "xgb_benign": float(_env("XGB_BENIGN_THRESHOLD", "0.8")),
        "cnn": float(_env("CNN_THRESHOLD", "0.5")),
    }
    batch_size = int(_env("CLASSIFY_BATCH_SIZE", "10000"))

    # Carga la cascada (falla rápido si faltan modelos → entrena primero)
    cascade = Cascade(models_dir, thresholds)
    feats = cascade.features
    col_sql = ", ".join(feats)

    conn = psycopg2.connect(
        host=_env("POSTGRES_HOST", "postgres"),
        port=_env("POSTGRES_PORT", "5432"),
        dbname=_env("POSTGRES_DB", "netflows"),
        user=_env("POSTGRES_USER", "tesis"),
        password=_env("POSTGRES_PASSWORD", ""),
    )
    conn.autocommit = False

    # Cuántos quedan por clasificar (para mostrar progreso)
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM flows WHERE label = 'unlabeled'")
        pending = cur.fetchone()[0]
    log.info("Flujos sin clasificar: %d. Lote=%d.", pending, batch_size)

    total = 0
    start = time.time()

    while True:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                f"SELECT id, {col_sql} FROM flows WHERE label = 'unlabeled' "
                f"ORDER BY id LIMIT %s",
                (batch_size,),
            )
            rows = cur.fetchall()
        if not rows:
            break

        ids = [r["id"] for r in rows]
        X = np.array(
            [[float(r.get(c, 0.0) or 0.0) for c in feats] for r in rows],
            dtype=float,
        )

        # Predicción vectorizada (todo el lote de una vez)
        proba = cascade.xgb.predict_proba(X)
        cnn_p = ae_err = None
        if cascade.scaler is not None and (cascade.cnn is not None or cascade.ae is not None):
            Xs = cascade.scaler.transform(X)
            if cascade.cnn is not None:
                xr = Xs.reshape((Xs.shape[0], Xs.shape[1], 1))
                cnn_p = cascade.cnn.predict(xr, verbose=0).ravel()
            if cascade.ae is not None and cascade.ae_threshold is not None:
                recon = cascade.ae.predict(Xs, verbose=0)
                ae_err = np.mean(np.square(Xs - recon), axis=1)

        updates = []
        for i, rid in enumerate(ids):
            v = decide(
                proba[i], cascade.class_names, cascade.benign_idx,
                None if cnn_p is None else float(cnn_p[i]),
                None if ae_err is None else float(ae_err[i]),
                cascade.ae_threshold, thresholds,
            )
            updates.append((rid, v["label"], v["attack_type"], v["confidence"], v["detector_stage"]))

        with conn.cursor() as cur:
            psycopg2.extras.execute_values(
                cur,
                "UPDATE flows AS f SET "
                "label = d.label::varchar(50), "
                "attack_type = d.attack_type::varchar(50), "
                "confidence = d.confidence::double precision, "
                "detector_stage = d.stage::varchar(30), "
                "processed_at = NOW() "
                "FROM (VALUES %s) AS d(id, label, attack_type, confidence, stage) "
                "WHERE f.id = d.id::bigint",
                updates,
                template="(%s,%s,%s,%s,%s)",
                page_size=batch_size,
            )
        conn.commit()

        total += len(rows)
        elapsed = max(time.time() - start, 1e-6)
        rate = total / elapsed
        remaining = max(pending - total, 0)
        eta_min = (remaining / rate / 60) if rate > 0 else 0
        log.info("Clasificados %d/%d  (%.0f flujos/s, ETA ~%.0f min)", total, pending, rate, eta_min)

    conn.close()
    log.info("TERMINADO. Flujos clasificados en esta corrida: %d", total)


if __name__ == "__main__":
    main()
