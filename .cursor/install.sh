#!/usr/bin/env bash
# Idempotenter Setup fuer die Cloud-Agent-Entwicklungsumgebung des Wachbuch-
# Produkts: Server (Django) UND Client (Flutter, iOS/Android). Bereitet nur
# quellabhaengige Abhaengigkeiten vor; Laufzeitzustand (DB, Demo-Daten,
# Dev-Server, Web-Demo) gehoert nach .cursor/start.sh bzw. die Terminals.
set -euo pipefail

# In den Server-Repo-Root wechseln, unabhaengig vom aktuellen Arbeitsverzeichnis.
# Der Cloud-Agent-Workspace enthaelt beide Repos (Rettungswache-Wachbuch und
# Wachbuch-Client) unter einem gemeinsamen Root.
SERVER_ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$SERVER_ROOT"

echo "== Server (Django) =="
# python3-venv (inkl. ensurepip) ist im Standard-Basisimage nicht enthalten,
# wird aber fuer das virtuelle Environment benoetigt. Der Check prueft ensurepip
# direkt, weil "python3 -m venv --help" auch ohne das Paket erfolgreich ist.
# Alle Python-Pakete werden als vorkompilierte Wheels installiert.
if ! python3 -c "import ensurepip" >/dev/null 2>&1; then
  sudo apt-get update -qq
  sudo apt-get install -y --no-install-recommends python3-venv
fi
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
echo "install.sh: Server-Abhaengigkeiten installiert."

# --- Client (Flutter) ---
# Der Client liegt als Schwester-Repo neben dem Server im Workspace.
CLIENT_ROOT="$SERVER_ROOT/../Wachbuch-Client"
if [ -d "$CLIENT_ROOT" ]; then
  echo "== Client (Flutter) =="
  # Flutter/Dart benoetigen unzip und xz zum Entpacken der Toolchain.
  if ! command -v unzip >/dev/null 2>&1 || ! command -v xz >/dev/null 2>&1; then
    sudo apt-get update -qq
    sudo apt-get install -y --no-install-recommends unzip xz-utils
  fi
  # Flutter SDK (stable) einmalig nach $HOME/flutter installieren (idempotent).
  FLUTTER_DIR="$HOME/flutter"
  if [ ! -x "$FLUTTER_DIR/bin/flutter" ]; then
    git clone --depth 1 -b stable https://github.com/flutter/flutter.git "$FLUTTER_DIR"
  fi
  git config --global --add safe.directory "$FLUTTER_DIR" 2>/dev/null || true
  # flutter/dart ohne Shell-Profil-Aenderung global verfuegbar machen.
  sudo ln -sf "$FLUTTER_DIR/bin/flutter" /usr/local/bin/flutter
  sudo ln -sf "$FLUTTER_DIR/bin/dart" /usr/local/bin/dart
  export PATH="$FLUTTER_DIR/bin:$PATH"
  (
    cd "$CLIENT_ROOT"
    flutter pub get
    flutter gen-l10n
  )
  echo "install.sh: Client-Abhaengigkeiten installiert."
else
  echo "install.sh: Wachbuch-Client nicht gefunden ($CLIENT_ROOT) - Client-Setup uebersprungen."
fi
