from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"

    def ready(self):
        # Keep the already large core/models.py stable while registering the
        # Wachalltag domain as normal models of the same Django app.
        from . import wachalltag_models  # noqa: F401
