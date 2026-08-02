#!/bin/sh
set -eu

python manage.py migrate --noinput
python manage.py bootstrap_project
python manage.py grant_database_access

# Optional Musterdaten für lokale Demos (DEMO_MODE=true in .env).
case "${DEMO_MODE:-false}" in
  1|true|TRUE|yes|YES|on|ON)
    python manage.py load_demo_data
    ;;
esac
