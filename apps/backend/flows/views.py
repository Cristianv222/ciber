from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Count
from .models import Flow, HoneypotEvent
from .serializers import FlowSerializer, HoneypotEventSerializer


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
