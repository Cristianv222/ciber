from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import FlowViewSet, HoneypotEventViewSet

router = DefaultRouter()
router.register(r'flows', FlowViewSet, basename='flow')
router.register(r'honeypot-events', HoneypotEventViewSet, basename='honeypot-event')

urlpatterns = [
    path('', include(router.urls)),
]
