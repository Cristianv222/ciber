-- =============================================================================
-- ESQUEMA DE BASE DE DATOS PARA TELEMETRÍA DE HONEYPOTS
-- Proyecto de Tesis - Sistema Autónomo de Monitoreo de Red
-- =============================================================================

CREATE TABLE IF NOT EXISTS honeypot_events (
    id                  BIGSERIAL PRIMARY KEY,
    timestamp           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    honeypot_name       VARCHAR(50) NOT NULL DEFAULT 'generic_honeypot',
    attacker_ip         INET NOT NULL,
    attacker_port       INTEGER,
    target_ip           INET NOT NULL,
    target_port         INTEGER,
    service             VARCHAR(30) NOT NULL DEFAULT 'unknown',
    username_attempted  VARCHAR(100),
    password_attempted  VARCHAR(100),
    command_executed    TEXT,
    payload_hash        VARCHAR(64),
    raw_event           JSONB
);

-- ÍNDICES PARA OPTIMIZACIÓN DE CONSULTAS Y GRAFANA
CREATE INDEX IF NOT EXISTS idx_honeypot_timestamp ON honeypot_events (timestamp);
CREATE INDEX IF NOT EXISTS idx_honeypot_attacker_ip ON honeypot_events (attacker_ip);
CREATE INDEX IF NOT EXISTS idx_honeypot_service ON honeypot_events (service);
