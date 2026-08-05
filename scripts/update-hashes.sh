#!/bin/sh
set -eu
if command -v uv >/dev/null 2>&1; then
    uv pip compile requirements.txt --generate-hashes --output-file requirements.lock
else
    python -m pip install "pip<26" "pip-tools==7.6.0"
    pip-compile --generate-hashes --output-file=requirements.lock requirements.txt
fi
echo "requirements.lock aktualisiert. Installation: pip install --require-hashes -r requirements.lock"
