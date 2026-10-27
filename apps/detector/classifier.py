"""Cascada de detección: XGBoost → CNN-LSTM → Autoencoder.

La lógica de decisión (`decide`) es una función pura y testeable, separada de la
carga de modelos (`Cascade`). El orden de features se lee de `metadata.json`
(escrito por models/train.py), de modo que no hay que duplicar la lista aquí.
"""

import json
import logging
import os

import numpy as np

log = logging.getLogger("detector.classifier")


def _benign(name):
    return str(name).strip().upper().startswith("BENIGN")


def decide(proba, class_names, benign_idx, cnn_p, ae_err, ae_threshold, thr):
    """Decide el veredicto a partir de las salidas de cada etapa.

    proba: vector de probabilidades de XGBoost (multiclase).
    cnn_p: probabilidad de ataque de CNN-LSTM (o None si no disponible).
    ae_err / ae_threshold: error de reconstrucción y umbral (o None).
    thr: dict con 'xgb_attack', 'xgb_benign', 'cnn'.

    Devuelve dict con label, attack_type, confidence, detector_stage, is_threat.
    """
    top = int(np.argmax(proba))
    conf = float(proba[top])
    cls = class_names[top]
    is_benign_class = (top == benign_idx) or _benign(cls)

    # --- Etapa 1: XGBoost ---
    if not is_benign_class and conf >= thr["xgb_attack"]:
        return _r(cls, cls, conf, "xgboost", True)
    if is_benign_class and conf >= thr["xgb_benign"]:
        return _r("benign", None, conf, "xgboost", False)

    # --- Etapa 2: CNN-LSTM (solo si XGBoost quedó indeciso) ---
    if cnn_p is not None:
        if cnn_p >= thr["cnn"]:
            atk = cls if not is_benign_class else "unknown"
            return _r(atk, atk, float(cnn_p), "cnn_lstm", True)

    # --- Etapa 3: Autoencoder (anomalía / zero-day) ---
    if ae_err is not None and ae_threshold is not None and ae_threshold > 0:
        ratio = ae_err / ae_threshold
        if ratio > 1.0:
            confidence = round(min(1.0, (ratio - 1.0) / ratio), 4)
            return _r("anomaly", "anomaly", confidence, "autoencoder", True)

    # --- Sin señal de amenaza: benigno (mejor esfuerzo) ---
    last_stage = ("autoencoder" if ae_err is not None
                  else "cnn_lstm" if cnn_p is not None else "xgboost")
    return _r("benign", None, conf, last_stage, False)


def _r(label, attack_type, confidence, stage, is_threat):
    return {
        "label": label[:50],
        "attack_type": (attack_type[:50] if attack_type else None),
        "confidence": round(float(confidence), 4),
        "detector_stage": stage,
        "is_threat": is_threat,
    }


class Cascade:
    """Carga los artefactos de /models y clasifica vectores de features."""

    def __init__(self, models_dir, thresholds):
        self.thr = thresholds
        meta_path = os.path.join(models_dir, "metadata.json")
        if not os.path.exists(meta_path):
            raise FileNotFoundError(
                f"No existe {meta_path}. Ejecuta el 'trainer' (Fase 2) antes del detector.")
        with open(meta_path) as f:
            meta = json.load(f)
        self.features = meta["feature_columns"]
        self.class_names = meta["class_names"]
        self.benign_idx = next((i for i, c in enumerate(self.class_names) if _benign(c)), -1)
        self.ae_threshold = (meta.get("models", {}).get("autoencoder", {}) or {}).get("threshold")

        import joblib
        xgb_path = os.path.join(models_dir, "xgboost.pkl")
        if not os.path.exists(xgb_path):
            raise FileNotFoundError(
                f"No existe {xgb_path}. Ejecuta el 'trainer' (Fase 2) antes del detector.")
        self.xgb = joblib.load(xgb_path)

        scaler_path = os.path.join(models_dir, "scaler.pkl")
        self.scaler = joblib.load(scaler_path) if os.path.exists(scaler_path) else None

        # Modelos opcionales (etapas 2 y 3) — soporta PyTorch (.pt) o Keras (.h5)
        self.cnn = self._load_model(os.path.join(models_dir, "cnn_lstm.pt"),
                                    os.path.join(models_dir, "cnn_lstm.h5"))
        self.ae = self._load_model(os.path.join(models_dir, "autoencoder.pt"),
                                   os.path.join(models_dir, "autoencoder.h5"))

        log.info("Cascada cargada. Features=%d, clases=%s, cnn=%s, ae=%s (umbral=%s)",
                 len(self.features), self.class_names,
                 self.cnn is not None, self.ae is not None, self.ae_threshold)

    @staticmethod
    def _load_model(pt_path, h5_path):
        # 1. Intentar PyTorch (.pt)
        if os.path.exists(pt_path):
            try:
                import torch
                import sys
                cur_dir = os.path.dirname(os.path.abspath(__file__))
                models_dir = os.path.abspath(os.path.join(cur_dir, "..", "..", "models"))
                if models_dir not in sys.path:
                    sys.path.insert(0, models_dir)
                from architectures import CNN_LSTM_PyTorch, Autoencoder_PyTorch

                data = torch.load(pt_path, map_location="cpu", weights_only=True)
                if "cnn_lstm" in os.path.basename(pt_path):
                    model = CNN_LSTM_PyTorch(n_features=78, n_classes=1)
                else:
                    model = Autoencoder_PyTorch(n_features=78)

                if isinstance(data, dict):
                    model.load_state_dict(data)
                else:
                    model = data
                model.eval()

                class _TorchWrapper:
                    def __init__(self, m):
                        self.m = m

                    def predict(self, x, verbose=0):
                        with torch.no_grad():
                            t = torch.from_numpy(x).float()
                            out = self.m(t)
                            return out.cpu().numpy()

                return _TorchWrapper(model)
            except Exception as exc:  # noqa: BLE001
                log.warning("No se pudo cargar modelo PyTorch %s: %s", pt_path, exc)

        # 2. Intentar Keras (.h5)
        if os.path.exists(h5_path):
            try:
                from tensorflow import keras
                return keras.models.load_model(h5_path)
            except Exception as exc:  # noqa: BLE001
                log.warning("No se pudo cargar modelo Keras %s: %s", h5_path, exc)

        return None

    def _vector(self, feat):
        return np.array([[float(feat.get(c, 0.0) or 0.0) for c in self.features]], dtype=float)

    def classify(self, feat):
        x = self._vector(feat)
        proba = self.xgb.predict_proba(x)[0]

        cnn_p = None
        ae_err = None
        need_escalation = True  # decide() reevalúa; calculamos etapas 2/3 solo si aportan

        if self.scaler is not None and (self.cnn is not None or self.ae is not None):
            xs = self.scaler.transform(x)
            if self.cnn is not None:
                xr = xs.reshape((1, xs.shape[1], 1))
                cnn_p = float(self.cnn.predict(xr, verbose=0)[0][0])
            if self.ae is not None and self.ae_threshold is not None:
                recon = self.ae.predict(xs, verbose=0)
                ae_err = float(np.mean(np.square(xs - recon)))

        return decide(proba, self.class_names, self.benign_idx,
                      cnn_p, ae_err, self.ae_threshold, self.thr)
