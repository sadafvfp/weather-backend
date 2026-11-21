from django.apps import AppConfig


class DeviceConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "backend.apps.device"

    def ready(self):
        from . import signals  # noqa: F401
