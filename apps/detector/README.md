# apps/detector — Agente detector SPADE (Fase 3)

Agente inteligente que **lee** flujos sin clasificar de PostgreSQL, aplica la
cascada de ML y **escribe** el veredicto vía la API REST; si detecta una amenaza,
envía una alerta XMPP al **DecisionAgent** (Fase 4).

## Flujo de trabajo (cada `POLL_INTERVAL` s)
1. `SELECT ... FROM flows WHERE label = 'unlabeled'` (lectura directa, rápida).
2. Cascada por flujo:
   - **Etapa 1 — XGBoost** (features en crudo): tipo de ataque + confianza.
   - **Etapa 2 — CNN-LSTM** (features escaladas): ataque vs. benigno (si XGBoost duda).
   - **Etapa 3 — Autoencoder** (features escaladas): anomalía por error de reconstrucción.
3. `PATCH /api/flows/{id}/` con `label, attack_type, confidence, detector_stage,
   processed_at` → el signal dispara el WebSocket (`flow_updated`).
4. Si es amenaza → `Message` XMPP a `decision@ejabberd`.

> El orden de features se lee de `metadata.json` (no se duplica `features.py`).
> XGBoost usa features en crudo; CNN-LSTM y Autoencoder usan `scaler.pkl`.

## ⚠️ Prerrequisito
Necesita en `/models` (volumen `models`, montado solo-lectura):
`metadata.json`, `xgboost.pkl` y `scaler.pkl` **obligatorios**; `cnn_lstm.h5` y
`autoencoder.h5` opcionales (si faltan, se omiten esas etapas). **Ejecuta el
`trainer` (Fase 2) antes de levantar el detector**, o arrancará y fallará.

## Levantar
```bash
docker compose --profile training run --rm trainer   # 1) generar modelos
docker compose --profile agents up -d --build detector   # 2) arrancar detector
docker compose logs -f detector
```

## Parámetros (env)
| Env | Def. | Descripción |
|-----|------|-------------|
| `POLL_INTERVAL` | `5` | segundos entre sondeos |
| `BATCH_SIZE` | `100` | flujos por sondeo |
| `XGB_ATTACK_THRESHOLD` | `0.6` | confianza mín. para marcar ataque en etapa 1 |
| `XGB_BENIGN_THRESHOLD` | `0.8` | confianza mín. para cerrar como benigno en etapa 1 |
| `CNN_THRESHOLD` | `0.5` | prob. mín. de ataque en etapa 2 |
| `DETECTOR_JID` / `DECISION_JID` | `detector@ejabberd` / `decision@ejabberd` | JIDs XMPP |
| `MODELS_DIR` | `/models` | ruta de artefactos |
