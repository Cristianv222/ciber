"""Gestión del entrenamiento de modelos lanzando el contenedor `trainer`
mediante el socket de Docker (montado en el backend)."""

import os
import logging

log = logging.getLogger('flows.training')

JOB_NAME = 'ciber_trainer_job'


def _client():
    import docker
    return docker.from_env()


def _volumes():
    vols = {
        os.environ.get('MODELS_VOLUME', 'ciber_models'): {'bind': '/models', 'mode': 'rw'},
    }
    root = os.environ.get('HOST_PROJECT_DIR')
    if root:
        vols[os.path.join(root, 'data', 'datasets')] = {'bind': '/data/datasets', 'mode': 'ro'}
    return vols


def start():
    """Lanza (o relanza) el contenedor de entrenamiento en segundo plano."""
    client = _client()
    try:
        old = client.containers.get(JOB_NAME)
        old.remove(force=True)
    except Exception:  # noqa: BLE001
        pass

    client.containers.run(
        os.environ.get('TRAINER_IMAGE', 'ciber-trainer'),
        detach=True,
        name=JOB_NAME,
        environment={
            'DATASET_PATH': '/data/datasets',
            'OUT_DIR': '/models',
            'EPOCHS': os.environ.get('TRAIN_EPOCHS', '15'),
            'BATCH_SIZE': os.environ.get('TRAIN_BATCH_SIZE', '256'),
            'AE_PERCENTILE': os.environ.get('TRAIN_AE_PERCENTILE', '99'),
        },
        volumes=_volumes(),
        network=os.environ.get('DOCKER_NETWORK', 'ciber_default'),
    )


def status():
    """Estado del último job de entrenamiento."""
    client = _client()
    try:
        cont = client.containers.get(JOB_NAME)
    except Exception:  # noqa: BLE001
        return {'state': 'idle'}

    cont.reload()
    raw = cont.status  # created, running, exited, dead
    state = 'running' if raw == 'running' else ('exited' if raw in ('exited', 'dead') else raw)
    try:
        logs = cont.logs(tail=80).decode('utf-8', 'ignore')
    except Exception:  # noqa: BLE001
        logs = ''
    return {
        'state': state,
        'exit_code': cont.attrs.get('State', {}).get('ExitCode'),
        'logs': logs,
    }
