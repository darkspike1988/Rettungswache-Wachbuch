#!/usr/bin/env bash
# Idempotenter Setup fuer die Cloud-Agent-Entwicklungsumgebung.
# Bereitet nur quellabhaengige Abhaengigkeiten vor; Laufzeitzustand (DB, Demo-
# Daten, Dev-Server) gehoert nach .cursor/start.sh bzw. das "web"-Terminal.
set -euo pipefail

# In den Repo-Root wechseln, unabhaengig vom aktuellen Arbeitsverzeichnis.
# Der Cloud-Agent-Workspace kann mehrere Repos enthalten (z. B. Rettungswache-
# Wachbuch und Wachbuch-Client), sodass Kommandos aus dem Workspace-Root laufen.
cd "$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"

# python3-venv ist im Standard-Basisimage nicht enthalten, wird aber fuer das
# virtuelle Environment benoetigt. Alle Python-Pakete werden als vorkompilierte
# Wheels installiert, daher ist keine Compiler-Toolchain erforderlich.
if ! python3 -m venv --help >/dev/null 2>&1; then
  sudo apt-get update -qq
  sudo apt-get install -y --no-install-recommends python3-venv
fi

python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/pip install -r requirements.txt

echo "install.sh: Abhaengigkeiten installiert."
