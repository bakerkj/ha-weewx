#!/usr/bin/env bash
# Build the addon image (or reuse it), then run the MQTT-only e2e via
# docker-compose.mqtt.yml. Verifies the MQTT publisher's (by felddy) HA
# discovery surface,
# state_class, availability, rain24h metadata, archive-only field
# (windrun), and that user.xaggs loaded clean at engine start. Storage
# is SQLite — MariaDB-as-backend is covered separately by
# scripts/test-mariadb.sh.
#
# Usage: scripts/test-mqtt.sh          # build + e2e (amd64)
#        BUILD=0 scripts/test-mqtt.sh  # reuse the existing ha-weewx-test image
#        ARCH=aarch64 scripts/test-mqtt.sh
set -euo pipefail
cd "$(dirname "$0")/.."

ARCH="${ARCH:-amd64}"
BUILD="${BUILD:-1}"
COMPOSE=(docker compose -p ha-weewx-mqtt -f docker-compose.mqtt.yml)

cleanup() { "${COMPOSE[@]}" down -v --remove-orphans >/dev/null 2>&1 || true; }
trap cleanup EXIT

if [[ "$BUILD" == "1" ]]; then
  docker build \
    --build-arg "BUILD_FROM=ghcr.io/home-assistant/${ARCH}-base-debian:trixie" \
    -t ha-weewx-test .
fi

mkdir -p test-results

"${COMPOSE[@]}" up --build --abort-on-container-exit --exit-code-from e2e-tests

# Log-cleanliness guard: the /dev/log "Logging error" spam is stderr
# meta-output that never reaches the e2e container, so check it here
# while logs still exist.
if "${COMPOSE[@]}" logs weewx 2>&1 | grep -qE 'Logging error|/dev/log'; then
  echo "FAIL: syslog (/dev/log) spam in weewx logs"
  exit 1
fi

echo "=== mqtt e2e OK ==="
