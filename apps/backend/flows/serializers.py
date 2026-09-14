from rest_framework import serializers
from .models import Flow, HoneypotEvent


class FlowSerializer(serializers.ModelSerializer):
    class Meta:
        model = Flow
        fields = '__all__'


class HoneypotEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = HoneypotEvent
        fields = '__all__'
