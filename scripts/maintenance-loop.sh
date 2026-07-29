#!/bin/sh
set -eu

# Fuehrt die eingestellten Loeschfristen regelmaessig aus. Laeuft bewusst mit
# der Datenbank-Owner-Rolle, weil das Anwendungskonto Audit-Ereignisse und
# Uebergaberevisionen nicht loeschen darf.

INTERVAL="${MAINTENANCE_INTERVAL_SECONDS:-86400}"

while true; do
    echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] purge_expired startet"
    if ! python manage.py purge_expired; then
        echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] purge_expired fehlgeschlagen" >&2
    fi
    if [ "${DEMO_MODE:-false}" = "true" ]; then
        echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Demodaten werden zurueckgesetzt"
        if ! python manage.py seed_demo --reset; then
            echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] seed_demo fehlgeschlagen" >&2
        fi
    fi
    sleep "$INTERVAL"
done
