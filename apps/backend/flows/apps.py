from django.apps import AppConfig


class FlowsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'flows'
    verbose_name = 'Flujos de Red'

    def ready(self):
        import flows.signals
