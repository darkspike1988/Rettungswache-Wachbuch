#!/usr/bin/env bash
# Publiziert clients/wachbuch-mobile in das separate GitHub-Repo Wachbuch-Mobile.
# Voraussetzung: Leeres Repo existiert bereits unter
#   https://github.com/darkspike1988/Wachbuch-Mobile
# (Cloud-Agent darf Repos nicht anlegen – einmalig manuell auf GitHub erstellen.)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$ROOT/clients/wachbuch-mobile"
REMOTE_URL="${MOBILE_REPO_URL:-https://github.com/darkspike1988/Wachbuch-Mobile.git}"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/wachbuch-mobile-publish.XXXXXX")"

cleanup() { rm -rf "$WORK"; }
trap cleanup EXIT

if [[ ! -d "$SRC/lib" ]]; then
  echo "Quelle fehlt: $SRC" >&2
  exit 1
fi

echo "Prüfe Remote: $REMOTE_URL"
if ! git ls-remote "$REMOTE_URL" HEAD &>/dev/null; then
  cat <<EOF >&2
Remote ist nicht erreichbar bzw. Repo existiert noch nicht.

Bitte einmalig auf GitHub anlegen:
  https://github.com/new?name=Wachbuch-Mobile&owner=darkspike1988&visibility=public

  Name: Wachbuch-Mobile
  Owner: darkspike1988
  Visibility: Public
  Ohne README/License (LICENSE liegt im Client) – oder mit AGPL-3.0

Danach erneut:
  ./scripts/publish-mobile-client-repo.sh
EOF
  exit 2
fi

cp -a "$SRC/." "$WORK/"
rm -rf "$WORK/.dart_tool" "$WORK/build" "$WORK/dist" \
  "$WORK/.flutter-plugins" "$WORK/.flutter-plugins-dependencies"

cd "$WORK"
git init -b main
git add -A
git -c user.name="Wachbuch Publisher" -c user.email="noreply@users.noreply.github.com" \
  commit -m "Initial import: AGPL Wachbuch mobile client (Flutter)"
git remote add origin "$REMOTE_URL"
git push -u origin main

echo "Fertig: $REMOTE_URL"
