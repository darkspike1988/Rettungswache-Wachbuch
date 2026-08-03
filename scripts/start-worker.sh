#!/bin/sh
set -eu

# Feed-Worker: aktualisiert RSS/CSV-Lagequellen und die Müllkalender (ICS)
# pro aktivierter Station. Beide Läufe erfolgen im selben Container, in jedem
# Zyklus nacheinander. Fehler einer einzelnen Quelle werden im Command
# abgefangen und protokolliert und brechen den Zyklus nicht.

while :; do
  python manage.py sync_feeds || true
  python manage.py sync_waste_calendar || true
  sleep 900
done
