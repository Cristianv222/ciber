from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Count, Q
from django.db.models.functions import TruncDay
from .models import Flow, HoneypotEvent, WebVisit
from .serializers import FlowSerializer, HoneypotEventSerializer, WebVisitSerializer


class FlowViewSet(viewsets.ModelViewSet):
    queryset = Flow.objects.all()
    serializer_class = FlowSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['src_ip', 'dst_ip', 'label']
    ordering_fields = ['timestamp', 'flow_duration', 'total_fwd_packets']
    ordering = ['-timestamp']

    def get_queryset(self):
        queryset = super().get_queryset()
        label = self.request.query_params.get('label', None)
        src_ip = self.request.query_params.get('src_ip', None)
        dst_ip = self.request.query_params.get('dst_ip', None)

        if label:
            queryset = queryset.filter(label__iexact=label)
        if src_ip:
            queryset = queryset.filter(src_ip=src_ip)
        if dst_ip:
            queryset = queryset.filter(dst_ip=dst_ip)

        return queryset

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Devuelve un resumen de conteo de flujos por etiqueta (label)."""
        stats = Flow.objects.values('label').annotate(total=Count('id')).order_by('-total')
        total_flows = Flow.objects.count()
        return Response({
            'total_flows': total_flows,
            'labels_distribution': stats
        })

    @action(detail=False, methods=['get'])
    def timeline(self, request):
        """Serie de flujos benignos vs. amenazas repartida en N tramos por orden de
        llegada (ntile), para la gráfica de velas del Dashboard. Robusta aunque los
        flujos se hayan insertado en un rango de tiempo corto."""
        from django.db import connection
        try:
            n = max(5, min(60, int(request.query_params.get('buckets', 30))))
        except (TypeError, ValueError):
            n = 30
        sql = """
            SELECT bucket,
                   count(*) FILTER (WHERE lower(label) IN ('benign','unlabeled','normal')) AS benign,
                   count(*) FILTER (WHERE lower(label) NOT IN ('benign','unlabeled','normal') AND label IS NOT NULL) AS threat,
                   min(ts) AS ts
            FROM (
                SELECT label, timestamp AS ts, ntile(%s) OVER (ORDER BY id) AS bucket
                FROM flows
            ) t
            GROUP BY bucket
            ORDER BY bucket;
        """
        series = []
        with connection.cursor() as cur:
            cur.execute(sql, [n])
            for bucket, benign, threat, ts in cur.fetchall():
                total = (benign or 0) + (threat or 0)
                series.append({
                    'i': bucket,
                    'date': ts.isoformat() if ts else None,
                    'benign': benign or 0,
                    'threat': threat or 0,
                    'total': total,
                    'benign_pct': round((benign or 0) / total * 100, 1) if total else 0,
                })
        return Response({'series': series})

    @action(detail=False, methods=['get'])
    def attack_map(self, request):
        """Ataques REALES detectados por el pipeline (tabla `flows`), geolocalizados
        por `src_ip` para el globo mundial.

        Agrupa por ubicación e incluye, por cada punto, una muestra de los ataques
        reales con su clasificación (attack_type, CVSS, confianza, etapa del detector,
        puerto destino y hora) para poder mostrar la información al hacer clic.
        El `target` es la red monitoreada (destino de los arcos)."""
        import os
        from .geo import locate

        import ipaddress

        # Exclusión de benignos insensible a mayúsculas (benign/BENIGN/unlabeled/normal)
        NON_ATTACK_RE = r'^(benign|unlabeled|normal)$'
        limit = int(request.query_params.get('limit', 5000))

        qs = (
            Flow.objects
            .exclude(label__iregex=NON_ATTACK_RE)
            .exclude(label__isnull=True)
            .order_by('-timestamp')
            .values('id', 'src_ip', 'dst_port', 'label', 'attack_type',
                    'confidence', 'cvss_score', 'detector_stage', 'timestamp')[:limit]
        )

        target = {
            'lat': float(os.environ.get('HONEYPOT_LAT', '-0.1807')),
            'lon': float(os.environ.get('HONEYPOT_LON', '-78.4678')),
            'label': os.environ.get('HONEYPOT_LABEL', 'Red monitoreada (Ecuador)'),
        }

        points = {}
        by_country = {}
        by_type = {}
        geo_cache = {}
        total_attacks = 0
        external = 0
        internal = 0

        # Nodo "red local": ataques con IP privada/reservada = atacante DENTRO de la
        # red monitoreada. Es metadato real (IP de origen), no un lugar al azar.
        internal_pt = {
            'lat': target['lat'] + 2.4, 'lon': target['lon'] - 2.4,
            'country': 'Red local (interno)', 'country_code': '', 'city': '',
            'total': 0, 'max_cvss': 0.0, 'attacks': [], 'internal': True,
        }

        def _push(bucket, f, ip, atype):
            bucket['total'] += 1
            if f['cvss_score'] and f['cvss_score'] > bucket['max_cvss']:
                bucket['max_cvss'] = round(float(f['cvss_score']), 1)
            if len(bucket['attacks']) < 25:
                bucket['attacks'].append({
                    'id': f['id'], 'src_ip': ip, 'dst_port': f['dst_port'],
                    'attack_type': atype, 'cvss_score': f['cvss_score'],
                    'confidence': f['confidence'], 'detector_stage': f['detector_stage'],
                    'timestamp': f['timestamp'],
                })

        for f in qs:
            ip = str(f['src_ip'])
            atype = f['attack_type'] or f['label'] or 'Desconocido'
            if ip not in geo_cache:
                geo_cache[ip] = locate(ip)
            loc = geo_cache[ip]

            if loc:  # IP pública -> país real
                total_attacks += 1
                external += 1
                by_type[atype] = by_type.get(atype, 0) + 1
                key = (round(loc['lat'], 2), round(loc['lon'], 2))
                if key not in points:
                    points[key] = {
                        'lat': loc['lat'], 'lon': loc['lon'],
                        'country': loc['country'], 'country_code': loc['country_code'],
                        'city': loc['city'], 'total': 0, 'max_cvss': 0.0,
                        'attacks': [], 'internal': False,
                    }
                _push(points[key], f, ip, atype)
                c = loc['country'] or 'Desconocido'
                by_country[c] = by_country.get(c, 0) + 1
                continue

            # Sin ubicación pública: ¿IP privada/reservada? -> red local (interno)
            try:
                ipo = ipaddress.ip_address(ip)
                is_internal = (ipo.is_private or ipo.is_reserved or ipo.is_loopback
                               or ipo.is_link_local or ipo.is_multicast or ipo.is_unspecified)
            except ValueError:
                is_internal = False
            if is_internal:
                total_attacks += 1
                internal += 1
                by_type[atype] = by_type.get(atype, 0) + 1
                _push(internal_pt, f, ip, atype)

        if internal_pt['total'] > 0:
            points[('__internal__',)] = internal_pt
            by_country['Red local (interno)'] = internal_pt['total']

        countries = sorted(
            [{'country': k, 'total': v} for k, v in by_country.items()],
            key=lambda x: -x['total'],
        )
        attack_types = sorted(
            [{'type': k, 'total': v} for k, v in by_type.items()],
            key=lambda x: -x['total'],
        )

        # Total de ataques detectados (= Dashboard). Ahora el mapa representa TODOS:
        # externos en su país e internos en el nodo de red local.
        total_detected = (
            Flow.objects.exclude(label__iregex=NON_ATTACK_RE).exclude(label__isnull=True).count()
        )

        return Response({
            'points': list(points.values()),
            'countries': countries,
            'attack_types': attack_types,
            'total_attacks': total_attacks,       # representados en el mapa (= total)
            'total_detected': total_detected,     # todos los detectados (= Dashboard)
            'external': external,                  # con país (IP pública)
            'internal': internal,                 # red local (IP privada)
            'located_points': len(points),
            'target': target,
        })


class HoneypotEventViewSet(viewsets.ModelViewSet):
    queryset = HoneypotEvent.objects.all()
    serializer_class = HoneypotEventSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['attacker_ip', 'honeypot_name', 'service', 'username_attempted', 'command_executed']
    ordering_fields = ['timestamp', 'attacker_ip', 'service']
    ordering = ['-timestamp']

    def get_queryset(self):
        queryset = super().get_queryset()
        attacker_ip = self.request.query_params.get('attacker_ip', None)
        service = self.request.query_params.get('service', None)
        honeypot_name = self.request.query_params.get('honeypot_name', None)

        if attacker_ip:
            queryset = queryset.filter(attacker_ip=attacker_ip)
        if service:
            queryset = queryset.filter(service__iexact=service)
        if honeypot_name:
            queryset = queryset.filter(honeypot_name__iexact=honeypot_name)

        return queryset

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Devuelve estadísticas de ataques recibidos por la Honeypot."""
        top_attackers = HoneypotEvent.objects.values('attacker_ip').annotate(total=Count('id')).order_by('-total')[:10]
        services = HoneypotEvent.objects.values('service').annotate(total=Count('id')).order_by('-total')
        total_events = HoneypotEvent.objects.count()
        return Response({
            'total_events': total_events,
            'top_attackers': top_attackers,
            'services_targeted': services
        })

    @action(detail=False, methods=['get'])
    def geo(self, request):
        """Ataques del honeypot geolocalizados (para el mapa/globo mundial).

        Agrega por ubicación (lat/lon) e incluye el país. El `target` es la
        ubicación del honeypot, destino de los arcos."""
        import os
        from .geo import locate

        rows = HoneypotEvent.objects.values('attacker_ip').annotate(total=Count('id'))
        points = {}
        for row in rows:
            ip = str(row['attacker_ip'])
            loc = locate(ip)
            if not loc:
                continue
            key = (round(loc['lat'], 2), round(loc['lon'], 2))
            if key not in points:
                points[key] = {
                    'lat': loc['lat'], 'lon': loc['lon'],
                    'country': loc['country'], 'country_code': loc['country_code'],
                    'city': loc['city'], 'total': 0, 'ips': [],
                }
            points[key]['total'] += row['total']
            if len(points[key]['ips']) < 20:
                points[key]['ips'].append(ip)

        by_country = {}
        for p in points.values():
            c = p['country'] or 'Desconocido'
            by_country[c] = by_country.get(c, 0) + p['total']
        countries = sorted(
            [{'country': k, 'total': v} for k, v in by_country.items()],
            key=lambda x: -x['total'],
        )

        target = {
            'lat': float(os.environ.get('HONEYPOT_LAT', '-0.1807')),
            'lon': float(os.environ.get('HONEYPOT_LON', '-78.4678')),
            'label': os.environ.get('HONEYPOT_LABEL', 'Honeypot (Ecuador)'),
        }
        return Response({
            'points': list(points.values()),
            'countries': countries,
            'target': target,
        })


class WebVisitViewSet(viewsets.ModelViewSet):
    queryset = WebVisit.objects.all()
    serializer_class = WebVisitSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['domain', 'src_ip', 'url_path']
    ordering_fields = ['timestamp', 'domain', 'src_ip']
    ordering = ['-timestamp']

    def get_queryset(self):
        qs = super().get_queryset()
        src_ip = self.request.query_params.get('src_ip')
        domain = self.request.query_params.get('domain')
        source = self.request.query_params.get('source')
        if src_ip:
            qs = qs.filter(src_ip=src_ip)
        if domain:
            qs = qs.filter(domain__icontains=domain)
        if source:
            qs = qs.filter(source=source)
        return qs

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Resumen de navegación: totales, dominios y clientes únicos."""
        total = WebVisit.objects.count()
        unique_domains = WebVisit.objects.values('domain').distinct().count()
        unique_clients = WebVisit.objects.values('src_ip').distinct().count()
        return Response({
            'total_visits': total,
            'unique_domains': unique_domains,
            'unique_clients': unique_clients,
        })

    @action(detail=False, methods=['get'])
    def top(self, request):
        """Top de sitios más visitados y clientes más activos."""
        limit = int(request.query_params.get('limit', 15))
        top_domains = (WebVisit.objects.values('domain')
                       .annotate(total=Count('id')).order_by('-total')[:limit])
        top_clients = (WebVisit.objects.values('src_ip')
                       .annotate(total=Count('id')).order_by('-total')[:limit])
        by_source = (WebVisit.objects.values('source')
                     .annotate(total=Count('id')).order_by('-total'))
        return Response({
            'top_domains': top_domains,
            'top_clients': top_clients,
            'by_source': by_source,
        })
