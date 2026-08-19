#!/bin/sh
set -eu
pip install pip-tools
pip-compile --generate-hashes --output-file=requirements.lock requirements.txt
pip-compile --generate-hashes --output-file=requirements-ci.lock requirements-ci.in
echo "requirements.lock und requirements-ci.lock aktualisiert. Committe beide und nutze in CI 'pip install --require-hashes -r requirements.lock -r requirements-ci.lock'"
