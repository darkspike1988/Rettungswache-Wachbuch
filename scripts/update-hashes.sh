#!/bin/sh
set -eu
pip install pip-tools
pip-compile --generate-hashes --output-file=requirements.lock requirements.txt
pip-compile --generate-hashes --output-file=requirements-ci.lock requirements-ci.in
pip-compile --generate-hashes --output-file=requirements-audit.lock requirements-audit.in
echo "requirements.lock, requirements-ci.lock und requirements-audit.lock aktualisiert. Committe alle Lock-Dateien und nutze in CI ausschliesslich --require-hashes."
