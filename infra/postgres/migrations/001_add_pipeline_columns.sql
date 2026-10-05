-- =============================================================================
-- MIGRACIÓN 001 — Columnas del pipeline autónomo en la tabla 'flows'
-- Proyecto de Tesis - Sistema Autónomo de Monitoreo de Red
-- =============================================================================
--
-- CUÁNDO USAR ESTE SCRIPT:
--   El archivo infra/postgres/init/01_schema.sql SOLO se ejecuta cuando el
--   volumen de datos de PostgreSQL está vacío (primer arranque). Sobre una base
--   de datos que YA tiene datos (p. ej. la máquina de la universidad), el init
--   no se vuelve a correr, por lo que estas columnas deben agregarse a mano con
--   este script, SIN perder los datos existentes.
--
-- CÓMO APLICARLO (en la máquina de la U, con los servicios levantados):
--   docker compose exec -T postgres \
--     psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
--     < infra/postgres/migrations/001_add_pipeline_columns.sql
--
-- Es idempotente: se puede ejecutar varias veces sin error ni efectos duplicados.
-- =============================================================================

ALTER TABLE flows ADD COLUMN IF NOT EXISTS attack_type    VARCHAR(50);
ALTER TABLE flows ADD COLUMN IF NOT EXISTS confidence     DOUBLE PRECISION;
ALTER TABLE flows ADD COLUMN IF NOT EXISTS detector_stage VARCHAR(30);
ALTER TABLE flows ADD COLUMN IF NOT EXISTS cvss_score     DOUBLE PRECISION;
ALTER TABLE flows ADD COLUMN IF NOT EXISTS action_taken   VARCHAR(100);
ALTER TABLE flows ADD COLUMN IF NOT EXISTS processed_at   TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_flows_attack_type  ON flows (attack_type);
CREATE INDEX IF NOT EXISTS idx_flows_processed_at ON flows (processed_at);
