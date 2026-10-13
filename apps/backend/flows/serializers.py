from rest_framework import serializers
from .models import Flow, HoneypotEvent, WebVisit


class FlowSerializer(serializers.ModelSerializer):
    class Meta:
        model = Flow
        fields = '__all__'


class HoneypotEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = HoneypotEvent
        fields = '__all__'


class WebVisitSerializer(serializers.ModelSerializer):
    class Meta:
        model = WebVisit
        fields = '__all__'
