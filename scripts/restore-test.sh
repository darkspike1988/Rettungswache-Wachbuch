#!/bin/sh
set -eu

latest="$(find /backups -type f -name 'rwsth-*.dump' -print | sort | tail -n 1)"
if [ -z "$latest" ]; then
    echo "Kein Wachbuch-Backup fuer den Restore-Test gefunden." >&2
    exit 1
fi

test_database="rwsth_restore_test"
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

echo "Restore-Test erfolgreich: $latest"
