from django.db import models


class Flow(models.Model):
    id = models.BigAutoField(primary_key=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    src_ip = models.GenericIPAddressField()
    src_port = models.IntegerField()
    dst_ip = models.GenericIPAddressField()
    dst_port = models.IntegerField()
    protocol = models.IntegerField()
    label = models.CharField(max_length=50, default='unlabeled')

    # Resultados del pipeline autónomo (poblados por los agentes SPADE vía API)
    attack_type = models.CharField(max_length=50, null=True, blank=True)          # Detector
    confidence = models.FloatField(null=True, blank=True)                         # Detector
    detector_stage = models.CharField(max_length=30, null=True, blank=True)       # xgboost / cnn_lstm / autoencoder
    cvss_score = models.FloatField(null=True, blank=True)                         # Decision (CVSS v4.0)
    action_taken = models.CharField(max_length=100, null=True, blank=True)        # Response
    processed_at = models.DateTimeField(null=True, blank=True)                    # Marca de procesamiento del pipeline

    # Métricas de duración y volúmenes
    flow_duration = models.BigIntegerField(null=True, blank=True)
    total_fwd_packets = models.BigIntegerField(null=True, blank=True)
    total_bwd_packets = models.BigIntegerField(null=True, blank=True)
    total_length_of_fwd_packets = models.BigIntegerField(null=True, blank=True)
    total_length_of_bwd_packets = models.BigIntegerField(null=True, blank=True)

    # Longitud de paquetes Forward
    fwd_packet_length_max = models.FloatField(null=True, blank=True)
    fwd_packet_length_min = models.FloatField(null=True, blank=True)
    fwd_packet_length_mean = models.FloatField(null=True, blank=True)
    fwd_packet_length_std = models.FloatField(null=True, blank=True)

    # Longitud de paquetes Backward
    bwd_packet_length_max = models.FloatField(null=True, blank=True)
    bwd_packet_length_min = models.FloatField(null=True, blank=True)
    bwd_packet_length_mean = models.FloatField(null=True, blank=True)
    bwd_packet_length_std = models.FloatField(null=True, blank=True)

    # Tasas de tráfico (Rates)
    flow_bytes_s = models.FloatField(null=True, blank=True)
    flow_packets_s = models.FloatField(null=True, blank=True)

    # Tiempos entre arribos (Flow IAT)
    flow_iat_mean = models.FloatField(null=True, blank=True)
    flow_iat_std = models.FloatField(null=True, blank=True)
    flow_iat_max = models.FloatField(null=True, blank=True)
    flow_iat_min = models.FloatField(null=True, blank=True)

    # Tiempos entre arribos Forward (Fwd IAT)
    fwd_iat_total = models.FloatField(null=True, blank=True)
    fwd_iat_mean = models.FloatField(null=True, blank=True)
    fwd_iat_std = models.FloatField(null=True, blank=True)
    fwd_iat_max = models.FloatField(null=True, blank=True)
    fwd_iat_min = models.FloatField(null=True, blank=True)

    # Tiempos entre arribos Backward (Bwd IAT)
    bwd_iat_total = models.FloatField(null=True, blank=True)
    bwd_iat_mean = models.FloatField(null=True, blank=True)
    bwd_iat_std = models.FloatField(null=True, blank=True)
    bwd_iat_max = models.FloatField(null=True, blank=True)
    bwd_iat_min = models.FloatField(null=True, blank=True)

    # Flags PSH y URG por dirección
    fwd_psh_flags = models.BigIntegerField(null=True, blank=True)
    bwd_psh_flags = models.BigIntegerField(null=True, blank=True)
    fwd_urg_flags = models.BigIntegerField(null=True, blank=True)
    bwd_urg_flags = models.BigIntegerField(null=True, blank=True)

    # Cabeceras y Tasas por dirección
    fwd_header_length = models.BigIntegerField(null=True, blank=True)
    bwd_header_length = models.BigIntegerField(null=True, blank=True)
    fwd_packets_s = models.FloatField(null=True, blank=True)
    bwd_packets_s = models.FloatField(null=True, blank=True)

    # Estadísticas globales de longitud de paquete
    min_packet_length = models.FloatField(null=True, blank=True)
    max_packet_length = models.FloatField(null=True, blank=True)
    packet_length_mean = models.FloatField(null=True, blank=True)
    packet_length_std = models.FloatField(null=True, blank=True)
    packet_length_variance = models.FloatField(null=True, blank=True)

    # Banderas TCP
    fin_flag_count = models.BigIntegerField(null=True, blank=True)
    syn_flag_count = models.BigIntegerField(null=True, blank=True)
    rst_flag_count = models.BigIntegerField(null=True, blank=True)
    psh_flag_count = models.BigIntegerField(null=True, blank=True)
    ack_flag_count = models.BigIntegerField(null=True, blank=True)
    urg_flag_count = models.BigIntegerField(null=True, blank=True)
    ece_flag_count = models.BigIntegerField(null=True, blank=True)
    cwr_flag_count = models.BigIntegerField(null=True, blank=True)

    # Ratios y Promedios
    down_up_ratio = models.FloatField(null=True, blank=True)
    average_packet_size = models.FloatField(null=True, blank=True)
    avg_fwd_segment_size = models.FloatField(null=True, blank=True)
    avg_bwd_segment_size = models.FloatField(null=True, blank=True)

    # Estadísticas Bulk
    fwd_avg_bytes_bulk = models.FloatField(null=True, blank=True)
    fwd_avg_packets_bulk = models.FloatField(null=True, blank=True)
    fwd_avg_bulk_rate = models.FloatField(null=True, blank=True)
    bwd_avg_bytes_bulk = models.FloatField(null=True, blank=True)
    bwd_avg_packets_bulk = models.FloatField(null=True, blank=True)
    bwd_avg_bulk_rate = models.FloatField(null=True, blank=True)

    # Estadísticas de Subflujo
    subflow_fwd_packets = models.BigIntegerField(null=True, blank=True)
    subflow_fwd_bytes = models.BigIntegerField(null=True, blank=True)
    subflow_bwd_packets = models.BigIntegerField(null=True, blank=True)
    subflow_bwd_bytes = models.BigIntegerField(null=True, blank=True)

    # Ventanas iniciales
    init_win_bytes_forward = models.BigIntegerField(null=True, blank=True)
    init_win_bytes_backward = models.BigIntegerField(null=True, blank=True)
    act_data_pkt_fwd = models.BigIntegerField(null=True, blank=True)
    min_seg_size_forward = models.BigIntegerField(null=True, blank=True)

    # Tiempos de Actividad e Inactividad
    active_mean = models.FloatField(null=True, blank=True)
    active_std = models.FloatField(null=True, blank=True)
    active_max = models.FloatField(null=True, blank=True)
    active_min = models.FloatField(null=True, blank=True)
    idle_mean = models.FloatField(null=True, blank=True)
    idle_std = models.FloatField(null=True, blank=True)
    idle_max = models.FloatField(null=True, blank=True)
    idle_min = models.FloatField(null=True, blank=True)

    class Meta:
        db_table = 'flows'
        managed = False
        ordering = ['-timestamp']
        verbose_name = 'Flujo de Red'
        verbose_name_plural = 'Flujos de Red'

    def __str__(self):
        return f"[{self.timestamp}] {self.src_ip}:{self.src_port} -> {self.dst_ip}:{self.dst_port} ({self.label})"


class HoneypotEvent(models.Model):
    id = models.BigAutoField(primary_key=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    honeypot_name = models.CharField(max_length=50, default='generic_honeypot')
    attacker_ip = models.GenericIPAddressField()
    attacker_port = models.IntegerField(null=True, blank=True)
    target_ip = models.GenericIPAddressField()
    target_port = models.IntegerField(null=True, blank=True)
    service = models.CharField(max_length=30, default='unknown')
    username_attempted = models.CharField(max_length=100, null=True, blank=True)
    password_attempted = models.CharField(max_length=100, null=True, blank=True)
    command_executed = models.TextField(null=True, blank=True)
    payload_hash = models.CharField(max_length=64, null=True, blank=True)
    raw_event = models.JSONField(null=True, blank=True)

    class Meta:
        db_table = 'honeypot_events'
        managed = False
        ordering = ['-timestamp']
        verbose_name = 'Evento Honeypot'
        verbose_name_plural = 'Eventos Honeypot'

    def __str__(self):
        return f"[{self.timestamp}] Honeypot '{self.honeypot_name}': {self.attacker_ip} -> {self.service} ({self.username_attempted}:{self.password_attempted})"
