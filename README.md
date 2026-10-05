# Sistema Autónomo de Monitoreo de Red para Detección y Respuesta a Ataques

Proyecto de tesis de ingeniería enfocado en la construcción de un sistema autónomo de seguridad de red basado en agentes inteligentes (SPADE), orientado a la captura de tráfico, extracción de características de flujos, detección de anomalías mediante Machine Learning y respuesta automatizada a incidentes.

---

## 🏗️ Arquitectura General del Sistema

La solución se compone del siguiente flujo de datos y componentes:

```
                  [ Tráfico de Red (Puerto SPAN / PCAP) ]
                                     │
                                     ▼
                          ┌──────────────────────┐
                          │    CICFlowMeter      │ (Extracción de ~80 métricas)
                          └──────────┬───────────┘
                                     │
                                     ▼
                          ┌──────────────────────┐
                          │ PostgreSQL (Database)│ (Tabla estructurada 'flows')
                          └──────────┬───────────┘
                                     │
       ┌─────────────────────────────┼─────────────────────────────┐
       ▼                             ▼                             ▼
┌──────────────┐          ┌────────────────────┐      ┌─────────────────────────┐
│   Grafana    │          │   Backend Django   │      │ Sistema Agentes (SPADE) │
│ (Dashboards) │          │ (REST API & Admin) │      │ - Detector (ML)         │
└──────────────┘          └────────────────────┘      │ - Tomador de Decisiones │
                                                      │ - Agente de Respuesta   │
                                                      └─────────────────────────┘
```

---

## 🧩 Componentes del Proyecto

1. **Infraestructura Base y Backend**
   - **PostgreSQL 16**: Base de datos relacional para el almacenamiento de los flujos de red enriquecidos con las ~80 características estándar de datasets como CIC-IDS2017 / CIC-IDS2018.
   - **Django Backend (`apps/backend`)**: API REST (Django REST Framework), Panel de Administración (`Django Admin`) y capa ORM para la gestión de flujos, agentes y políticas de seguridad.
   - **Grafana**: Dashboard interactivo para la visualización del tráfico en tiempo real, monitoreo de métricas e indicadores de anomalías.

2. **Aplicaciones y Agentes (Fases Posteriores - `apps/`)**
   - `apps/cicflowmeter`: Módulo encargado de la captura continua de tráfico y generación de flujos.
   - `apps/detector`: Agente autónomo SPADE para el análisis de flujos mediante modelos de Machine Learning.
   - `apps/decision`: Agente encargado de la evaluación de políticas de seguridad y priorización de alertas.
   - `apps/response`: Agente de respuesta proactiva ante incidentes (mitigación y aislamiento).

---

## 🚀 Cómo Levantar el Entorno

### Requisitos Previos
- AlmaLinux 9 (o distribución equivalente)
- Docker Engine y `docker-compose-plugin`

### Pasos de Despliegue

1. **Configurar las variables de entorno:**
   Copia la plantilla `.env.example` para crear el archivo real `.env`:
   ```bash
   cp .env.example .env
   ```

2. **Definir credenciales:**
   Edita el archivo `.env` asignando contraseñas seguras.

3. **Iniciar los servicios:**
   Ejecuta Docker Compose en modo desatendido:
   ```bash
   docker compose up -d --build
   ```

4. **Crear superusuario para Django Admin:**
   ```bash
   docker compose exec backend python manage.py createsuperuser
   ```

5. **Acceso a los servicios:**
   - **Backend API REST**: `http://localhost:8000/api/flows/`
   - **Django Admin**: `http://localhost:8000/admin/`
   - **Grafana**: `http://localhost:3000` (Usuario inicial: `admin`)
   - **PostgreSQL**: `localhost:5432` (Base de datos: `netflows`, Usuario: `tesis`)
   - **ejabberd (XMPP)**: `localhost:5222` (c2s) · Admin web: `http://localhost:5280/admin`

---

## 📡 Servidor XMPP (ejabberd) para los Agentes SPADE

Los agentes SPADE (`detector`, `decision`, `response`) se comunican entre sí mediante
mensajería XMPP. El servicio `ejabberd` provee ese canal.

- **Dominio XMPP:** `ejabberd` (el nombre del servicio en `docker-compose`, resoluble por
  la red interna de Docker).
- **JIDs de los agentes:** `detector@ejabberd`, `decision@ejabberd`, `response@ejabberd`
  (más `admin@ejabberd` para administración).
- **Configuración:** `infra/ejabberd/ejabberd.yml`.
- **Credenciales:** definidas en `.env` (`XMPP_*_PASSWORD`). Copia las variables desde
  `.env.example` y asígnales contraseñas.

### Registro de usuarios XMPP

En el **primer arranque** los cuatro usuarios se registran automáticamente vía la
variable `CTL_ON_CREATE` del compose (usa los valores de `XMPP_*_PASSWORD` del `.env`).

Si necesitas registrarlos **manualmente** (por ejemplo, tras cambiar una contraseña),
ejecuta:

```bash
docker compose exec ejabberd ejabberdctl register detector ejabberd "$XMPP_DETECTOR_PASSWORD"
docker compose exec ejabberd ejabberdctl register decision ejabberd "$XMPP_DECISION_PASSWORD"
docker compose exec ejabberd ejabberdctl register response ejabberd "$XMPP_RESPONSE_PASSWORD"
```

Para verificar los usuarios registrados:

```bash
docker compose exec ejabberd ejabberdctl registered_users ejabberd
```

> Los agentes SPADE se conectan con `verify_security=False` porque en desarrollo
> ejabberd usa un certificado autofirmado generado en el primer arranque.

---

## 🗄️ Migraciones de esquema (columnas del pipeline)

Las tablas las crea el SQL de `infra/postgres/init/` **solo cuando el volumen de datos
está vacío**. Sobre una base de datos que ya tiene datos (p. ej. la máquina de la
universidad), aplica los scripts de `infra/postgres/migrations/` a mano, sin perder
datos. Por ejemplo, para añadir las columnas del pipeline:

```bash
docker compose exec -T postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  < infra/postgres/migrations/001_add_pipeline_columns.sql
```

En desarrollo local con BD vacía basta con recrear el volumen: `docker compose down -v`.

---

## 🔄 Pipeline autónomo completo (Capas y perfiles)

```
cicflowmeter ──▶ flows ──▶ detector ──[XMPP]──▶ decision ──[XMPP]──▶ response
 (ingesta)      (BD)     (cascada ML)  alerta   (CVSS v4.0)  orden    (iptables)
                              │             │                   │
                              └── API REST PATCH → signal → WebSocket (flow_updated) en vivo
```

Los servicios están organizados por **perfiles** de compose para arrancar solo lo necesario:

| Perfil | Servicios | Cuándo |
|--------|-----------|--------|
| *(base)* | postgres, redis, backend, ejabberd, grafana | siempre |
| `training` | trainer | a demanda, para entrenar modelos |
| `ingest` | cicflowmeter | captura de tráfico |
| `agents` | detector, decision, response | pipeline de detección/respuesta |

### Puesta en marcha (desarrollo local)
```bash
cp .env.example .env            # y rellena contraseñas
docker compose up -d --build                                  # 1) infra + backend
docker compose --profile training run --rm trainer           # 2) entrenar modelos (necesita CSV en data/datasets/)
docker compose --profile agents up -d --build                # 3) detector + decision + response
# 4) ingesta sobre un pcap (Mac) o el SPAN (Linux):
docker compose run --rm cicflowmeter python main.py --mode pcap --pcap /data/pcap/muestra.pcap
```

### Verificación end-to-end
Con el stack y los agentes arriba, siembra un flujo de prueba y comprueba que el
pipeline lo clasifica y puntúa:
```bash
./scripts/e2e_smoke.sh            # POST de un flujo → espera label/attack_type/cvss_score
```
Para ver la retransmisión en vivo por WebSocket: conéctate a `ws://localhost:8000/ws/flows/`
(p. ej. con `wscat -c ws://localhost:8000/ws/flows/`) y observa los mensajes
`new_flow` (ingesta) y `flow_updated` (clasificación / CVSS / acción).

---

## 🏭 Despliegue en producción (máquina de la universidad)

El código es el mismo; cambia el archivo de entorno y se aplican overrides de
seguridad con `docker-compose.prod.yml` (DEBUG=False, CORS/CSRF acotados, bloqueo
real con iptables, captura en vivo del SPAN).

```bash
cp .env.prod.example .env.prod    # y rellena secretos, ALLOWED_HOSTS, CORS, etc.

# Entrenar una vez:
docker compose --env-file .env.prod -f docker-compose.yml -f docker-compose.prod.yml \
  --profile training run --rm trainer

# Levantar todo el sistema:
docker compose --env-file .env.prod -f docker-compose.yml -f docker-compose.prod.yml \
  --profile ingest --profile agents up -d --build
```

> **Pendiente de endurecimiento (recomendado antes de exponer):** la API REST está
> hoy en `AllowAny`. Como los agentes escriben vía API, conviene añadir autenticación
> por token para los agentes antes del despliegue expuesto. Ver notas en el código.
