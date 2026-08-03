#!/bin/sh
set -eu

# Restore-Test laeuft grundsaetzlich mit den Credentials des Backup-Containers
# (Least-Privilege). pg_restore darf mit der Backup-Rolle laufen, weil
# pg_dump --no-owner --no-acl erzeugt wurde. Fuer createdb/dropdb benoetigt
# dieses Skript jedoch Owner- oder Superuser-Rechte und muss daher explizit mit
# RESTORE_OWNER=1 und den Owner-Credentials gestartet werden.
: "${RESTORE_OWNER:=0}"

if [ "$RESTORE_OWNER" = "1" ]; then
    : "${PGUSER:?RESTORE_OWNER=1 erfordert Owner-Credentials (PGUSER/PGPASSWORD).}"
    : "${PGPASSWORD:?RESTORE_OWNER=1 erfordert Owner-Credentials (PGUSER/PGPASSWORD).}"
else
    : "${PGUSER:?Backup-Rolle als PGUSER setzen (z. B. rwsth_backup).}"
    : "${PGPASSWORD:?Backup-Rolle als PGPASSWORD setzen.}"
fi

latest="$(find /backups -type f -name 'rwsth-*.dump' -print | sort | tail -n 1)"
if [ -z "$latest" ]; then
    echo "Kein Wachbuch-Backup fuer den Restore-Test gefunden." >&2
    exit 1
fi

test_database="rwsth_restore_test"

if [ "$RESTORE_OWNER" = "1" ]; then
    dropdb --host "$PGHOST" --username "$PGUSER" --if-exists "$test_database"
    createdb --host "$PGHOST" --username "$PGUSER" "$test_database"
    trap 'dropdb --host "$PGHOST" --username "$PGUSER" --if-exists "$test_database"' EXIT
    pg_restore \
        --host "$PGHOST" \
        --username "$PGUSER" \
        --dbname "$test_database" \
        --exit-on-error \
        "$latest"
    psql \
        --host "$PGHOST" \
        --username "$PGUSER" \
        --dbname "$test_database" \
        --tuples-only \
        --command "SELECT count(*) FROM django_migrations; SELECT count(*) FROM core_station;"
else
    pg_restore \
        --host "$PGHOST" \
        --username "$PGUSER" \
        --list "$latest" >/dev/null
    psql \
        --host "$PGHOST" \
        --username "$PGUSER" \
        --dbname "$PGDATABASE" \
        --tuples-only \
        --command "SELECT count(*) FROM django_migrations; SELECT count(*) FROM core_station;"
fi

echo "Restore-Test erfolgreich: $latest"
