from .settings import *  # noqa: F403


STORAGES = {
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    }
}
MIDDLEWARE = [
    item for item in MIDDLEWARE  # noqa: F405
    if item != "whitenoise.middleware.WhiteNoiseMiddleware"
]
TRUST_TAILSCALE_HEADERS = False
# Die Tests pruefen bewusst das Verhalten ohne Betreiberangaben.
SILENCED_SYSTEM_CHECKS = SILENCED_SYSTEM_CHECKS + ["wachbuch.W001"]  # noqa: F405
