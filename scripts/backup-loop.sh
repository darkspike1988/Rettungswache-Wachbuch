#!/bin/sh
set -eu

mkdir -p /backups

while true; do
    timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
    temporary="/backups/.rwsth-${timestamp}.dump.tmp"
    target="/backups/rwsth-${timestamp}.dump"
    pg_dump \
        --host "$PGHOST" \
        --username "$PGUSER" \
        --dbname "$PGDATABASE" \
        --format custom \
        --no-owner \
        --no-acl \
        --file "$temporary"
    mv "$temporary" "$target"
    find /backups -type f -name 'rwsth-*.dump' -mtime +6 -delete
    sleep 86400
done
