#!/usr/bin/env bash
# Host-side felddy unit/device_class sweep.
#
# Replaces what used to be Phase 2 of build/check_image.sh — that
# version ran inside the built addon image, installed gcc + python3-dev
# via apt, downloaded uv via curl|sh, and pip-installed homeassistant
# into the image's venv, all just to import DEVICE_CLASS_UNITS once.
# The image mutation was unhygienic and the apt run added 10-20 s to
# every build-checks run on a cache miss.
#
# Instead: extract the patched weewx_ha and user/ trees from the built
# addon image with `docker cp`, drop them into a host venv that already
# has uv (set up by setup-uv in the workflow), pip-install homeassistant
# + weewx into that venv, and run build/check_felddy_units.py with the
# host venv's Python. The addon image stays unmutated and the heavy
# pip install benefits directly from the host's uv cache.
#
# Inputs:
#   IMAGE       — tag of the built addon image (default: ha-weewx-test)
#   HA_VERSION  — homeassistant pin (default: 2026.1.3)
#   WEEWX_VERSION — weewx pin (default: 5.3.1, matches pyproject.toml)
# Expects `uv` already on PATH and a working `docker` daemon.

set -euo pipefail

cd "$(dirname "$0")/.."

IMAGE="${IMAGE:-ha-weewx-test}"
HA_VERSION="${HA_VERSION:-2026.1.3}"
WEEWX_VERSION="${WEEWX_VERSION:-5.3.1}"

WORK="$(mktemp -d)"
CTR="felddy-extract-$$"
cleanup() {
  docker rm -f "$CTR" >/dev/null 2>&1 || true
  rm -rf "$WORK"
}
trap cleanup EXIT

# Extract the patched weewx_ha package and the bundled user modules from
# the built image. weewx_ha carries patches/venv/* applied; user/
# carries the bundled extensions (rain24h registers obs_group_dict at
# import time, which check_felddy_units.py relies on).
docker create --name "$CTR" "$IMAGE" >/dev/null
docker cp "$CTR:/opt/weewx/lib/python3.13/site-packages/weewx_ha" "$WORK/weewx_ha"
docker cp "$CTR:/opt/weewx-data/bin/user" "$WORK/user"

# Build a host venv with HA + stock weewx + felddy's runtime deps. The
# check doesn't touch any patched weewx core code (no weedb, no schema),
# so unpatched weewx from PyPI is fine. paho-mqtt + pydantic + setuptools
# are felddy's pyproject.toml deps — needed so the patched weewx_ha
# package overlay (next step) can import.
uv venv "$WORK/venv" --python 3.13
uv pip install --python "$WORK/venv/bin/python" \
  "homeassistant==${HA_VERSION}" \
  "weewx==${WEEWX_VERSION}" \
  paho-mqtt pydantic setuptools

# Overlay the patched weewx_ha on top of whatever weewx pulled in (if
# anything — weewx doesn't depend on weewx_ha, so this is just a copy).
SITE="$(find "$WORK/venv/lib" -maxdepth 2 -name site-packages -type d | head -1)"
[ -n "$SITE" ] || {
  echo "FAIL: could not locate site-packages in $WORK/venv/lib"
  exit 1
}
cp -r "$WORK/weewx_ha" "$SITE/weewx_ha"

# PYTHONPATH so `import user.rain24h` finds the bundled module.
PYTHONPATH="$WORK" "$WORK/venv/bin/python" build/check_felddy_units.py
