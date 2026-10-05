from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import FlowViewSet, HoneypotEventViewSet
from . import auth_views, control_views

router = DefaultRouter()
router.register(r'flows', FlowViewSet, basename='flow')
router.register(r'honeypot-events', HoneypotEventViewSet, basename='honeypot-event')

urlpatterns = [
    path('', include(router.urls)),
    path('auth/login/', auth_views.login, name='auth-login'),
    path('auth/me/', auth_views.me, name='auth-me'),
    path('models/info/', control_views.models_info, name='models-info'),
    path('system/status/', control_views.system_status, name='system-status'),
    path('train/', control_views.train_start, name='train-start'),
    path('train/status/', control_views.train_status, name='train-status'),
]
