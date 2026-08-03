#!/bin/sh
# Long-running push outbox worker. The loop writes a tiny liveness file into
# /tmp so the docker healthcheck can verify it is making progress.
set -eu

INTERVAL=${PUSH_WORKER_INTERVAL:-15}
BATCH=${PUSH_WORKER_BATCH:-25}

cleanup() {
    rm -f /tmp/push_worker.alive
}
trap cleanup EXIT INT TERM

while true; do
    date -u +%Y-%m-%dT%H:%M:%SZ > /tmp/push_worker.alive
    python manage.py push_worker --watch --interval "$INTERVAL" --batch-size "$BATCH" || {
        rm -f /tmp/push_worker.alive
        sleep 5
    }
done
