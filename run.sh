#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"
if [ "${1:-}" = "--pages" ]; then
  exec .venv/bin/python -m ease_volume.hosted
fi
exec .venv/bin/python -m uvicorn ease_volume.server:app --host 127.0.0.1 --port "${EASE_PORT:-8765}"
