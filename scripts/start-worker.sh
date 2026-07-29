#!/bin/sh
set -eu

exec python manage.py sync_feeds --watch --interval 900
