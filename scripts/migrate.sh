#!/bin/sh
set -eu

python manage.py migrate --noinput
python manage.py bootstrap_project
python manage.py grant_database_access
