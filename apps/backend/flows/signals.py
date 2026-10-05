from django.db.models.signals import post_save
from django.dispatch import receiver
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from .models import Flow, HoneypotEvent
from .serializers import FlowSerializer, HoneypotEventSerializer


@receiver(post_save, sender=Flow)
def broadcast_flow(sender, instance, created, **kwargs):
    """Retransmite un flujo tanto al crearse (ingesta) como al actualizarse
    (clasificación/decisión/respuesta de los agentes SPADE vía la API REST).

    Se usa un `type` distinto para que el frontend diferencie un flujo nuevo
    de uno ya procesado por el pipeline."""
    channel_layer = get_channel_layer()
    serializer = FlowSerializer(instance)
    message_type = 'flow_message' if created else 'flow_updated_message'
    async_to_sync(channel_layer.group_send)(
        'flows_room',
        {
            'type': message_type,
            'data': serializer.data
        }
    )


@receiver(post_save, sender=HoneypotEvent)
def broadcast_honeypot_event(sender, instance, created, **kwargs):
    if created:
        channel_layer = get_channel_layer()
        serializer = HoneypotEventSerializer(instance)
        async_to_sync(channel_layer.group_send)(
            'flows_room',
            {
                'type': 'honeypot_event_message',
                'data': serializer.data
            }
        )
