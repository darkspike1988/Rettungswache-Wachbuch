#!/bin/sh
# Erzeugt requirements.lock mit Integritaets-Hashes aus requirements.txt.
#
# Nutzt pip-compile (pip-tools) mit --generate-hashes, sodass pip spaeter mit
# `pip install --require-hashes -r requirements.lock` die Integritaet jedes
# Pakets gegen SHA256 pruefen kann. Das schliesst Supply-Chain-Angriffe auf
# transitive Abhaengigkeiten aus, solange der Lockfile im Review geprueft wird.
#
# Vorab einmalig in einem frischen venv installieren:
#     pip install pip-tools
#
# Aufruf:
#     ./scripts/update-hashes.sh
#
# Anschliessend requirements.lock committen. CI schlaegt fehl, wenn die
# installierten Versionen nicht zu den hinterlegten Hashes passen.
set -eu

root_dir="$(cd "$(dirname "$0")/.." && pwd)"
cd "$root_dir"

if ! command -v pip-compile >/dev/null 2>&1; then
    echo "pip-compile nicht gefunden. Bitte 'pip install pip-tools' ausfuehren." >&2
    exit 1
fi

pip-compile --quiet --generate-hashes \
    --output-file requirements.lock \
    requirements.txt

echo "requirements.lock aktualisiert. Bitte aenderungen reviewen und committen."
