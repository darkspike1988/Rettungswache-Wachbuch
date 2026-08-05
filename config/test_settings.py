from .settings import *

SETUP_WIZARD_ENABLED = False


STORAGES = {
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    }
}
MIDDLEWARE = [
    item for item in MIDDLEWARE
    if item != "whitenoise.middleware.WhiteNoiseMiddleware"
]
