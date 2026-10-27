"""Entrenamiento de la cascada de detección sobre el dataset institucional de la UPEC.

Genera y exporta a OUT_DIR (por defecto models/):
    xgboost.pkl       Clasificador XGBoost (Etapa 1: filtro de alta velocidad)
    cnn_lstm.pt       Red CNN-LSTM híbrida en PyTorch (Etapa 2: clasificación de amenazas)
    autoencoder.pt    Autoencoder en PyTorch entrenado con tráfico benigno (Etapa 3: anomalías)
    scaler.pkl        StandardScaler (para CNN-LSTM y Autoencoder)
    metadata.json     Orden canónico de features, clases, umbral del autoencoder y métricas

Hiperparámetros alineados con la tesis de la UPEC:
    - Optimizador Adam con tasa de aprendizaje = 0.001
    - Batch Normalization y Dropout (0.3) para prevenir sobreajuste
    - Umbral de detección del autoencoder por percentil sobre tráfico benigno
"""

import argparse
import json
import os
import time
from datetime import datetime, timezone

import joblib
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

from features import FEATURE_COLUMNS, load_dataset


def _env(name, default=None):
    v = os.environ.get(name)
    return v if v not in (None, "") else default


def parse_args():
    p = argparse.ArgumentParser(description="Entrenamiento de la cascada de detección (UPEC)")
    p.add_argument("--dataset", default=_env("DATASET_PATH", "data/datasets/dataset_1m.csv"))
    p.add_argument("--out", default=_env("OUT_DIR", "models"))
    p.add_argument("--test-size", type=float, default=float(_env("TEST_SIZE", "0.2")))
    p.add_argument("--epochs", type=int, default=int(_env("EPOCHS", "5")))
    p.add_argument("--batch-size", type=int, default=int(_env("BATCH_SIZE", "512")))
    p.add_argument("--ae-percentile", type=float, default=float(_env("AE_PERCENTILE", "99.0")),
                   help="Percentil del error benigno para el umbral del autoencoder")
    return p.parse_args()


# =====================================================================
# ETAPA 1: XGBoost (Filtro de alta velocidad)
# =====================================================================
def train_xgboost(X_train, y_train, X_test, y_test, class_names, out_dir):
    from xgboost import XGBClassifier

    print(f"\n[1/3 XGBoost] Entrenando clasificador sobre {len(X_train):,} muestras ({len(class_names)} clases)...")
    t0 = time.time()
    model = XGBClassifier(
        n_estimators=200,
        max_depth=8,
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
        objective="multi:softprob",
        num_class=len(class_names),
        tree_method="hist",
        n_jobs=-1,
        eval_metric="mlogloss",
        random_state=42,
    )
    model.fit(X_train, y_train)
    preds = model.predict(X_test)
    acc = accuracy_score(y_test, preds)
    f1 = f1_score(y_test, preds, average="weighted")
    print(f"[1/3 XGBoost] Completado en {time.time()-t0:.1f}s | Accuracy Test: {acc:.4f} | F1-Score: {f1:.4f}")
    
    out_path = os.path.join(out_dir, "xgboost.pkl")
    joblib.dump(model, out_path)
    return {"accuracy": float(acc), "f1_score": float(f1)}


# =====================================================================
# ETAPA 2: Red Neuronal Híbrida CNN-LSTM (PyTorch)
# =====================================================================
class CNN_LSTM_PyTorch(nn.Module):
    def __init__(self, n_features, n_classes=1):
        super().__init__()
        self.conv1 = nn.Conv1d(1, 64, kernel_size=3, padding=1)
        self.bn1 = nn.BatchNorm1d(64)
        self.pool1 = nn.MaxPool1d(2)
        
        self.conv2 = nn.Conv1d(64, 128, kernel_size=3, padding=1)
        self.bn2 = nn.BatchNorm1d(128)
        self.pool2 = nn.MaxPool1d(2)
        
        self.lstm = nn.LSTM(input_size=128, hidden_size=64, batch_first=True)
        self.dropout = nn.Dropout(0.3)
        self.fc1 = nn.Linear(64, 64)
        self.relu = nn.ReLU()
        self.fc2 = nn.Linear(64, n_classes)
        self.act = nn.Sigmoid() if n_classes == 1 else nn.Softmax(dim=1)

    def forward(self, x):
        if x.dim() == 2:
            x = x.unsqueeze(1)
        elif x.dim() == 3 and x.size(2) == 1:
            x = x.transpose(1, 2)
            
        x = torch.relu(self.bn1(self.conv1(x)))
        x = self.pool1(x)
        x = torch.relu(self.bn2(self.conv2(x)))
        x = self.pool2(x)
        
        x = x.permute(0, 2, 1)
        out, _ = self.lstm(x)
        last_step = out[:, -1, :]
        x = self.dropout(last_step)
        x = self.relu(self.fc1(x))
        x = self.fc2(x)
        return self.act(x)


def train_cnn_lstm(Xs_train, y_train, Xs_test, y_test, epochs, batch_size, out_dir):
    print(f"\n[2/3 CNN-LSTM] Entrenando red híbrida en PyTorch ({epochs} épocas, batch={batch_size})...")
    t0 = time.time()
    n_features = Xs_train.shape[1]
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"  Dispositivo: {device}")
    
    # Preparar DataLoaders
    x_tr = torch.from_numpy(Xs_train).float()
    y_tr = torch.from_numpy(y_train).float().unsqueeze(1)
    x_te = torch.from_numpy(Xs_test).float()
    y_te = torch.from_numpy(y_test).float().unsqueeze(1)
    
    train_loader = DataLoader(TensorDataset(x_tr, y_tr), batch_size=batch_size, shuffle=True)
    
    model = CNN_LSTM_PyTorch(n_features, n_classes=1).to(device)
    # Tasa de aprendizaje 0.001 según especificación de la tesis
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    criterion = nn.BCELoss()
    
    model.train()
    for ep in range(1, epochs + 1):
        ep_loss = 0.0
        n_batches = 0
        for bx, by in train_loader:
            bx, by = bx.to(device), by.to(device)
            optimizer.zero_grad()
            pred = model(bx)
            loss = criterion(pred, by)
            loss.backward()
            optimizer.step()
            ep_loss += loss.item()
            n_batches += 1
        avg_loss = ep_loss / max(1, n_batches)
        print(f"  Época {ep}/{epochs} - Loss: {avg_loss:.4f}")
        
    model.eval()
    with torch.no_grad():
        test_preds = (model(x_te.to(device)).cpu() >= 0.5).int().numpy().flatten()
        test_acc = accuracy_score(y_test, test_preds)
        test_f1 = f1_score(y_test, test_preds)
        
    print(f"[2/3 CNN-LSTM] Completado en {time.time()-t0:.1f}s | Accuracy Test: {test_acc:.4f} | F1-Score: {test_f1:.4f}")
    
    out_path = os.path.join(out_dir, "cnn_lstm.pt")
    torch.save(model.state_dict(), out_path)
    return {"accuracy": float(test_acc), "f1_score": float(test_f1)}


# =====================================================================
# ETAPA 3: Autoencoder (Detector de Anomalías / Día Cero)
# =====================================================================
class Autoencoder_PyTorch(nn.Module):
    def __init__(self, n_features):
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Linear(n_features, 64),
            nn.BatchNorm1d(64),
            nn.ReLU(),
            nn.Linear(64, 32),
            nn.BatchNorm1d(32),
            nn.ReLU(),
            nn.Linear(32, 16),
            nn.BatchNorm1d(16),
            nn.ReLU(),
        )
        self.decoder = nn.Sequential(
            nn.Linear(16, 32),
            nn.BatchNorm1d(32),
            nn.ReLU(),
            nn.Linear(32, 64),
            nn.BatchNorm1d(64),
            nn.ReLU(),
            nn.Linear(64, n_features),
        )

    def forward(self, x):
        return self.decoder(self.encoder(x))


def train_autoencoder(Xs_train, y_train, epochs, batch_size, percentile, out_dir):
    benign = Xs_train[y_train == 0]
    if len(benign) == 0:
        print("[3/3 Autoencoder] AVISO: No hay tráfico benigno; omitiendo")
        return None
        
    n_features = benign.shape[1]
    print(f"\n[3/3 Autoencoder] Entrenando red de reconstrucción con {len(benign):,} muestras benignas...")
    t0 = time.time()
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    x_benign = torch.from_numpy(benign).float()
    loader = DataLoader(TensorDataset(x_benign, x_benign), batch_size=batch_size, shuffle=True)
    
    model = Autoencoder_PyTorch(n_features).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    criterion = nn.MSELoss()
    
    model.train()
    for ep in range(1, epochs + 1):
        ep_loss = 0.0
        n_batches = 0
        for bx, _ in loader:
            bx = bx.to(device)
            optimizer.zero_grad()
            recon = model(bx)
            loss = criterion(recon, bx)
            loss.backward()
            optimizer.step()
            ep_loss += loss.item()
            n_batches += 1
        print(f"  Época {ep}/{epochs} - Reconstruction MSE: {ep_loss / max(1, n_batches):.6f}")
        
    model.eval()
    with torch.no_grad():
        recon_benign = model(x_benign.to(device)).cpu().numpy()
        errors = np.mean(np.square(benign - recon_benign), axis=1)
        threshold = float(np.percentile(errors, percentile))
        
    print(f"[3/3 Autoencoder] Completado en {time.time()-t0:.1f}s | Umbral percentil {percentile}%: {threshold:.6f}")
    
    out_path = os.path.join(out_dir, "autoencoder.pt")
    torch.save(model.state_dict(), out_path)
    return threshold


# =====================================================================
# MAIN PIPELINE
# =====================================================================
def main():
    args = parse_args()
    os.makedirs(args.out, exist_ok=True)

    print("=" * 65)
    print("ENTRENAMIENTO DE LA CASCADA DE DETECCIÓN (TESIS UPEC)")
    print("=" * 65)
    print(f"Dataset:    {args.dataset}")
    print(f"Destino:    {args.out}")
    print(f"Test size:  {args.test_size} (División {int((1-args.test_size)*100)}/{int(args.test_size*100)})")
    print(f"Épocas:     {args.epochs}")
    print(f"Batch size: {args.batch_size}")
    print("=" * 65)

    X, y_bin, y_multi, class_names = load_dataset(args.dataset)
    print(f"\nDatos cargados: {len(X):,} flujos | {X.shape[1]} features | Clases: {class_names}")

    X_train, X_test, ybin_train, ybin_test, ymul_train, ymul_test = train_test_split(
        X.to_numpy(), y_bin, y_multi, test_size=args.test_size,
        random_state=42, stratify=y_bin,
    )

    print("\nAjustando StandardScaler sobre el conjunto de entrenamiento...")
    scaler = StandardScaler().fit(X_train)
    Xs_train = scaler.transform(X_train)
    Xs_test = scaler.transform(X_test)
    joblib.dump(scaler, os.path.join(args.out, "scaler.pkl"))

    metadata = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "feature_columns": FEATURE_COLUMNS,
        "class_names": class_names,
        "n_samples": int(len(X)),
        "models": {},
    }

    # 1. XGBoost
    try:
        metadata["models"]["xgboost"] = train_xgboost(
            X_train, ymul_train, X_test, ymul_test, class_names, args.out
        )
    except Exception as exc:
        print(f"[xgboost] ERROR: {exc}")

    # 2. CNN-LSTM (PyTorch)
    try:
        metadata["models"]["cnn_lstm"] = train_cnn_lstm(
            Xs_train, ybin_train, Xs_test, ybin_test,
            args.epochs, args.batch_size, args.out
        )
    except Exception as exc:
        print(f"[cnn_lstm] ERROR: {exc}")

    # 3. Autoencoder (PyTorch)
    try:
        thr = train_autoencoder(
            Xs_train, ybin_train, args.epochs,
            args.batch_size, args.ae_percentile, args.out
        )
        metadata["models"]["autoencoder"] = {"threshold": thr}
    except Exception as exc:
        print(f"[autoencoder] ERROR: {exc}")

    # Guardar metadata.json
    meta_path = os.path.join(args.out, "metadata.json")
    with open(meta_path, "w") as f:
        json.dump(metadata, f, indent=2)

    print("\n" + "=" * 65)
    print(f"ENTRENAMIENTO COMPLETADO CON ÉXITO")
    print(f"Artefactos exportados a {args.out}:")
    for f in sorted(os.listdir(args.out)):
        fpath = os.path.join(args.out, f)
        if os.path.isfile(fpath):
            size_mb = os.path.getsize(fpath) / (1024 * 1024)
            print(f"  - {f:<20} ({size_mb:.2f} MB)")
    print("=" * 65)


if __name__ == "__main__":
    main()
