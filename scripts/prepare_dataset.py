"""Preparación y balanceo del dataset institucional de 1 millón de registros.

Lee los datos brutos de la UPEC:
  - C:\\Users\\godoy\\Downloads\\datos_benignos.csv.gz (Tráfico SPAN)
  - C:\\Users\\godoy\\Downloads\\datos_malignos.csv.gz (Honeynet T-Pot)

Clasifica el tráfico maligno en las 5 clases de ataque de la tesis:
  1. DoS
  2. DDoS
  3. PortScan
  4. BruteForce
  5. Exploit

Genera un dataset balanceado de 1.000.000 de flujos (500k benignos + 500k malignos)
y lo guarda en data/datasets/dataset_1m.csv.
"""

import os
import sys
import time
import numpy as np
import pandas as pd

_def_benign = r"C:\Users\godoy\Downloads\datos_benignos.csv.gz"
_def_malign = r"C:\Users\godoy\Downloads\datos_malignos.csv.gz"
BENIGN_PATH = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("BENIGN_CSV_PATH", _def_benign if os.path.exists(_def_benign) else "data/raw/datos_benignos.csv.gz")
MALIGN_PATH = sys.argv[2] if len(sys.argv) > 2 else os.environ.get("MALIGN_CSV_PATH", _def_malign if os.path.exists(_def_malign) else "data/raw/datos_malignos.csv.gz")
OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "datasets")
OUT_FILE = os.path.join(OUT_DIR, "dataset_1m.csv")

TARGET_BENIGN = 500_000
TARGET_MALIGN = 500_000
CHUNK_SIZE = 150_000

# Puertos característicos de la Honeynet institucional
BRUTE_PORTS = {21, 22, 23, 3389, 5900, 3306, 5432, 5434, 5435}
EXPLOIT_PORTS = {80, 443, 445, 8080, 8000, 8888, 9000, 8011, 8081, 7001, 5000, 8443}


def classify_malign_chunk(df):
    """Clasificación vectorizada basada en puertos y características de flujo."""
    cond_brute = df["dst_port"].isin(BRUTE_PORTS)
    cond_exploit = df["dst_port"].isin(EXPLOIT_PORTS)
    cond_ddos = (df["dst_port"] == 123)
    
    # DoS: DNS amplification o tasas altas de paquetes o inundación SYN sin respuesta
    cond_dos = (
        (df["dst_port"] == 53) | 
        (df["flow_packets_s"] > 5000) | 
        ((df["syn_flag_count"] > 0) & (df["total_bwd_packets"] == 0) & (df["total_fwd_packets"] > 5))
    )
    
    conditions = [cond_brute, cond_exploit, cond_ddos, cond_dos]
    choices = ["BruteForce", "Exploit", "DDoS", "DoS"]
    
    # El resto corresponde a escaneo de puertos / reconocimiento
    return np.select(conditions, choices, default="PortScan")


def extract_malign_data(target_total=500_000):
    """Extrae y clasifica flujos malignos balanceando las 5 clases."""
    print(f"\n[1/3] Extrayendo y clasificando flujos malignos desde {MALIGN_PATH}...")
    t0 = time.time()
    
    # Cuotas objetivo por clase para evitar que DDoS/NTP monopolice el dataset
    quotas = {
        "BruteForce": 50_000,
        "PortScan": 50_000,
        "Exploit": 100_000,
        "DoS": 100_000,
        "DDoS": 200_000,
    }
    
    collected = {k: [] for k in quotas}
    total_collected = 0
    scanned_rows = 0

    for chunk in pd.read_csv(MALIGN_PATH, chunksize=CHUNK_SIZE, low_memory=False):
        scanned_rows += len(chunk)
        chunk["attack_type"] = classify_malign_chunk(chunk)
        chunk["label"] = chunk["attack_type"]
        
        # Agrupar y recolectar según cuotas
        for atk, group in chunk.groupby("attack_type"):
            needed = quotas[atk] - sum(len(c) for c in collected[atk])
            if needed > 0:
                take = group.iloc[:needed]
                collected[atk].append(take)
                total_collected += len(take)
        
        print(f"  Scanned {scanned_rows:,} rows -> Malign collected: {total_collected:,}/{target_total:,} "
              f"({', '.join(f'{k}: {sum(len(c) for c in v):,}' for k, v in collected.items())})", end="\r")
        
        if total_collected >= target_total:
            break

    print()
    df_malign = pd.concat([df for sublist in collected.values() for df in sublist], ignore_index=True)
    
    # Si faltó alguna cuota para llegar exactamente a target_total, rellenamos proporcionalmente
    if len(df_malign) < target_total:
        print(f"  Completando flujos restantes hasta {target_total:,}...")
        diff = target_total - len(df_malign)
        # Tomar muestras adicionales de los chunks ya procesados
        extra = chunk.sample(n=min(diff, len(chunk)), random_state=42)
        df_malign = pd.concat([df_malign, extra], ignore_index=True)

    print(f"[1/3] Completado en {time.time()-t0:.1f}s. Distribución maligna final:")
    print(df_malign["label"].value_counts())
    return df_malign.iloc[:target_total]


def extract_benign_data(target_total=500_000):
    """Extrae flujos benignos de la captura SPAN institucional."""
    print(f"\n[2/3] Extrayendo {target_total:,} flujos benignos desde {BENIGN_PATH}...")
    t0 = time.time()
    
    chunks = []
    total = 0
    for chunk in pd.read_csv(BENIGN_PATH, chunksize=CHUNK_SIZE, low_memory=False):
        needed = target_total - total
        take = chunk.iloc[:needed].copy()
        take["label"] = "Benign"
        take["attack_type"] = "Benign"
        chunks.append(take)
        total += len(take)
        print(f"  Benign collected: {total:,}/{target_total:,}", end="\r")
        if total >= target_total:
            break

    print()
    df_benign = pd.concat(chunks, ignore_index=True)
    print(f"[2/3] Completado en {time.time()-t0:.1f}s. Total benignos: {len(df_benign):,}")
    return df_benign


def main():
    print("=" * 60)
    print("PREPARACIÓN DEL DATASET INSTITUCIONAL UPEC (1 MILLÓN DE FLUJOS)")
    print("=" * 60)
    
    os.makedirs(OUT_DIR, exist_ok=True)
    
    df_malign = extract_malign_data(TARGET_MALIGN)
    df_benign = extract_benign_data(TARGET_BENIGN)
    
    print("\n[3/3] Combinando y barajando el dataset final...")
    df_final = pd.concat([df_benign, df_malign], ignore_index=True)
    
    # Barajar aleatoriamente con semilla fija para reproducibilidad
    df_final = df_final.sample(frac=1.0, random_state=42).reset_index(drop=True)
    
    print(f"Guardando {len(df_final):,} registros en {OUT_FILE}...")
    t0 = time.time()
    df_final.to_csv(OUT_FILE, index=False)
    file_size_mb = os.path.getsize(OUT_FILE) / (1024 * 1024)
    
    print(f"Guardado exitoso en {time.time()-t0:.1f}s ({file_size_mb:.2f} MB)")
    print("\nRESUMEN FINAL DE CLASES:")
    print(df_final["label"].value_counts())
    print("\nDISTRIBUCIÓN BINARIA:")
    print((df_final["label"] != "Benign").value_counts().rename({False: "Benign", True: "Attack"}))
    print("=" * 60)


if __name__ == "__main__":
    main()
