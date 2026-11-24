"""Prueba de hipótesis: sistema propuesto (A) vs IDS convencional / Snort (B).

Contrasta la hipótesis de la sección 3.5.2 de la tesis:
    H0: no hay diferencia en el F1-score entre el sistema propuesto y el IDS convencional (mu_A = mu_B)
    H1: el sistema propuesto presenta un F1-score superior (mu_A > mu_B)
Criterio: si p < 0,05 se rechaza H0.

Procedimiento:
    1) Shapiro-Wilk sobre las diferencias (normalidad).
    2) Si son normales -> prueba t pareada (ttest_rel); si no -> Wilcoxon.
    3) Reporta estadístico, valor p, decisión e intervalo de confianza del 95%.

Entrada: un CSV con una fila por escenario y las columnas:
    escenario, f1_sistema, f1_snort     (valores de F1 en [0,1] o en %)

Uso:
    python3 prueba_hipotesis.py comparacion.csv
"""
import argparse
import numpy as np
import pandas as pd
from scipy import stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv", help="CSV con columnas: escenario, f1_sistema, f1_snort")
    ap.add_argument("--col-a", default="f1_sistema")
    ap.add_argument("--col-b", default="f1_snort")
    a = ap.parse_args()

    df = pd.read_csv(a.csv)
    A = df[a.col_a].to_numpy(dtype=float)
    B = df[a.col_b].to_numpy(dtype=float)
    if A.max() > 1.5:     # vienen en porcentaje -> a proporción
        A, B = A / 100.0, B / 100.0
    d = A - B
    n = len(d)

    print(f"Escenarios pareados: {n}")
    print(f"F1 medio  A (sistema) = {A.mean():.4f}")
    print(f"F1 medio  B (Snort)   = {B.mean():.4f}")
    print(f"Diferencia media (A-B) = {d.mean():.4f}")

    # 1) Normalidad de las diferencias
    W, p_sw = stats.shapiro(d)
    print(f"\nShapiro-Wilk (normalidad de diferencias): W={W:.3f}, p={p_sw:.4f}")

    # 2) Prueba adecuada (una cola: A > B)
    if p_sw > 0.05:
        t, p_two = stats.ttest_rel(A, B)
        p = p_two / 2 if t > 0 else 1 - p_two / 2
        prueba = f"t de Student pareada: t={t:.3f}"
    else:
        try:
            w, p_two = stats.wilcoxon(A, B, alternative="greater")
            p = p_two
        except ValueError:
            w, p_two = stats.wilcoxon(A, B)
            p = p_two / 2
        prueba = f"Wilcoxon (no paramétrica): W={w:.3f}"

    # 3) IC 95% de la diferencia media
    if n > 1:
        ic = stats.t.interval(0.95, n - 1, loc=d.mean(), scale=stats.sem(d))
        print(f"IC 95% de la diferencia media: ({ic[0]:.4f}, {ic[1]:.4f})")

    print(f"\n{prueba}, p (una cola) = {p:.4f}")
    if p < 0.05 and A.mean() > B.mean():
        print(">> Se RECHAZA H0: el sistema propuesto tiene F1 estadísticamente superior (p < 0,05).")
    else:
        print(">> No se rechaza H0: no hay evidencia de diferencia significativa.")


if __name__ == "__main__":
    main()
