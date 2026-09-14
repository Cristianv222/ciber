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
