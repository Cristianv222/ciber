"""Endpoints de control y estado del sistema para el frontend:
información de modelos, estado de contenedores y entrenamiento."""

import json
import os

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from . import training

MODELS_DIR = os.environ.get('MODELS_DIR', '/models')

# Contenedores que componen el sistema (para el panel de estado)
SERVICE_CONTAINERS = [
    ('ciber_postgres', 'PostgreSQL'),
    ('ciber_redis', 'Redis'),
    ('ciber_backend', 'Backend / API'),
    ('ciber_xmpp', 'XMPP (Prosody)'),
    ('ciber_grafana', 'Grafana'),
    ('ciber_detector', 'Agente Detector'),
    ('ciber_decision', 'Agente Decisión'),
    ('ciber_response', 'Agente Respuesta'),
    ('ciber_cicflowmeter', 'Ingesta CICFlowMeter'),
    ('ciber_frontend', 'Frontend'),
]


@api_view(['GET'])
@permission_classes([AllowAny])
def models_info(request):
    """Metadatos de los modelos entrenados (lee /models/metadata.json)."""
    meta_path = os.path.join(MODELS_DIR, 'metadata.json')
    present = {}
    for name in ('xgboost.pkl', 'cnn_lstm.h5', 'autoencoder.h5', 'scaler.pkl', 'metadata.json'):
        present[name] = os.path.exists(os.path.join(MODELS_DIR, name))

    if not os.path.exists(meta_path):
        return Response({'trained': False, 'artifacts': present})

    try:
        with open(meta_path) as f:
            meta = json.load(f)
    except Exception as exc:  # noqa: BLE001
        return Response({'trained': False, 'artifacts': present, 'error': str(exc)})

    return Response({'trained': True, 'artifacts': present, **meta})


@api_view(['GET'])
@permission_classes([AllowAny])
def system_status(request):
    """Estado de los contenedores del sistema (vía socket de Docker)."""
    try:
        import docker
        client = docker.from_env()
    except Exception as exc:  # noqa: BLE001
        return Response({'available': False, 'error': str(exc), 'services': []})

    services = []
    for cname, label in SERVICE_CONTAINERS:
        entry = {'name': cname, 'label': label, 'state': 'absent', 'health': None}
        try:
            c = client.containers.get(cname)
            c.reload()
            entry['state'] = c.status  # running, exited, ...
            entry['health'] = (c.attrs.get('State', {}).get('Health', {}) or {}).get('Status')
        except Exception:  # noqa: BLE001
            pass
        services.append(entry)
    return Response({'available': True, 'services': services})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def train_start(request):
    try:
        training.start()
        return Response({'detail': 'Entrenamiento iniciado', 'state': 'running'}, status=202)
    except Exception as exc:  # noqa: BLE001
        return Response({'detail': f'No se pudo iniciar: {exc}'}, status=500)


@api_view(['GET'])
@permission_classes([AllowAny])
def train_status(request):
    try:
        return Response(training.status())
    except Exception as exc:  # noqa: BLE001
        return Response({'state': 'unknown', 'error': str(exc)}, status=500)
