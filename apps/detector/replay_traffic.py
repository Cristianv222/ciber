"""Reproduce un dataset de flujos como TRÁFICO EN VIVO hacia la API.

Lee un CSV en el esquema de `flows`, quita la etiqueta (label='unlabeled') y
POSTea cada flujo a /api/flows/ a un ritmo configurable. El detector los recoge
y los clasifica en vivo, y se ven en el frontend por WebSocket (new_flow →
flow_updated). Sirve para demostrar el pipeline autónomo con tráfico realista.

Variables:
    REPLAY_CSV    ruta del CSV            (def. /data/dataset.csv)
    API_BASE_URL  base de la API          (def. http://backend:8000)
    REPLAY_LIMIT  cuántos flujos enviar   (def. 2000; 0 = todos)
    REPLAY_RATE   flujos por segundo      (def. 100)
    REPLAY_SHUFFLE  true = mezcla antes    (def. true)
"""

import csv
import os
import random
import sys
import time

import requests

csv.field_size_limit(sys.maxsize)

# Columnas que NO se envían (las llena el pipeline o son automáticas)
EXCLUDE = {
    "id", "timestamp", "label", "attack_type", "confidence",
    "detector_stage", "cvss_score", "action_taken", "processed_at",
}


def _env(name, default=None):
    v = os.environ.get(name)
    return v if v not in (None, "") else default


def main():
    csv_path = _env("REPLAY_CSV", "/data/dataset.csv")
    api = _env("API_BASE_URL", "http://backend:8000").rstrip("/") + "/api/flows/"
    limit = int(_env("REPLAY_LIMIT", "2000"))
    rate = float(_env("REPLAY_RATE", "100"))
    shuffle = str(_env("REPLAY_SHUFFLE", "true")).lower() in ("1", "true", "yes")
    delay = 1.0 / rate if rate > 0 else 0

    print(f"[replay] Leyendo {csv_path}…", flush=True)
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        rows = []
        for row in reader:
            rows.append(row)
            if not shuffle and limit and len(rows) >= limit:
                break
    if shuffle:
        random.shuffle(rows)
    if limit:
        rows = rows[:limit]

    print(f"[replay] Enviando {len(rows)} flujos a {api} a ~{rate}/s…", flush=True)
    session = requests.Session()
    sent, failed = 0, 0
    start = time.time()
    for row in rows:
        payload = {k: v for k, v in row.items() if k not in EXCLUDE and v not in (None, "")}
        payload["label"] = "unlabeled"
        try:
            r = session.post(api, json=payload, timeout=5)
            if r.status_code >= 400:
                failed += 1
            else:
                sent += 1
        except Exception:  # noqa: BLE001
            failed += 1
        if sent % 500 == 0 and sent:
            print(f"[replay] Enviados {sent}…", flush=True)
        if delay:
            time.sleep(delay)

    elapsed = time.time() - start
    print(f"\n[replay] LISTO. Enviados {sent}, fallidos {failed} en {elapsed:.0f}s "
          f"(~{sent/max(elapsed,1):.0f}/s). El detector los está clasificando en vivo.", flush=True)


if __name__ == "__main__":
    main()
