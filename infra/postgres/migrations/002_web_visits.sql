-- =============================================================================
-- MIGRACIÓN 002 — Tabla 'web_visits' (navegación web)
-- Aplicar sobre una BD existente (p. ej. la máquina de la universidad):
--   docker compose exec -T postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
--     < infra/postgres/migrations/002_web_visits.sql
-- Idempotente.
-- =============================================================================

CREATE TABLE IF NOT EXISTS web_visits (
    id              BIGSERIAL PRIMARY KEY,
    timestamp       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    src_ip          INET NOT NULL,
    dst_ip          INET,
    dst_port        INTEGER,
    source          VARCHAR(10) NOT NULL DEFAULT 'tls',
    domain          VARCHAR(255) NOT NULL,
    url_path        TEXT,
    method          VARCHAR(10)
);

CREATE INDEX IF NOT EXISTS idx_web_timestamp ON web_visits (timestamp);
CREATE INDEX IF NOT EXISTS idx_web_domain    ON web_visits (domain);
CREATE INDEX IF NOT EXISTS idx_web_src       ON web_visits (src_ip);
