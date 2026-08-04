#!/bin/sh
set -eu
pip install pip-tools
pip-compile --generate-hashes --output-file=requirements.lock requirements.txt
echo "requirements.lock aktualisiert. Committe und nutze 'pip install --require-hashes -r requirements.lock'"
