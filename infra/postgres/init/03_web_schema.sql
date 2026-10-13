-- =============================================================================
-- ESQUEMA DE NAVEGACIÓN WEB (visibilidad de sitios visitados)
-- Proyecto de Tesis - Sistema Autónomo de Monitoreo de Red
-- =============================================================================
-- Registra los sitios/dominios visitados, extraídos sin descifrar TLS:
--   - source='tls'  -> dominio del SNI del handshake TLS (HTTPS)
--   - source='dns'  -> dominio consultado por DNS
--   - source='http' -> Host + ruta de peticiones HTTP en claro (incluye url_path)
-- =============================================================================

CREATE TABLE IF NOT EXISTS web_visits (
    id              BIGSERIAL PRIMARY KEY,
    timestamp       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    src_ip          INET NOT NULL,
    dst_ip          INET,
    dst_port        INTEGER,
    source          VARCHAR(10) NOT NULL DEFAULT 'tls',  -- tls | dns | http
    domain          VARCHAR(255) NOT NULL,
    url_path        TEXT,         -- solo HTTP plano
    method          VARCHAR(10)   -- solo HTTP plano
);

CREATE INDEX IF NOT EXISTS idx_web_timestamp ON web_visits (timestamp);
CREATE INDEX IF NOT EXISTS idx_web_domain    ON web_visits (domain);
CREATE INDEX IF NOT EXISTS idx_web_src       ON web_visits (src_ip);
