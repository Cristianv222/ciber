from django.contrib import admin
from .models import Flow, HoneypotEvent


@admin.register(Flow)
class FlowAdmin(admin.ModelAdmin):
    list_display = ('id', 'timestamp', 'src_ip', 'src_port', 'dst_ip', 'dst_port', 'protocol', 'label', 'attack_type', 'confidence', 'cvss_score', 'action_taken', 'processed_at')
    list_filter = ('label', 'attack_type', 'detector_stage', 'protocol', 'timestamp')
    search_fields = ('src_ip', 'dst_ip', 'label')
    ordering = ('-timestamp',)
    readonly_fields = [f.name for f in Flow._meta.fields]

    def has_add_permission(self, request):
        return True

    def has_delete_permission(self, request, obj=None):
        return True


@admin.register(HoneypotEvent)
class HoneypotEventAdmin(admin.ModelAdmin):
    list_display = ('id', 'timestamp', 'honeypot_name', 'attacker_ip', 'target_ip', 'service', 'username_attempted', 'password_attempted', 'command_executed')
    list_filter = ('honeypot_name', 'service', 'timestamp')
    search_fields = ('attacker_ip', 'username_attempted', 'password_attempted', 'command_executed')
    ordering = ('-timestamp',)
    readonly_fields = [f.name for f in HoneypotEvent._meta.fields]

    def has_add_permission(self, request):
        return True

    def has_delete_permission(self, request, obj=None):
        return True
