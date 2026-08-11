#!/usr/bin/env bash
# Per-Boot-Initialisierung der Entwicklungs-Datenbank. Muss idempotent sein und
# terminieren (der Dev-Server laeuft im "web"-Terminal, nicht hier).
set -euo pipefail

set -a
# shellcheck disable=SC1091
source .cursor/dev.env
set +a

# shellcheck disable=SC1091
source .venv/bin/activate

python manage.py migrate --noinput
python manage.py bootstrap_project
python manage.py load_demo_data

# Hinweis: grant_database_access ist ein reiner PostgreSQL-Schritt (Rollen-
# rechte) und fuer die lokale SQLite-Dev-Datenbank nicht anwendbar.

echo "start.sh: Datenbank migriert und Demo-Daten geladen."
