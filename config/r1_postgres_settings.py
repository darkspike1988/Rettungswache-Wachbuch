"""PostgreSQL-Testsettings fuer den R1-Konkurrenznachweis (isoliert, Loopback).

Bewusst getrennt von ``config.test_settings`` (SQLite). Row-Locks, echte
Transaktionstrennung und Sperrwarteverhalten sind nur auf einer echten
PostgreSQL-Instanz nachweisbar; SQLite bleibt schneller Vertragstest.

Alle Verbindungsdaten stammen aus der Umgebung. Der Runner
``scripts/r1-postgres-runner.sh`` legt eine eigene, wegwerfbare PostgreSQL-Instanz
ausschliesslich auf 127.0.0.1 mit zufaelligem Port an und setzt diese Variablen.
Es wird keine bestehende Datenbank verwendet.
"""

import os

from .test_settings import *  # noqa: F403

if os.environ.get("R1_DISPOSABLE_DB") != "1":
    raise RuntimeError(
        "R1 settings require explicit disposable-database acknowledgement."
    )
if os.environ.get("R1_PG_HOST", "127.0.0.1") != "127.0.0.1":
    raise RuntimeError("R1 settings accept loopback only; never a production DB host.")

TEST_RUNNER = "config.r1_test_runner.PostgresEvidenceRunner"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ["R1_PG_DB"],
        "USER": os.environ["R1_PG_USER"],
        "PASSWORD": os.environ["R1_PG_PASSWORD"],
        "HOST": os.environ.get("R1_PG_HOST", "127.0.0.1"),
        "PORT": os.environ["R1_PG_PORT"],
        # Kein Connection-Reuse: jede Testverbindung bleibt eigenstaendig.
        "CONN_MAX_AGE": 0,
        "OPTIONS": {
            "connect_timeout": 5,
            "options": "-c statement_timeout=10000 -c lock_timeout=8000",
        },
        # Django legt diese Test-DB selbst an und zerstoert sie danach.
        "TEST": {"NAME": os.environ.get("R1_PG_TEST_DB", "r1wb_test")},
    }
}
