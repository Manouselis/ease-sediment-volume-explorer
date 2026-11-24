#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"
geoutils_ref=fda51a598f81f8cdd5f96855ae59edb23738ac45
if [ -f .gitmodules ] && git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  git submodule update --init --recursive -- vendor/geoutils
elif [ ! -f vendor/geoutils/geoutils/__init__.py ]; then
  mkdir -p vendor
  git clone https://github.com/GlacioHack/geoutils.git vendor/geoutils
  git -C vendor/geoutils checkout "$geoutils_ref"
fi
if [ "$(git -C vendor/geoutils rev-parse HEAD)" != "$geoutils_ref" ]; then
  printf 'GeoUtils must be at the pinned revision %s.\n' "$geoutils_ref" >&2
  exit 1
fi
if command -v uv >/dev/null 2>&1; then
  uv venv --allow-existing .venv --python "$(command -v python3)"
  uv pip install --python .venv/bin/python -r requirements.txt
else
  python3 -m venv .venv
  .venv/bin/python -m pip install -r requirements.txt
fi
.venv/bin/python scripts/bundle_plotly.py
printf 'Ready. Start with ./run.sh and open http://127.0.0.1:8765\n'
