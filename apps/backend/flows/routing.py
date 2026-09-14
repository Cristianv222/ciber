from django.urls import re_path
from .consumers import FlowConsumer

websocket_urlpatterns = [
    re_path(r'ws/flows/$', FlowConsumer.as_asgi()),
]
