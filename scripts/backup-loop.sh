#!/bin/sh
set -eu

mkdir -p /backups

# 0 deaktiviert die lokale Aufbewahrung, sonst Tage (Standard 7).
BACKUP_RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-7}"
run_once=false
if [ "${1:-}" = "--once" ]; then
    run_once=true
elif [ -n "${1:-}" ]; then
    echo "Aufruf: backup-loop.sh [--once]" >&2
    exit 2
fi

encrypt_dump() {
    input="$1"
    output="$2"
    if [ -z "${BACKUP_GPG_RECIPIENT:-}" ]; then
        echo "BACKUP_ENCRYPT_REMOTE=true erfordert BACKUP_GPG_RECIPIENT." >&2
        exit 1
    fi
    gpg --batch --yes --trust-model always \
        --compress-algo none \
        --cipher-algo AES256 \
        --recipient "$BACKUP_GPG_RECIPIENT" \
        --output "$output" \
        --encrypt "$input"
}

upload_offsite() {
    dump_path="$1"
    payload="$dump_path"
    encrypted_path="${dump_path}.gpg"
    if [ "${BACKUP_ENCRYPT_REMOTE:-false}" = "true" ]; then
        encrypt_dump "$dump_path" "$encrypted_path"
        payload="$encrypted_path"
    fi
    if [ -z "${BACKUP_OFF_TARGET:-}" ]; then
        echo "Kein BACKUP_OFF_TARGET gesetzt - ueberspringe Offsite-Upload." >&2
        return 0
    fi
    case "$BACKUP_OFF_TARGET" in
        file://*)
            cp "$payload" "${BACKUP_OFF_TARGET#file://}"
            ;;
        *)
            echo "Unbekanntes BACKUP_OFF_TARGET-Schema: $BACKUP_OFF_TARGET" >&2
            exit 1
            ;;
    esac
    echo "Offsite-Upload nach $BACKUP_OFF_TARGET abgeschlossen ($payload)."
}

prune_old_dumps() {
    # 0 deaktiviert die lokale Aufbewahrung (Ringe bleiben unveraendert).
    [ "$BACKUP_RETENTION_DAYS" -gt 0 ] || return 0
    find /backups -type f \
        \( -name 'rwsth-*.dump' -o -name 'rwsth-*.dump.gpg' \) \
        -mtime +"$BACKUP_RETENTION_DAYS" -delete
}

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
    upload_offsite "$target"
    prune_old_dumps
    if [ "$run_once" = "true" ]; then
        echo "Backup abgeschlossen: $target"
        break
    fi
    sleep 86400
done
