"""Valida la cascada sobre un dataset etiquetado: matriz de confusión + métricas.

Lee un CSV en el esquema de `flows` (con la columna `label` como ground truth),
clasifica con el modelo (XGBoost multiclase) y compara contra la etiqueta real.
No toca la base de datos.

Uso (detector container, con el CSV y los modelos montados):
    docker compose run --rm \
      -v "/ruta/dataset.csv:/data/dataset.csv:ro" \
      -v /ruta/models:/models:ro \
      -v /ruta/validate.py:/app/validate.py:ro \
      -e VALIDATE_CSV=/data/dataset.csv detector python validate.py
"""

import csv
import os
import sys

import numpy as np
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score

from classifier import Cascade

csv.field_size_limit(sys.maxsize)


def _env(name, default=None):
    v = os.environ.get(name)
    return v if v not in (None, "") else default


def _norm(s):
    return str(s).strip().lower()


def main():
    csv_path = _env("VALIDATE_CSV", "/data/dataset.csv")
    batch = int(_env("VALIDATE_BATCH", "20000"))

    thresholds = {"xgb_attack": 0.6, "xgb_benign": 0.8, "cnn": 0.5}
    cascade = Cascade(_env("MODELS_DIR", "/models"), thresholds)
    feats = cascade.features
    classes = list(cascade.class_names)
    # Mapa normalizado -> nombre canónico de clase (para comparar sin importar mayúsculas)
    canon = {_norm(c): c for c in classes}

    y_true, y_pred = [], []
    rows = []
    total = 0
    skipped = 0

    def flush():
        nonlocal rows, total, skipped
        if not rows:
            return
        X = np.array([[float(r.get(c, 0.0) or 0.0) for c in feats] for r in rows], dtype=float)
        proba = cascade.xgb.predict_proba(X)
        idx = np.argmax(proba, axis=1)
        for r, i in zip(rows, idx):
            truth = canon.get(_norm(r.get("label")))
            if truth is None:        # etiqueta no reconocida → se omite
                skipped += 1
                continue
            y_true.append(truth)
            y_pred.append(classes[i])
            total += 1
        rows = []

    print(f"[validate] Leyendo {csv_path}…", flush=True)
    print(f"[validate] Clases del modelo: {classes}", flush=True)
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
            if len(rows) >= batch:
                flush()
                if total % 200000 == 0:
                    print(f"[validate] Procesados {total}…", flush=True)
        flush()

    print(f"\n[validate] Total evaluado: {total}  (omitidos: {skipped})\n", flush=True)

    acc = accuracy_score(y_true, y_pred)
    print("=" * 60)
    print(f"  ACCURACY GLOBAL: {acc * 100:.2f}%")
    print("=" * 60)
    print("\nREPORTE POR CLASE (precision / recall / F1):\n")
    print(classification_report(y_true, y_pred, labels=classes, digits=4, zero_division=0))

    print("MATRIZ DE CONFUSIÓN (filas = real, columnas = predicho):\n")
    cm = confusion_matrix(y_true, y_pred, labels=classes)
    width = max(len(c) for c in classes) + 2
    header = " " * width + "".join(f"{c[:10]:>12}" for c in classes)
    print(header)
    for i, c in enumerate(classes):
        line = f"{c:<{width}}" + "".join(f"{cm[i][j]:>12}" for j in range(len(classes)))
        print(line)
    print("\n[validate] Listo.")


if __name__ == "__main__":
    main()
