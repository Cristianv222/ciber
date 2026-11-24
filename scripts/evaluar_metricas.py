"""Evaluación por escenario de la cascada de detección (Tesis UPEC).

Calcula, a partir de los flujos clasificados por el sistema, las cinco métricas
de la sección 3.3.2 (DR/Recall, Precisión, F1-Score y FPR) y las matrices de
confusión, de forma global y por escenario (E1–E6).

Entrada: un CSV exportado del sistema (p. ej. desde PostgreSQL de la VM3) con,
como mínimo, dos columnas:
    - etiqueta_real   (y_true : clase verdadera del flujo)
    - clasificacion   (y_pred : clase predicha por la cascada)
Y, opcionalmente:
    - escenario       (E1..E6) para desglosar las métricas por escenario.

Uso:
    python3 evaluar_metricas.py flujos.csv \
        --col-true etiqueta_real --col-pred clasificacion \
        --col-escenario escenario --benigno Benign --out resultados/
"""
import argparse, os
import numpy as np
import pandas as pd
from sklearn.metrics import confusion_matrix
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def metricas_binarias(y_true, y_pred, benigno):
    """DR, Precisión, F1 y FPR tratando 'ataque' como positivo y benigno como negativo."""
    yt = (np.asarray(y_true) != benigno).astype(int)   # 1 = ataque, 0 = benigno
    yp = (np.asarray(y_pred) != benigno).astype(int)
    tn, fp, fn, tp = confusion_matrix(yt, yp, labels=[0, 1]).ravel()
    dr  = tp / (tp + fn) if (tp + fn) else float("nan")   # Recall / Tasa de detección
    pr  = tp / (tp + fp) if (tp + fp) else float("nan")   # Precisión
    f1  = 2 * pr * dr / (pr + dr) if (pr + dr) else float("nan")
    fpr = fp / (fp + tn) if (fp + tn) else float("nan")   # Tasa de falsos positivos
    return dict(TP=tp, TN=tn, FP=fp, FN=fn, DR=dr, Precision=pr, F1=f1, FPR=fpr)


def guardar_matriz(y_true, y_pred, titulo, ruta):
    clases = sorted(set(list(y_true) + list(y_pred)))
    cm = confusion_matrix(y_true, y_pred, labels=clases)
    fig, ax = plt.subplots(figsize=(1.4 + 0.9 * len(clases), 1.2 + 0.9 * len(clases)))
    im = ax.imshow(cm, cmap="Blues")
    ax.set_xticks(range(len(clases))); ax.set_xticklabels(clases, rotation=45, ha="right")
    ax.set_yticks(range(len(clases))); ax.set_yticklabels(clases)
    ax.set_xlabel("Predicción"); ax.set_ylabel("Etiqueta real"); ax.set_title(titulo)
    for i in range(len(clases)):
        for j in range(len(clases)):
            ax.text(j, i, int(cm[i, j]), ha="center", va="center",
                    color="white" if cm[i, j] > cm.max() / 2 else "black")
    fig.tight_layout(); fig.savefig(ruta, dpi=160); plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--col-true", default="etiqueta_real")
    ap.add_argument("--col-pred", default="clasificacion")
    ap.add_argument("--col-escenario", default="escenario")
    ap.add_argument("--benigno", default="Benign")
    ap.add_argument("--out", default="resultados")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    df = pd.read_csv(a.csv)
    yt, yp = df[a.col_true].astype(str), df[a.col_pred].astype(str)

    filas = []
    # --- Global ---
    g = metricas_binarias(yt, yp, a.benigno); g["Escenario"] = "GLOBAL"; filas.append(g)
    guardar_matriz(yt, yp, "Matriz de confusión global", os.path.join(a.out, "cm_global.png"))

    # --- Por escenario ---
    if a.col_escenario in df.columns:
        for esc, sub in df.groupby(a.col_escenario):
            m = metricas_binarias(sub[a.col_true].astype(str), sub[a.col_pred].astype(str), a.benigno)
            m["Escenario"] = esc; filas.append(m)
            guardar_matriz(sub[a.col_true].astype(str), sub[a.col_pred].astype(str),
                           f"Matriz de confusión – {esc}", os.path.join(a.out, f"cm_{esc}.png"))

    res = pd.DataFrame(filas)[["Escenario", "TP", "TN", "FP", "FN", "DR", "Precision", "F1", "FPR"]]
    for c in ["DR", "Precision", "F1", "FPR"]:
        res[c] = (res[c] * 100).round(2)
    res.to_csv(os.path.join(a.out, "metricas_por_escenario.csv"), index=False)
    print(res.to_string(index=False))
    print(f"\nResultados y matrices guardados en: {a.out}/")
    print("Metas: DR>=95% | Precision>=90% | F1>=92% | FPR<=5%")


if __name__ == "__main__":
    main()
