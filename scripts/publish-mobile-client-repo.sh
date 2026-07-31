#!/usr/bin/env bash
# Publiziert clients/wachbuch-mobile nach https://github.com/darkspike1988/Wachbuch-Client
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$ROOT/clients/wachbuch-mobile"
REMOTE_URL="${MOBILE_REPO_URL:-https://github.com/darkspike1988/Wachbuch-Client.git}"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/wachbuch-client-publish.XXXXXX")"
MSG="${PUBLISH_MESSAGE:-Sync: AGPL Wachbuch Client (Flutter) aligned with server}"

cleanup() { rm -rf "$WORK"; }
trap cleanup EXIT

if [[ ! -d "$SRC/lib" ]]; then
  echo "Quelle fehlt: $SRC" >&2
  exit 1
fi

echo "Prüfe Remote: $REMOTE_URL"
if ! git ls-remote "$REMOTE_URL" &>/dev/null; then
  cat <<EOF >&2
Remote nicht erreichbar: $REMOTE_URL

Repo public? Oder Cursor-App-Zugriff fehlt:
  https://github.com/settings/installations
  → Cursor → Configure → Wachbuch-Client hinzufügen
EOF
  exit 2
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
  commit -m "$MSG"

git remote add origin "$REMOTE_URL"
set +e
if [[ "$HAS_COMMITS" -eq 1 ]]; then
  echo "Remote hat Commits – force-with-lease Push auf main…"
  git push --force-with-lease -u origin main
  status=$?
  if [[ $status -ne 0 && "${ALLOW_FORCE:-0}" == "1" ]]; then
    echo "Lease fehlgeschlagen – ALLOW_FORCE=1 → force push"
    git push --force -u origin main
    status=$?
  fi
else
  git push -u origin main
  status=$?
fi
set -e

if [[ $status -ne 0 ]]; then
  cat <<EOF >&2

Push fehlgeschlagen (oft 403): Die GitHub-App darf Wachbuch-Client nicht beschreiben.

Freigabe:
  1. https://github.com/settings/installations
  2. Cursor → Configure
  3. Repository access: Wachbuch-Client hinzufügen (oder All repositories)
  4. Erneut: ./scripts/publish-mobile-client-repo.sh

Lokal mit eigenem Account:
  ALLOW_FORCE=1 ./scripts/publish-mobile-client-repo.sh
EOF
  exit $status
fi

echo "Fertig: ${REMOTE_URL%.git}"
