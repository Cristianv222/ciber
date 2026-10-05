import json
from channels.generic.websocket import AsyncWebsocketConsumer


class FlowConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_group_name = 'flows_room'

        # Únase al grupo de retransmisión de flujos y honeypots
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

        # Enviar mensaje de bienvenida / estado de conexión al cliente
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'message': 'Conectado exitosamente al canal de flujos y telemetría Honeypot en tiempo real.'
        }))

    async def disconnect(self, close_code):
        # Salir del grupo al desconectarse
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        # Manejo de datos enviados desde el cliente
        data = json.loads(text_data)
        message_type = data.get('type', 'ping')

        if message_type == 'ping':
            await self.send(text_data=json.dumps({
                'type': 'pong',
                'status': 'active'
            }))

    async def flow_message(self, event):
        """Manejador ejecutado cuando se emite un nuevo flujo desde Signals."""
        flow_data = event['data']
        await self.send(text_data=json.dumps({
            'type': 'new_flow',
            'flow': flow_data
        }))

    async def flow_updated_message(self, event):
        """Manejador ejecutado cuando un agente actualiza un flujo existente
        (label, confidence, detector_stage, cvss_score, action_taken)."""
        flow_data = event['data']
        await self.send(text_data=json.dumps({
            'type': 'flow_updated',
            'flow': flow_data
        }))

    async def honeypot_event_message(self, event):
        """Manejador ejecutado cuando se registra un ataque en la Honeypot."""
        honeypot_data = event['data']
        await self.send(text_data=json.dumps({
            'type': 'new_honeypot_event',
            'event': honeypot_data
        }))
