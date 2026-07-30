import os
from pathlib import Path

import dj_database_url
from django.core.exceptions import ImproperlyConfigured


BASE_DIR = Path(__file__).resolve().parent.parent


def env_bool(name, default=False):
    return os.getenv(name, str(default)).lower() in {"1", "true", "yes", "on"}


configured_secret = os.getenv("DJANGO_SECRET_KEY") or os.getenv("SECRET_KEY")
DEBUG = env_bool("DJANGO_DEBUG")
if not configured_secret and not DEBUG:
    raise ImproperlyConfigured("DJANGO_SECRET_KEY is required when DEBUG is false.")
SECRET_KEY = configured_secret or "development-only-rwsth-4Jt8vR2mQ7xN5kP9sW3cL6hF1yD0aB"
ALLOWED_HOSTS = [value.strip() for value in os.getenv(
    "ALLOWED_HOSTS", "localhost,127.0.0.1,testserver"
).split(",") if value.strip()]
CSRF_TRUSTED_ORIGINS = [value.strip() for value in os.getenv(
    "CSRF_TRUSTED_ORIGINS", ""
).split(",") if value.strip()]

INSTALLED_APPS = [
    "axes",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "core",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "core.middleware.TailscaleAuthMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "core.middleware.SecurityHeadersMiddleware",
    "axes.middleware.AxesMiddleware",
]

AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesStandaloneBackend",
    "django.contrib.auth.backends.ModelBackend",
]
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = 1
AXES_HTTP_RESPONSE_CODE = 429
AXES_LOCKOUT_PARAMETERS = [["username", "ip_address"]]
AXES_RESET_ON_SUCCESS = True

ROOT_URLCONF = "config.urls"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "core.context.current_membership",
                "core.context.navigation",
                "core.context.application_metadata",
                "core.context.operator_metadata",
                "core.context.demo_session",
            ],
        },
    }
]

WSGI_APPLICATION = "config.wsgi.application"
if os.getenv("DATABASE_URL"):
    DATABASES = {
        "default": dj_database_url.config(conn_max_age=60, conn_health_checks=True)
    }
elif os.getenv("DB_HOST"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "HOST": os.environ["DB_HOST"],
            "PORT": os.getenv("DB_PORT", "5432"),
            "NAME": os.environ["DB_NAME"],
            "USER": os.environ["DB_USER"],
            "PASSWORD": os.environ["DB_PASSWORD"],
            "CONN_MAX_AGE": 60,
            "CONN_HEALTH_CHECKS": True,
        }
    }
else:
    DATABASES = {
        "default": dj_database_url.parse(f"sqlite:///{BASE_DIR / 'db.sqlite3'}")
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "de-de"
TIME_ZONE = "Europe/Berlin"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "staticfiles": {
        # Die Manifest-Variante verlangt ein vorher gelaufenes collectstatic.
        # Im Betrieb ist das richtig, in Entwicklung und Tests waere es nur
        # eine Huerde - dort genuegt die einfache Auslieferung.
        "BACKEND": (
            "django.contrib.staticfiles.storage.StaticFilesStorage" if DEBUG
            else "whitenoise.storage.CompressedManifestStaticFilesStorage"
        ),
    }
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "access"
LOGIN_REDIRECT_URL = "access"
LOGOUT_REDIRECT_URL = "access"
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_HTTPONLY = True
SECURE_COOKIES = env_bool("SECURE_COOKIES", default=not DEBUG)
SESSION_COOKIE_SECURE = SECURE_COOKIES
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SECURE = SECURE_COOKIES
CSRF_COOKIE_SAMESITE = "Lax"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
SECURE_HSTS_SECONDS = 31_536_000
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
X_FRAME_OPTIONS = "DENY"

# TLS ends at Tailscale Serve; redirecting the loopback health probe would break it.
SECURE_SSL_REDIRECT = False
# The shared tailnet hostname must not impose preload/subdomain policy on other apps.
SILENCED_SYSTEM_CHECKS = ["security.W005", "security.W008", "security.W021"]

# Der Cache liegt in der Datenbank, damit Zaehler wie die Reset-Drosselung ueber
# alle Gunicorn-Worker hinweg gelten und kein zusaetzlicher Dienst noetig ist.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.db.DatabaseCache",
        "LOCATION": "wachbuch_cache",
    }
}

# Passwort-Reset drosseln: je Adresse und je Absender-IP pro Stunde.
PASSWORD_RESET_MAX_PER_EMAIL = int(os.getenv("PASSWORD_RESET_MAX_PER_EMAIL", "3"))
PASSWORD_RESET_MAX_PER_IP = int(os.getenv("PASSWORD_RESET_MAX_PER_IP", "12"))
PASSWORD_RESET_WINDOW_SECONDS = 3600

# Ohne EMAIL_HOST schreibt Django Nachrichten in die Konsole statt sie zu
# versenden. Der Passwort-Reset funktioniert dann nur im Testbetrieb.
EMAIL_HOST = os.getenv("EMAIL_HOST", "").strip()
if EMAIL_HOST:
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
    EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "").strip()
    EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
    EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", default=True)
    EMAIL_USE_SSL = env_bool("EMAIL_USE_SSL")
    EMAIL_TIMEOUT = 10
else:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "wachbuch@localhost").strip()
PASSWORD_RESET_TIMEOUT = 60 * 60 * 3

TRUST_TAILSCALE_HEADERS = env_bool("TRUST_TAILSCALE_HEADERS")
TAILSCALE_ADMIN_LOGIN = os.getenv("TAILSCALE_ADMIN_LOGIN", "").strip().lower()
DEFAULT_STATION_NAME = os.getenv("DEFAULT_STATION_NAME", "Rettungswache").strip()
DEFAULT_STATION_SLUG = os.getenv("DEFAULT_STATION_SLUG", "rettungswache").strip()
APP_NAME = os.getenv("APP_NAME", "Rettungswache-Wachbuch").strip()
SOURCE_URL = os.getenv(
    "SOURCE_URL", "https://github.com/Darkspike1988/Rettungswache-Wachbuch"
).strip()
FEED_ALLOWED_HOSTS = {
    value.strip().lower()
    for value in os.getenv("FEED_ALLOWED_HOSTS", "").split(",")
    if value.strip()
}
FEED_MAX_BYTES = 2_000_000

# Opt-in, aus Datenschutzgruenden standardmaessig leer. Ein selbst gehosteter
# Nominatim-Server ist vorzuziehen; oeffentliche Instanzen erhalten die
# eingegebene Wachenadresse als Suchtext.
GEOCODING_HOST = os.getenv("GEOCODING_HOST", "").strip().lower()

# Demobetrieb: erlaubt jedem Besucher eine Sitzung als Demokonto. Nur fuer
# oeffentliche Schaufenster-Instanzen gedacht, niemals fuer echte Wachendaten.
DEMO_MODE = env_bool("DEMO_MODE")
DEMO_STATION_SLUG = os.getenv("DEMO_STATION_SLUG", "demo-wache").strip()
DEMO_USERNAME = os.getenv("DEMO_USERNAME", "demo@wachbuch.invalid").strip()

# Angaben der verantwortlichen Stelle (Traeger/Kreis) fuer Impressum,
# Datenschutz- und Barrierefreiheitserklaerung. Vor einem echten Betrieb durch
# eine oeffentliche Stelle muessen diese Werte gesetzt werden; ohne Angabe
# zeigen die Seiten deutliche Platzhalter statt erfundener Angaben.
OPERATOR_NAME = os.getenv("OPERATOR_NAME", "").strip()
OPERATOR_ADDRESS = os.getenv("OPERATOR_ADDRESS", "").strip()
OPERATOR_REPRESENTATIVE = os.getenv("OPERATOR_REPRESENTATIVE", "").strip()
OPERATOR_CONTACT = os.getenv("OPERATOR_CONTACT", "").strip()
DPO_CONTACT = os.getenv("DPO_CONTACT", "").strip()
ACCESSIBILITY_CONTACT = os.getenv("ACCESSIBILITY_CONTACT", "").strip()
