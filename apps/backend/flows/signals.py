from django.db.models.signals import post_save
from django.dispatch import receiver
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from .models import Flow, HoneypotEvent
from .serializers import FlowSerializer, HoneypotEventSerializer


@receiver(post_save, sender=Flow)
def broadcast_new_flow(sender, instance, created, **kwargs):
    if created:
        channel_layer = get_channel_layer()
        serializer = FlowSerializer(instance)
        async_to_sync(channel_layer.group_send)(
            'flows_room',
            {
                'type': 'flow_message',
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
