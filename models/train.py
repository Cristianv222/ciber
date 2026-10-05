"""Entrenamiento de la cascada de detección sobre un dataset CIC-IDS.

Genera y exporta a OUT_DIR (por defecto /models):
    xgboost.pkl       Clasificador XGBoost multiclase (etapa 1: tipo de ataque)
    cnn_lstm.h5       Red CNN-LSTM binaria (etapa 2: ataque vs benigno)
    autoencoder.h5    Autoencoder entrenado con tráfico benigno (etapa 3: anomalía)
    scaler.pkl        StandardScaler (para CNN-LSTM y Autoencoder)
    metadata.json     Orden de features, clases, umbral del autoencoder, etc.

Uso:
    python train.py --dataset /data/datasets --out /models
    DATASET_PATH=/data/datasets OUT_DIR=/models python train.py

XGBoost usa las features en crudo (los árboles son invariantes a la escala).
CNN-LSTM y Autoencoder usan las features escaladas con `scaler.pkl`.
"""

import argparse
import json
import os
from datetime import datetime, timezone

import joblib
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

from features import FEATURE_COLUMNS, load_dataset


def _env(name, default=None):
    v = os.environ.get(name)
    return v if v not in (None, "") else default


def parse_args():
    p = argparse.ArgumentParser(description="Entrenamiento de la cascada de detección")
    p.add_argument("--dataset", default=_env("DATASET_PATH", "/data/datasets"))
    p.add_argument("--out", default=_env("OUT_DIR", "/models"))
    p.add_argument("--test-size", type=float, default=float(_env("TEST_SIZE", "0.2")))
    p.add_argument("--epochs", type=int, default=int(_env("EPOCHS", "15")))
    p.add_argument("--batch-size", type=int, default=int(_env("BATCH_SIZE", "256")))
    p.add_argument("--ae-percentile", type=float, default=float(_env("AE_PERCENTILE", "99")),
                   help="percentil del error benigno para el umbral del autoencoder")
    return p.parse_args()


def train_xgboost(X_train, y_train, X_test, y_test, class_names, out_dir):
    from xgboost import XGBClassifier
    from sklearn.metrics import accuracy_score

    print(f"[xgboost] entrenando multiclase ({len(class_names)} clases)…")
    model = XGBClassifier(
        n_estimators=300, max_depth=8, learning_rate=0.1,
        subsample=0.8, colsample_bytree=0.8,
        objective="multi:softprob", num_class=len(class_names),
        tree_method="hist", n_jobs=-1, eval_metric="mlogloss",
    )
    model.fit(X_train, y_train)
    acc = accuracy_score(y_test, model.predict(X_test))
    print(f"[xgboost] accuracy test = {acc:.4f}")
    joblib.dump(model, os.path.join(out_dir, "xgboost.pkl"))
    return acc


def train_cnn_lstm(Xs_train, y_train, Xs_test, y_test, epochs, batch_size, out_dir):
    from tensorflow import keras
    from tensorflow.keras import layers

    n_features = Xs_train.shape[1]
    Xtr = Xs_train.reshape((-1, n_features, 1))
    Xte = Xs_test.reshape((-1, n_features, 1))

    print("[cnn_lstm] entrenando clasificador binario…")
    model = keras.Sequential([
        keras.Input(shape=(n_features, 1)),
        layers.Conv1D(64, 3, activation="relu", padding="same"),
        layers.MaxPooling1D(2),
        layers.Conv1D(128, 3, activation="relu", padding="same"),
        layers.MaxPooling1D(2),
        layers.LSTM(64),
        layers.Dropout(0.3),
        layers.Dense(64, activation="relu"),
        layers.Dense(1, activation="sigmoid"),
    ])
    model.compile(optimizer="adam", loss="binary_crossentropy", metrics=["accuracy"])
    model.fit(Xtr, y_train, validation_split=0.1, epochs=epochs,
              batch_size=batch_size, verbose=2)
    loss, acc = model.evaluate(Xte, y_test, verbose=0)
    print(f"[cnn_lstm] accuracy test = {acc:.4f}")
    model.save(os.path.join(out_dir, "cnn_lstm.h5"))
    return acc


def train_autoencoder(Xs_train, y_train, epochs, batch_size, percentile, out_dir):
    from tensorflow import keras
    from tensorflow.keras import layers

    # Entrena SOLO con tráfico benigno (y == 0)
    benign = Xs_train[y_train == 0]
    if len(benign) == 0:
        print("[autoencoder] AVISO: no hay tráfico benigno; se omite")
        return None
    n_features = benign.shape[1]

    print(f"[autoencoder] entrenando con {len(benign)} muestras benignas…")
    model = keras.Sequential([
        keras.Input(shape=(n_features,)),
        layers.Dense(64, activation="relu"),
        layers.Dense(32, activation="relu"),
        layers.Dense(16, activation="relu"),
        layers.Dense(32, activation="relu"),
        layers.Dense(64, activation="relu"),
        layers.Dense(n_features, activation="linear"),
    ])
    model.compile(optimizer="adam", loss="mse")
    model.fit(benign, benign, validation_split=0.1, epochs=epochs,
              batch_size=batch_size, verbose=2)

    recon = model.predict(benign, verbose=0)
    errors = np.mean(np.square(benign - recon), axis=1)
    threshold = float(np.percentile(errors, percentile))
    print(f"[autoencoder] umbral (p{percentile}) = {threshold:.6f}")
    model.save(os.path.join(out_dir, "autoencoder.h5"))
    return threshold


def main():
    args = parse_args()
    os.makedirs(args.out, exist_ok=True)

    print(f"[train] cargando dataset desde {args.dataset}…")
    X, y_bin, y_multi, class_names = load_dataset(args.dataset)
    print(f"[train] muestras={len(X)}  features={X.shape[1]}  clases={class_names}")

    X_train, X_test, ybin_train, ybin_test, ymul_train, ymul_test = train_test_split(
        X.to_numpy(), y_bin, y_multi, test_size=args.test_size,
        random_state=42, stratify=y_bin,
    )

    scaler = StandardScaler().fit(X_train)
    Xs_train = scaler.transform(X_train)
    Xs_test = scaler.transform(X_test)
    joblib.dump(scaler, os.path.join(args.out, "scaler.pkl"))

    metadata = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "feature_columns": FEATURE_COLUMNS,
        "class_names": class_names,          # índice = código que predice XGBoost
        "n_samples": int(len(X)),
        "models": {},
    }

    # Etapa 1 — XGBoost (obligatoria)
    try:
        metadata["models"]["xgboost"] = {"accuracy": train_xgboost(
            X_train, ymul_train, X_test, ymul_test, class_names, args.out)}
    except Exception as exc:  # noqa: BLE001
        print(f"[xgboost] ERROR: {exc}")

    # Etapas 2 y 3 — CNN-LSTM y Autoencoder (requieren TensorFlow)
    try:
        import tensorflow  # noqa: F401
        has_tf = True
    except Exception as exc:  # noqa: BLE001
        has_tf = False
        print(f"[train] TensorFlow no disponible, se omiten CNN-LSTM y Autoencoder: {exc}")

    if has_tf:
        try:
            metadata["models"]["cnn_lstm"] = {"accuracy": train_cnn_lstm(
                Xs_train, ybin_train, Xs_test, ybin_test,
                args.epochs, args.batch_size, args.out)}
        except Exception as exc:  # noqa: BLE001
            print(f"[cnn_lstm] ERROR: {exc}")

        try:
            thr = train_autoencoder(Xs_train, ybin_train, args.epochs,
                                    args.batch_size, args.ae_percentile, args.out)
            metadata["models"]["autoencoder"] = {"threshold": thr}
        except Exception as exc:  # noqa: BLE001
            print(f"[autoencoder] ERROR: {exc}")

    with open(os.path.join(args.out, "metadata.json"), "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"[train] artefactos exportados a {args.out}")
    print(f"[train] contenido: {sorted(os.listdir(args.out))}")


if __name__ == "__main__":
    main()
