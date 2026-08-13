#!/bin/zsh
set -euo pipefail
cd "$(dirname "$0")"
set -a
source .env
set +a
exec .venv/bin/gunicorn config.wsgi:application \
  --bind 127.0.0.1:8090 \
  --workers 2 \
  --timeout 60 \
  --access-logfile - \
  --error-logfile -
