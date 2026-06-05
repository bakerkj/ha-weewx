#!/usr/bin/env bash
# Build the addon image (or reuse it), then run the MQTT-only e2e via
# docker-compose.mqtt.yml. Verifies the felddy HA discovery surface,
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

echo "=== mqtt e2e OK ==="
