-- =============================================================================
-- ESQUEMA DE BASE DE DATOS PARA RECOLECCIÓN DE FLUJOS DE RED (CICFlowMeter)
-- Proyecto de Tesis - Sistema Autónomo de Monitoreo de Red
-- =============================================================================

CREATE TABLE IF NOT EXISTS flows (
    -- Metadatos del flujo e Identificador Único
    id                              BIGSERIAL PRIMARY KEY,
    timestamp                       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    src_ip                          INET NOT NULL,
    src_port                        INTEGER NOT NULL,
    dst_ip                          INET NOT NULL,
    dst_port                        INTEGER NOT NULL,
    protocol                        INTEGER NOT NULL,
    label                           VARCHAR(50) NOT NULL DEFAULT 'unlabeled',

    -- Métrica Duración y Conteos de Paquetes/Bytes
    flow_duration                   BIGINT,
    total_fwd_packets               BIGINT,
    total_bwd_packets               BIGINT,
    total_length_of_fwd_packets     BIGINT,
    total_length_of_bwd_packets     BIGINT,

    -- Longitud de Paquetes Forward
    fwd_packet_length_max           DOUBLE PRECISION,
    fwd_packet_length_min           DOUBLE PRECISION,
    fwd_packet_length_mean          DOUBLE PRECISION,
    fwd_packet_length_std           DOUBLE PRECISION,

    -- Longitud de Paquetes Backward
    bwd_packet_length_max           DOUBLE PRECISION,
    bwd_packet_length_min           DOUBLE PRECISION,
    bwd_packet_length_mean          DOUBLE PRECISION,
    bwd_packet_length_std           DOUBLE PRECISION,

    -- Rendimiento del Flujo (Flow Rates)
    flow_bytes_s                    DOUBLE PRECISION,
    flow_packets_s                  DOUBLE PRECISION,

    -- Tiempos entre Arribos del Flujo Completo (Flow IAT)
    flow_iat_mean                   DOUBLE PRECISION,
    flow_iat_std                    DOUBLE PRECISION,
    flow_iat_max                    DOUBLE PRECISION,
    flow_iat_min                    DOUBLE PRECISION,

    -- Tiempos entre Arribos Forward (Fwd IAT)
    fwd_iat_total                   DOUBLE PRECISION,
    fwd_iat_mean                    DOUBLE PRECISION,
    fwd_iat_std                     DOUBLE PRECISION,
    fwd_iat_max                     DOUBLE PRECISION,
    fwd_iat_min                     DOUBLE PRECISION,

    -- Tiempos entre Arribos Backward (Bwd IAT)
    bwd_iat_total                   DOUBLE PRECISION,
    bwd_iat_mean                    DOUBLE PRECISION,
    bwd_iat_std                     DOUBLE PRECISION,
    bwd_iat_max                     DOUBLE PRECISION,
    bwd_iat_min                     DOUBLE PRECISION,

    -- Flags PSH y URG por Dirección
    fwd_psh_flags                   BIGINT,
    bwd_psh_flags                   BIGINT,
    fwd_urg_flags                   BIGINT,
    bwd_urg_flags                   BIGINT,

    -- Cabeceras y Tasas por Dirección
    fwd_header_length               BIGINT,
    bwd_header_length               BIGINT,
    fwd_packets_s                   DOUBLE PRECISION,
    bwd_packets_s                   DOUBLE PRECISION,

    -- Estadísticas Globales de Longitud de Paquetes
    min_packet_length               DOUBLE PRECISION,
    max_packet_length               DOUBLE PRECISION,
    packet_length_mean              DOUBLE PRECISION,
    packet_length_std               DOUBLE PRECISION,
    packet_length_variance          DOUBLE PRECISION,

    -- Conteos Globales de Flags TCP
    fin_flag_count                  BIGINT,
    syn_flag_count                  BIGINT,
    rst_flag_count                  BIGINT,
    psh_flag_count                  BIGINT,
    ack_flag_count                  BIGINT,
    urg_flag_count                  BIGINT,
    ece_flag_count                  BIGINT,
    cwr_flag_count                  BIGINT,

    -- Ratios y Promedios de Segmento
    down_up_ratio                   DOUBLE PRECISION,
    average_packet_size             DOUBLE PRECISION,
    avg_fwd_segment_size            DOUBLE PRECISION,
    avg_bwd_segment_size            DOUBLE PRECISION,

    -- Estadísticas Bulk (Tráfico Masivo)
    fwd_avg_bytes_bulk              DOUBLE PRECISION,
    fwd_avg_packets_bulk            DOUBLE PRECISION,
    fwd_avg_bulk_rate               DOUBLE PRECISION,
    bwd_avg_bytes_bulk              DOUBLE PRECISION,
    bwd_avg_packets_bulk            DOUBLE PRECISION,
    bwd_avg_bulk_rate               DOUBLE PRECISION,

    -- Estadísticas de Subflujo (Subflows)
    subflow_fwd_packets             BIGINT,
    subflow_fwd_bytes               BIGINT,
    subflow_bwd_packets             BIGINT,
    subflow_bwd_bytes               BIGINT,

    -- Ventanas Iniciales y Segmentos de Datos
    init_win_bytes_forward          BIGINT,
    init_win_bytes_backward         BIGINT,
    act_data_pkt_fwd                BIGINT,
    min_seg_size_forward            BIGINT,

    -- Tiempos de Actividad e Inactividad (Active / Idle)
    active_mean                     DOUBLE PRECISION,
    active_std                      DOUBLE PRECISION,
    active_max                      DOUBLE PRECISION,
    active_min                      DOUBLE PRECISION,
    idle_mean                       DOUBLE PRECISION,
    idle_std                        DOUBLE PRECISION,
    idle_max                        DOUBLE PRECISION,
    idle_min                        DOUBLE PRECISION
);

-- =============================================================================
-- ÍNDICES PARA OPTIMIZACIÓN DE CONSULTAS Y DASHBOARDS EN GRAFANA
-- =============================================================================
CREATE INDEX IF NOT EXISTS idx_flows_timestamp ON flows (timestamp);
CREATE INDEX IF NOT EXISTS idx_flows_label ON flows (label);
CREATE INDEX IF NOT EXISTS idx_flows_src_ip ON flows (src_ip);
CREATE INDEX IF NOT EXISTS idx_flows_dst_ip ON flows (dst_ip);
