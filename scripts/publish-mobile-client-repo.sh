#!/usr/bin/env bash
# Publiziert clients/wachbuch-mobile in das separate GitHub-Repo wachbuch-Client.
# Voraussetzung: Repo existiert unter
#   https://github.com/darkspike1988/wachbuch-Client
# (Cloud-Agent darf Repos nicht anlegen – einmalig manuell auf GitHub erstellen.)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$ROOT/clients/wachbuch-mobile"
REMOTE_URL="${MOBILE_REPO_URL:-https://github.com/darkspike1988/wachbuch-Client.git}"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/wachbuch-client-publish.XXXXXX")"

cleanup() { rm -rf "$WORK"; }
trap cleanup EXIT

if [[ ! -d "$SRC/lib" ]]; then
  echo "Quelle fehlt: $SRC" >&2
  exit 1
fi

echo "Prüfe Remote: $REMOTE_URL"
if ! git ls-remote "$REMOTE_URL" HEAD &>/dev/null && ! git ls-remote "$REMOTE_URL" refs/heads/main &>/dev/null; then
  # Empty repos may have no HEAD yet – try listing refs
  if ! git ls-remote "$REMOTE_URL" &>/dev/null; then
    cat <<EOF >&2
Remote ist nicht erreichbar bzw. Repo existiert noch nicht / ist privat ohne Zugriff.

Bitte unter dem Account darkspike1988 anlegen (oder Link prüfen):
  https://github.com/new?name=wachbuch-Client&owner=darkspike1988&visibility=public

  Name: wachbuch-Client
  Owner: darkspike1988
  Visibility: Public (empfohlen)
  Ohne README/License (LICENSE liegt im Client) – oder mit AGPL-3.0

Danach erneut:
  ./scripts/publish-mobile-client-repo.sh

Oder mit URL:
  MOBILE_REPO_URL=https://github.com/DEIN-USER/wachbuch-Client.git ./scripts/publish-mobile-client-repo.sh
EOF
    exit 2
  fi
fi

HAS_COMMITS=0
if git ls-remote "$REMOTE_URL" HEAD 2>/dev/null | grep -q .; then
  HAS_COMMITS=1
fi

cp -a "$SRC/." "$WORK/"
rm -rf "$WORK/.dart_tool" "$WORK/build" "$WORK/dist" \
  "$WORK/.flutter-plugins" "$WORK/.flutter-plugins-dependencies"

cd "$WORK"
git init -b main
git add -A
git -c user.name="Wachbuch Publisher" -c user.email="noreply@users.noreply.github.com" \
  commit -m "Import: AGPL Wachbuch Client (Flutter iOS/Android)"

git remote add origin "$REMOTE_URL"
if [[ "$HAS_COMMITS" -eq 1 ]]; then
  echo "Remote hat bereits Commits – force-with-lease Push auf main…"
  git push --force-with-lease -u origin main
else
  git push -u origin main
fi

echo "Fertig: $REMOTE_URL"
echo "Repo: ${REMOTE_URL%.git}"
