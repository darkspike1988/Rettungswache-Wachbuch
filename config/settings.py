import os
from pathlib import Path

import dj_database_url
from django.core.exceptions import ImproperlyConfigured


BASE_DIR = Path(__file__).resolve().parent.parent

from core.version import APP_VERSION as DEFAULT_APP_VERSION  # noqa: E402


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
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "core.middleware.CorrelationIdMiddleware",
    "core.middleware.SecurityHeadersMiddleware",
    "core.middleware.ClientIPMiddleware",
    "axes.middleware.AxesMiddleware",
]

# Strukturierte Logs: Korrelations-ID ohne personenbezogene Nutzdaten.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django.request": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "wachbuch.errors": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "wachbuch.requests": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

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
                "core.context.application_metadata",
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

# BSI TR-02102 / moderne Verwaltungspraxis: Argon2id bevorzugt, PBKDF2 als Fallback.
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
    "django.contrib.auth.hashers.ScryptPasswordHasher",
]

LANGUAGE_CODE = "de-de"
TIME_ZONE = "Europe/Berlin"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    }
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "landing"
LOGOUT_REDIRECT_URL = "landing"
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

# TLS terminates at an external reverse proxy. Inside the container the health
# probe and Gunicorn speak plain HTTP on loopback, so Django must not redirect.
SECURE_SSL_REDIRECT = False
SILENCED_SYSTEM_CHECKS = ["security.W005", "security.W008", "security.W021"]

DEFAULT_STATION_NAME = os.getenv("DEFAULT_STATION_NAME", "Rettungswache").strip()
DEFAULT_STATION_SLUG = os.getenv("DEFAULT_STATION_SLUG", "rettungswache").strip()
APP_NAME = os.getenv("APP_NAME", "Wachbuch").strip() or "Wachbuch"
SOURCE_URL = os.getenv(
    "SOURCE_URL", "https://github.com/Darkspike1988/Rettungswache-Wachbuch"
).strip()
APP_VERSION = os.getenv("APP_VERSION", DEFAULT_APP_VERSION).strip()
FEED_ALLOWED_HOSTS = {
    value.strip().lower()
    for value in os.getenv("FEED_ALLOWED_HOSTS", "").split(",")
    if value.strip()
}
FEED_MAX_BYTES = 2_000_000
WASTE_CALENDAR_MAX_BYTES = 1_048_576
RETENTION_FEED_DAYS = int(os.getenv("RETENTION_FEED_DAYS", "90") or "0")
RETENTION_AUDIT_DAYS = int(os.getenv("RETENTION_AUDIT_DAYS", "0") or "0")
MFA_ENABLED = env_bool("MFA_ENABLED", default=True)
MFA_REQUIRED = env_bool("MFA_REQUIRED", default=False)
DEMO_MODE = env_bool("DEMO_MODE", default=False)
DEMO_PASSWORD = os.getenv("DEMO_PASSWORD", "Demo-Passwort-12345").strip() or "Demo-Passwort-12345"
if DEMO_MODE:
    # Presentations should not require MFA setup on every demo account.
    MFA_REQUIRED = False
REGISTRATION_ENABLED = env_bool("REGISTRATION_ENABLED", default=False)
REGISTRATION_RATE_LIMIT = int(os.getenv("REGISTRATION_RATE_LIMIT", "5") or "5")
TRUSTED_PROXY = env_bool("TRUSTED_PROXY", default=False)
RATELIMIT_KEY_SALT = os.getenv("RATELIMIT_KEY_SALT", "wachbuch")
WEBAUTHN_ENABLED = env_bool("WEBAUTHN_ENABLED", default=True)
WEBAUTHN_RP_ID = os.getenv("WEBAUTHN_RP_ID", "").strip()
WEBAUTHN_ORIGIN = os.getenv("WEBAUTHN_ORIGIN", "").strip()
WEB_PUSH_ENABLED = env_bool("WEB_PUSH_ENABLED", default=False)
VAPID_PUBLIC_KEY = os.getenv("VAPID_PUBLIC_KEY", "").strip()
VAPID_PRIVATE_KEY = os.getenv("VAPID_PRIVATE_KEY", "").strip()
VAPID_ADMIN_EMAIL = os.getenv("VAPID_ADMIN_EMAIL", "ops@localhost").strip() or "ops@localhost"

# Essential auth cookies only. No analytics or advertising cookies are set.
SESSION_COOKIE_NAME = "rwsth_session"
CSRF_COOKIE_NAME = "rwsth_csrf"
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_AGE = 60 * 60 * 12
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_SAVE_EVERY_REQUEST = False

# Redis Cache Configuration
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379") or "6379")
REDIS_DB = int(os.getenv("REDIS_DB", "0") or "0")
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "").strip() or None

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "CONNECTION_POOL_KWARGS": {"max_connections": 100},
            "PICKLE_VERSION": -1,  # Use the latest protocol
        },
        "KEY_PREFIX": "wachbuch",
        "TIMEOUT": 300,  # Default cache timeout: 5 minutes
    }
}

# Cache timeouts for specific views (in seconds)
HANDOVER_CACHE_TIMEOUT = 60  # 1 minute for handover lists
DASHBOARD_CACHE_TIMEOUT = 30  # 30 seconds for dashboard
CALENDAR_CACHE_TIMEOUT = 120  # 2 minutes for calendar
COFFEE_CACHE_TIMEOUT = 60  # 1 minute for coffee ledger

# Use cached template loader for production
if not DEBUG:
    TEMPLATES[0]["OPTIONS"]["loaders"] = [
        ("django.template.loaders.cached.Loader", [
            "django.template.backends.django.DjangoTemplates",
        ]),
    ]
