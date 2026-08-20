from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"

    def ready(self):
        # Keep the already large core/models.py stable while registering
        # additional domains as normal models of the same Django app.
        from . import privacy_models  # noqa: F401
        from . import wachalltag_models  # noqa: F401
        from . import image_privacy  # noqa: F401
        from . import checks  # noqa: F401
        from .feed_sync import validate_feed_allowed_hosts
        validate_feed_allowed_hosts()
