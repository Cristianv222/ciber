# apps/cicflowmeter — Ingesta de flujos (Capa 2)

Captura tráfico de red, lo agrupa en **flujos bidireccionales** y extrae las ~80
características estilo **CIC-IDS** que almacena la tabla `flows`. Es lo que "llena"
la base de datos para que el resto del pipeline (detector → decision → response)
tenga qué analizar.

## Archivos
- `flow.py` — modelo de flujo y cálculo de las ~80 features (nombres de columna
  idénticos a la tabla `flows`).
- `meter.py` — gestor de sesiones: abre flujos, los cierra por FIN/RST o timeout.
- `sinks.py` — sumideros: `ApiSink` (POST a la API) y `DbSink` (INSERT directo).
- `main.py` — punto de entrada (lee interfaz en vivo o un `.pcap`).

## Dónde se escriben los flujos (importante)
- **`INGEST_MODE=api`** (por defecto): `POST /api/flows/` → ORM de Django →
  dispara el signal `post_save` → **el WebSocket retransmite el flujo nuevo en
  vivo**. Recomendado para ver el sistema funcionando en tiempo real.
- **`INGEST_MODE=db`**: `INSERT` directo con psycopg2. Más rápido para tráfico
  alto, pero **no** dispara el WebSocket (los flujos solo se ven vía Grafana).

## Uso

### Desarrollo local (Mac) — sobre un archivo .pcap
`network_mode: host` no captura la interfaz real en Docker Desktop de Mac, así que
en local se trabaja sobre un `.pcap`. Coloca el archivo en `data/pcap/` y:

```bash
docker compose run --rm cicflowmeter \
  python main.py --mode pcap --pcap /data/pcap/muestra.pcap --sink api
```

O directamente con Python (sin Docker), teniendo el backend levantado:

```bash
pip install -r apps/cicflowmeter/requirements.txt
python apps/cicflowmeter/main.py --mode pcap --pcap data/pcap/muestra.pcap \
  --sink api --api-url http://localhost:8000
```

### Universidad (AlmaLinux) — captura del puerto SPAN en vivo
```bash
# Ajusta SPAN_INTERFACE en .env a la interfaz del SPAN
docker compose --profile ingest up -d --build cicflowmeter
docker compose logs -f cicflowmeter
```

## Parámetros (env / CLI)
| Env | CLI | Def. | Descripción |
|-----|-----|------|-------------|
| `CAPTURE_MODE` | `--mode` | `live` | `live` (interfaz) o `pcap` (archivo) |
| `SPAN_INTERFACE` | `--interface` | `eth0` | interfaz a capturar |
| `PCAP_FILE` | `--pcap` | — | ruta al `.pcap` |
| `INGEST_MODE` | `--sink` | `api` | `api` o `db` |
| `API_BASE_URL` | `--api-url` | `http://localhost:8000` | base de la API |
| `FLOW_TIMEOUT` | `--flow-timeout` | `120` | seg. para cerrar flujo inactivo |
| `ACTIVITY_TIMEOUT` | `--activity-timeout` | `5` | seg. que separan activo/idle |

## Notas de fidelidad
Las métricas estándar (duración, conteos, longitudes, IAT, flags, tasas,
active/idle) siguen las definiciones de CICFlowMeter. `subflow_*` usa clumping de
1 s y `*_bulk_*` la heurística de CICFlowMeter (grupos de ≥4 paquetes con separación
≤1 s). Pueden diferir ligeramente de la implementación Java original; conviene
entrenar los modelos (Fase 2) con features generadas por este mismo módulo para
evitar desajuste train/serve.
