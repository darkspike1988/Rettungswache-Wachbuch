#!/usr/bin/env bash
# R1: isolierte, wegwerfbare PostgreSQL-Instanz fuer den Konkurrenznachweis.
#
# Sicherheits-/Isolationsmodell:
#  * Es wird AUSSCHLIESSLICH ein neuer, eigener, wegwerfbarer Container erzeugt.
#  * Der Container teilt den Netzwerk-Namespace des aufrufenden Containers und
#    lauscht ausschliesslich auf 127.0.0.1 mit einem zufaelligen Port
#    (listen_addresses=127.0.0.1). Keine veroeffentlichten Ports, keine Bindung
#    an 0.0.0.0/Host/LAN.
#  * Bestehende Container, Datenbanken und Dienste werden nie verwendet,
#    gestoppt oder veraendert.
#  * Kein Image-Pull (Image muss lokal vorhanden sein), keine Installation und
#    kein Neustart von Diensten; der eigene Container wird nur im EXIT-Trap
#    entfernt.
#
# Aufruf:  scripts/r1-postgres-runner.sh [django_test_label]
# Default-Label: core.test_r1_postgres_concurrency
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${R1_PYTHON:-python3}"
IMAGE="${R1_PG_IMAGE:-postgres@sha256:742f40ea20b9ff2ff31db5458d127452988a2164df9e17441e191f3b72252193}"
# Bewusst NICHT "test_*.py": sonst importiert die Django-Test-Discovery der
# SQLite-Suite dieses Modul und scheitert an den fehlenden R1_PG_*-Variablen.
SETTINGS_MODULE="config.r1_postgres_settings"
TEST_LABEL="core.test_r1_postgres_concurrency"
if [ "$#" -gt 0 ] && [[ "$1" != -* ]]; then
  TEST_LABEL="$1"
  shift
fi
NETNS_CONTAINER="${R1_NETNS_CONTAINER:-$(hostname)}"
PG_USER="r1wb"
PG_DB="r1wb"
PG_TEST_DB="r1wb_concurrency_test"

_rand() { "$PYTHON" -c "import secrets,string;print(''.join(secrets.choice(string.ascii_lowercase+string.digits) for _ in range(10)))"; }
_free_port() { "$PYTHON" -c "import socket;s=socket.socket();s.bind(('127.0.0.1',0));print(s.getsockname()[1]);s.close()"; }

# Das gewaehlte Image muss lokal vorhanden sein (kein Pull, keine Netzabhaengigkeit).
if ! docker image inspect "$IMAGE" >/dev/null 2>&1; then
  echo "FEHLER: Image '$IMAGE' ist lokal nicht vorhanden. Kein Pull erlaubt." >&2
  exit 3
fi

IMAGE_ID="$(docker image inspect "$IMAGE" --format '{{.Id}}')"

NAME="r1pg-$(_rand)"
PORT="$(_free_port)"
PASSWORD="$("$PYTHON" -c "import secrets;print(secrets.token_hex(16))")"
CID=""

cleanup() {
  if [ -n "$CID" ]; then
    # Nur den eigenen, in diesem Lauf erzeugten Container entfernen.
    docker rm -f "$CID" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

echo "R1-Postgres-Runner"
echo "  image          : $IMAGE ($IMAGE_ID)"
echo "  container      : $NAME"
echo "  net namespace  : container:$NETNS_CONTAINER (geteilt, keine Portpublikation)"
echo "  bind           : 127.0.0.1:$PORT (Loopback only, zufaelliger Port)"
echo "  db/user        : $PG_DB / $PG_USER (nur diese Instanz)"

CID="$(docker run --pull=never -d --rm \
  --memory=512m --cpus=1 \
  --name "$NAME" \
  --label com.wachbuch.r1=self \
  --network "container:$NETNS_CONTAINER" \
  -e POSTGRES_USER="$PG_USER" \
  -e POSTGRES_PASSWORD="$PASSWORD" \
  -e POSTGRES_DB="$PG_DB" \
  "$IMAGE" -c listen_addresses=127.0.0.1 -c port="$PORT")"

# Bereitschaft deterministisch ueber pg_isready auf dem Loopback-Port pruefen
# (bounded, kein blindes Warten als Rennsteuerung).
READY=0
for _ in $(seq 1 90); do
  if docker exec "$CID" pg_isready -h 127.0.0.1 -p "$PORT" -U "$PG_USER" -d "$PG_DB" >/dev/null 2>&1; then
    READY=1; break
  fi
  sleep 1
done
if [ "$READY" -ne 1 ]; then
  echo "FEHLER: PostgreSQL wurde nicht bereit. Container-Log:" >&2
  docker logs "$CID" >&2 || true
  exit 4
fi

SERVERVER="$(docker exec "$CID" postgres --version 2>/dev/null || true)"
echo "  server         : $SERVERVER"

cd "$REPO_DIR"
export DJANGO_SECRET_KEY="r1-local-dummy-secret-key-000000000000"
export R1_DISPOSABLE_DB=1
export DEBUG=
export R1_PG_HOST="127.0.0.1"
export R1_PG_PORT="$PORT"
export R1_PG_DB="$PG_DB"
export R1_PG_USER="$PG_USER"
export R1_PG_PASSWORD="$PASSWORD"
export R1_PG_TEST_DB="$PG_TEST_DB"

echo "  test label     : $TEST_LABEL"
echo "  settings       : $SETTINGS_MODULE"
echo "-------------------------------------------------------------"

set +e
"$PYTHON" manage.py test "$TEST_LABEL" "$@" --settings="$SETTINGS_MODULE"
RC=$?
set -e

echo "-------------------------------------------------------------"
echo "Runner-Exit-Code: $RC (0 = Tests gruen)"
exit "$RC"
