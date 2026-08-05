#!/bin/sh
set -eu

umask 077
script_dir="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
repo_root="$(CDPATH= cd -- "$script_dir/.." && pwd)"
env_file="$repo_root/.env"
example_file="$repo_root/.env.example"

if [ -e "$env_file" ]; then
    echo "Abbruch: $env_file existiert bereits. Die geführte Installation überschreibt keine Konfiguration." >&2
    exit 1
fi
for required_command in openssl awk docker; do
    command -v "$required_command" >/dev/null 2>&1 || {
        echo "Fehlendes Programm: $required_command" >&2
        exit 1
    }
done
docker compose version >/dev/null 2>&1 || {
    echo "Docker Compose v2 ist erforderlich." >&2
    exit 1
}

temp_env="$(mktemp "${TMPDIR:-/tmp}/wachbuch-env.XXXXXX")"
trap 'rm -f "$temp_env"' EXIT HUP INT TERM

django_secret="$(openssl rand -hex 48)"
owner_password="$(openssl rand -hex 32)"
app_password="$(openssl rand -hex 32)"
feed_password="$(openssl rand -hex 32)"
backup_password="$(openssl rand -hex 32)"
push_password="$(openssl rand -hex 32)"
feed_secret="$(openssl rand -hex 48)"
push_secret="$(openssl rand -hex 48)"
setup_token="$(openssl rand -hex 32)"
crypto_key="$(openssl rand -hex 32)"

awk \
    -v django_secret="$django_secret" \
    -v owner_password="$owner_password" \
    -v app_password="$app_password" \
    -v feed_password="$feed_password" \
    -v backup_password="$backup_password" \
    -v push_password="$push_password" \
    -v feed_secret="$feed_secret" \
    -v push_secret="$push_secret" \
    -v setup_token="$setup_token" \
    -v crypto_key="$crypto_key" '
    /^DJANGO_SECRET_KEY=/ { print "DJANGO_SECRET_KEY=" django_secret; next }
    /^POSTGRES_PASSWORD=/ { print "POSTGRES_PASSWORD=" owner_password; next }
    /^APP_DB_PASSWORD=/ { print "APP_DB_PASSWORD=" app_password; next }
    /^FEED_DB_PASSWORD=/ { print "FEED_DB_PASSWORD=" feed_password; next }
    /^BACKUP_DB_PASSWORD=/ { print "BACKUP_DB_PASSWORD=" backup_password; next }
    /^PUSH_DB_PASSWORD=/ { print "PUSH_DB_PASSWORD=" push_password; next }
    /^FEED_WORKER_SECRET_KEY=/ { print "FEED_WORKER_SECRET_KEY=" feed_secret; next }
    /^PUSH_WORKER_SECRET_KEY=/ { print "PUSH_WORKER_SECRET_KEY=" push_secret; next }
    /^SETUP_TOKEN=/ { print "SETUP_TOKEN=" setup_token; next }
    /^CRYPTO_MASTER_KEY=/ { print "CRYPTO_MASTER_KEY=" crypto_key; next }
    { print }
    ' "$example_file" > "$temp_env"

mv "$temp_env" "$env_file"
trap - EXIT HUP INT TERM
mkdir -p "$repo_root/backups"
cd "$repo_root"
docker compose config --quiet
docker compose build
docker compose run --rm --no-deps --user 0:0 --entrypoint chown backup 70:70 /backups
docker compose up -d --wait --wait-timeout 180

http_port="$(awk -F= '$1 == "HTTP_PORT" { print $2; exit }' "$env_file")"
http_port="${http_port:-8090}"
echo
echo "Wachbuch wurde gestartet. Öffne für die geführte Ersteinrichtung:"
echo "http://127.0.0.1:${http_port}/einrichtung/"
echo "Einrichtungs-Code: ${setup_token}"
echo
echo "Die Datei .env enthält Geheimnisse und darf nicht weitergegeben werden."
