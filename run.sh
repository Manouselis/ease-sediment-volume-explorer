#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"
exec .venv/bin/python -m uvicorn ease_volume.server:app --host 127.0.0.1 --port "${EASE_PORT:-8765}"
