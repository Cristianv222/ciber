# models/ — Entrenamiento de la cascada de detección (Fase 2)

Entrena los tres modelos que usa el **detector** (Fase 3) y exporta los artefactos
a un volumen `/models` compartido.

## Artefactos generados
| Archivo | Modelo / Framework | Rol en la cascada (Tesis UPEC) | Métrica Test (1M) |
|---|---|---|---|
| `xgboost.pkl` | XGBoost (árboles) | Etapa 1 — Filtro rápido multiclase / descarte de benignos | Accuracy: **98.12%**, F1: **98.16%** |
| `cnn_lstm.pt` | CNN-LSTM (PyTorch) | Etapa 2 — Clasificador multiclase de amenazas sospechosas | Accuracy: **91.10%**, F1: **90.56%** |
| `autoencoder.pt` | Autoencoder (PyTorch) | Etapa 3 — Detección no supervisada de anomalías / día cero | Umbral (p99): **0.973276** |
| `scaler.pkl` | StandardScaler | Normalización z-score para CNN-LSTM y Autoencoder | — |
| `metadata.json` | JSON | 78 features, 6 clases (`Benign`, `BruteForce`, `DDoS`, `DoS`, `Exploit`, `PortScan`) | — |

> **XGBoost** usa las features en crudo; **CNN-LSTM** y **Autoencoder** usan las
> features escaladas con `scaler.pkl`. El **orden de features** está fijado en
> `features.py::FEATURE_COLUMNS` y coincide con las columnas de `flows` y con lo
> que produce `apps/cicflowmeter` → sin desajuste train/serve.

## Dataset
Coloca los CSV de **CIC-IDS2017/2018** en `data/datasets/` (ignorados por git).
`features.py` traduce automáticamente las cabeceras del dataset a los nombres
canónicos; las features ausentes se rellenan con 0 (con aviso).

## Cómo entrenar (a demanda, perfil `training`)
```bash
# Construye la imagen y ejecuta el entrenamiento una vez:
docker compose --profile training run --rm trainer

# O con hiperparámetros:
docker compose --profile training run --rm \
  -e EPOCHS=25 -e BATCH_SIZE=512 trainer
```
Los artefactos quedan en el volumen `models`, que el **detector** monta en `/models`.

## ⚠️ Prerrequisito del detector
El detector (Fase 3) **necesita `xgboost.pkl`, `scaler.pkl` y `metadata.json`
presentes en `/models` antes de arrancar**, y `cnn_lstm.h5` / `autoencoder.h5`
para las etapas 2 y 3. Ejecuta el `trainer` **antes** de levantar el detector.

## Parámetros (env / CLI)
| Env | CLI | Def. | Descripción |
|-----|-----|------|-------------|
| `DATASET_PATH` | `--dataset` | `/data/datasets` | CSV o carpeta de CSV |
| `OUT_DIR` | `--out` | `/models` | destino de artefactos |
| `TEST_SIZE` | `--test-size` | `0.2` | proporción de test |
| `EPOCHS` | `--epochs` | `15` | épocas de las redes Keras |
| `BATCH_SIZE` | `--batch-size` | `256` | tamaño de batch |
| `AE_PERCENTILE` | `--ae-percentile` | `99` | percentil para el umbral del autoencoder |
