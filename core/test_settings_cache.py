"""Regression guard for PR #109 release blocker B1 (cache configuration).

The PR added a second, unconditional ``CACHES`` block that overrode the
REDIS_URL-aware block. Effect: the JSON serializer was silently dropped
(django-redis then falls back to pickle) and Redis was forced even when
no Redis is configured. These tests import the settings module in a clean
subprocess with env-only dummy values, so they assert real import-time
behaviour instead of a re-import of an already-loaded module.
"""

import os
import subprocess
import sys
from pathlib import Path

from django.test import SimpleTestCase

_PROJECT_ROOT = Path(__file__).resolve().parent.parent

_PROBE = (
    "import os, django\n"
    "os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')\n"
    "django.setup()\n"
    "from django.conf import settings\n"
    "cache = settings.CACHES['default']\n"
    "options = cache.get('OPTIONS', {}) or {}\n"
    "print('BACKEND=' + cache['BACKEND'])\n"
    "print('LOCATION=' + str(cache.get('LOCATION', '')))\n"
    "print('SERIALIZER=' + str(options.get('SERIALIZER', '')))\n"
    "print('SESSION_ENGINE=' + str(getattr(settings, 'SESSION_ENGINE', '')))\n"
)


def _effective(env):
    """Return effective cache/session settings for a clean env-only import."""
    clean = {
        "PATH": os.environ.get("PATH", ""),
        "DJANGO_SECRET_KEY": "test-only-dummy-secret",  # env-only dummy, no real secret
        "DJANGO_DEBUG": "false",
    }
    clean.update(env)
    completed = subprocess.run(
        [sys.executable, "-c", _PROBE],
        cwd=str(_PROJECT_ROOT),
        env=clean,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise AssertionError(
            "settings probe failed: %s%s" % (completed.stdout, completed.stderr)
        )
    result = {}
    for line in completed.stdout.splitlines():
        if "=" in line:
            key, _, value = line.partition("=")
            result[key] = value
    return result


class CacheConfigRegressionTests(SimpleTestCase):
    # Bogus loopback URL: only inspected as configuration, never contacted.
    REDIS_URL = "redis://127.0.0.1:6379/0"

    def test_redis_url_selects_json_serializer(self):
        eff = _effective({"REDIS_URL": self.REDIS_URL})
        self.assertEqual(eff["BACKEND"], "django_redis.cache.RedisCache")
        self.assertEqual(eff["LOCATION"], self.REDIS_URL)
        self.assertEqual(
            eff["SERIALIZER"], "django_redis.serializers.json.JSONSerializer"
        )
        self.assertEqual(
            eff["SESSION_ENGINE"], "django.contrib.sessions.backends.cached_db"
        )

    def test_without_redis_uses_locmem_and_db_sessions(self):
        eff = _effective({})
        self.assertEqual(
            eff["BACKEND"], "django.core.cache.backends.locmem.LocMemCache"
        )
        self.assertEqual(eff["SESSION_ENGINE"], "django.contrib.sessions.backends.db")

    def test_redis_url_wins_over_discrete_host(self):
        eff = _effective({"REDIS_URL": self.REDIS_URL, "REDIS_HOST": "some-other-host"})
        self.assertEqual(eff["LOCATION"], self.REDIS_URL)
