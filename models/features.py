"""Definición canónica de features y carga de datasets CIC-IDS.

Este módulo es la ÚNICA fuente de verdad sobre:
  1. Qué columnas se usan como features y en qué ORDEN (`FEATURE_COLUMNS`).
  2. Cómo se traducen las cabeceras de los CSV de CIC-IDS2017/2018 a esos nombres.

Los nombres canónicos coinciden con las columnas de la tabla `flows` (y con las
claves que produce apps/cicflowmeter/flow.py::Flow.get_data), de modo que el mismo
vector sirve para entrenar (Fase 2) y para inferir en producción (Fase 3), sin
desajuste train/serve.
"""

import glob
import os
import re

import numpy as np
import pandas as pd


# --- Orden fijo de features (78). Debe coincidir con las columnas de `flows`. ---
FEATURE_COLUMNS = [
    "dst_port", "protocol",
    "flow_duration", "total_fwd_packets", "total_bwd_packets",
    "total_length_of_fwd_packets", "total_length_of_bwd_packets",
    "fwd_packet_length_max", "fwd_packet_length_min", "fwd_packet_length_mean", "fwd_packet_length_std",
    "bwd_packet_length_max", "bwd_packet_length_min", "bwd_packet_length_mean", "bwd_packet_length_std",
    "flow_bytes_s", "flow_packets_s",
    "flow_iat_mean", "flow_iat_std", "flow_iat_max", "flow_iat_min",
    "fwd_iat_total", "fwd_iat_mean", "fwd_iat_std", "fwd_iat_max", "fwd_iat_min",
    "bwd_iat_total", "bwd_iat_mean", "bwd_iat_std", "bwd_iat_max", "bwd_iat_min",
    "fwd_psh_flags", "bwd_psh_flags", "fwd_urg_flags", "bwd_urg_flags",
    "fwd_header_length", "bwd_header_length", "fwd_packets_s", "bwd_packets_s",
    "min_packet_length", "max_packet_length", "packet_length_mean", "packet_length_std", "packet_length_variance",
    "fin_flag_count", "syn_flag_count", "rst_flag_count", "psh_flag_count",
    "ack_flag_count", "urg_flag_count", "ece_flag_count", "cwr_flag_count",
    "down_up_ratio", "average_packet_size", "avg_fwd_segment_size", "avg_bwd_segment_size",
    "fwd_avg_bytes_bulk", "fwd_avg_packets_bulk", "fwd_avg_bulk_rate",
    "bwd_avg_bytes_bulk", "bwd_avg_packets_bulk", "bwd_avg_bulk_rate",
    "subflow_fwd_packets", "subflow_fwd_bytes", "subflow_bwd_packets", "subflow_bwd_bytes",
    "init_win_bytes_forward", "init_win_bytes_backward", "act_data_pkt_fwd", "min_seg_size_forward",
    "active_mean", "active_std", "active_max", "active_min",
    "idle_mean", "idle_std", "idle_max", "idle_min",
]


# --- Cabecera CIC-IDS (nombre visible) -> nombre canónico ---
_CIC_HEADERS = {
    "Destination Port": "dst_port",
    "Protocol": "protocol",
    "Flow Duration": "flow_duration",
    "Total Fwd Packets": "total_fwd_packets",
    "Total Backward Packets": "total_bwd_packets",
    "Total Length of Fwd Packets": "total_length_of_fwd_packets",
    "Total Length of Bwd Packets": "total_length_of_bwd_packets",
    "Fwd Packet Length Max": "fwd_packet_length_max",
    "Fwd Packet Length Min": "fwd_packet_length_min",
    "Fwd Packet Length Mean": "fwd_packet_length_mean",
    "Fwd Packet Length Std": "fwd_packet_length_std",
    "Bwd Packet Length Max": "bwd_packet_length_max",
    "Bwd Packet Length Min": "bwd_packet_length_min",
    "Bwd Packet Length Mean": "bwd_packet_length_mean",
    "Bwd Packet Length Std": "bwd_packet_length_std",
    "Flow Bytes/s": "flow_bytes_s",
    "Flow Packets/s": "flow_packets_s",
    "Flow IAT Mean": "flow_iat_mean",
    "Flow IAT Std": "flow_iat_std",
    "Flow IAT Max": "flow_iat_max",
    "Flow IAT Min": "flow_iat_min",
    "Fwd IAT Total": "fwd_iat_total",
    "Fwd IAT Mean": "fwd_iat_mean",
    "Fwd IAT Std": "fwd_iat_std",
    "Fwd IAT Max": "fwd_iat_max",
    "Fwd IAT Min": "fwd_iat_min",
    "Bwd IAT Total": "bwd_iat_total",
    "Bwd IAT Mean": "bwd_iat_mean",
    "Bwd IAT Std": "bwd_iat_std",
    "Bwd IAT Max": "bwd_iat_max",
    "Bwd IAT Min": "bwd_iat_min",
    "Fwd PSH Flags": "fwd_psh_flags",
    "Bwd PSH Flags": "bwd_psh_flags",
    "Fwd URG Flags": "fwd_urg_flags",
    "Bwd URG Flags": "bwd_urg_flags",
    "Fwd Header Length": "fwd_header_length",
    "Bwd Header Length": "bwd_header_length",
    "Fwd Packets/s": "fwd_packets_s",
    "Bwd Packets/s": "bwd_packets_s",
    "Min Packet Length": "min_packet_length",
    "Max Packet Length": "max_packet_length",
    "Packet Length Mean": "packet_length_mean",
    "Packet Length Std": "packet_length_std",
    "Packet Length Variance": "packet_length_variance",
    "FIN Flag Count": "fin_flag_count",
    "SYN Flag Count": "syn_flag_count",
    "RST Flag Count": "rst_flag_count",
    "PSH Flag Count": "psh_flag_count",
    "ACK Flag Count": "ack_flag_count",
    "URG Flag Count": "urg_flag_count",
    "ECE Flag Count": "ece_flag_count",
    "CWE Flag Count": "cwr_flag_count",   # CIC lo etiqueta "CWE" pero es el flag CWR
    "Down/Up Ratio": "down_up_ratio",
    "Average Packet Size": "average_packet_size",
    "Avg Fwd Segment Size": "avg_fwd_segment_size",
    "Avg Bwd Segment Size": "avg_bwd_segment_size",
    "Fwd Avg Bytes/Bulk": "fwd_avg_bytes_bulk",
    "Fwd Avg Packets/Bulk": "fwd_avg_packets_bulk",
    "Fwd Avg Bulk Rate": "fwd_avg_bulk_rate",
    "Bwd Avg Bytes/Bulk": "bwd_avg_bytes_bulk",
    "Bwd Avg Packets/Bulk": "bwd_avg_packets_bulk",
    "Bwd Avg Bulk Rate": "bwd_avg_bulk_rate",
    "Subflow Fwd Packets": "subflow_fwd_packets",
    "Subflow Fwd Bytes": "subflow_fwd_bytes",
    "Subflow Bwd Packets": "subflow_bwd_packets",
    "Subflow Bwd Bytes": "subflow_bwd_bytes",
    "Init_Win_bytes_forward": "init_win_bytes_forward",
    "Init_Win_bytes_backward": "init_win_bytes_backward",
    "act_data_pkt_fwd": "act_data_pkt_fwd",
    "min_seg_size_forward": "min_seg_size_forward",
    "Active Mean": "active_mean",
    "Active Std": "active_std",
    "Active Max": "active_max",
    "Active Min": "active_min",
    "Idle Mean": "idle_mean",
    "Idle Std": "idle_std",
    "Idle Max": "idle_max",
    "Idle Min": "idle_min",
}


def _norm(s):
    """Normaliza una cabecera: minúsculas y solo alfanuméricos."""
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


# Mapa normalizado -> canónico (tolera espacios/guiones/casing distintos entre versiones)
_CIC_TO_CANON = {_norm(k): v for k, v in _CIC_HEADERS.items()}
_LABEL_KEYS = {_norm(x) for x in ("Label", "label", " Label")}


def _read_csv_any(path):
    if os.path.isdir(path):
        files = sorted(glob.glob(os.path.join(path, "*.csv")))
        if not files:
            raise FileNotFoundError(f"No se encontraron CSV en {path}")
        return pd.concat((pd.read_csv(f, low_memory=False) for f in files), ignore_index=True)
    return pd.read_csv(path, low_memory=False)


def load_dataset(path):
    """Carga un dataset CIC-IDS y lo alinea al conjunto canónico de features.

    Devuelve: X (DataFrame con FEATURE_COLUMNS en orden), y_bin (0=benigno,
    1=ataque), y_multi (códigos enteros), class_names (lista, índice = código)."""
    df = _read_csv_any(path)

    # Renombra columnas a canónico por nombre normalizado
    rename, label_col = {}, None
    for col in df.columns:
        n = _norm(col)
        if n in _CIC_TO_CANON:
            rename[col] = _CIC_TO_CANON[n]
        elif n in _LABEL_KEYS:
            label_col = col
    df = df.rename(columns=rename)

    if label_col is None:
        raise ValueError("No se encontró columna 'Label' en el dataset")

    # Asegura todas las features (rellena las ausentes con 0)
    missing = [c for c in FEATURE_COLUMNS if c not in df.columns]
    for c in missing:
        df[c] = 0.0
    if missing:
        print(f"[features] AVISO: {len(missing)} features ausentes rellenadas con 0: {missing}")

    X = df[FEATURE_COLUMNS].copy()
    X = X.apply(pd.to_numeric, errors="coerce")
    X = X.replace([np.inf, -np.inf], np.nan).fillna(0.0)

    labels = df[label_col].astype(str).str.strip()
    y_bin = (~labels.str.upper().str.startswith("BENIGN")).astype(int).to_numpy()

    class_names = sorted(labels.unique().tolist())
    code = {name: i for i, name in enumerate(class_names)}
    y_multi = labels.map(code).to_numpy()

    return X, y_bin, y_multi, class_names
