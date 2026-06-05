#!/usr/bin/env bash
# Build the addon image (or reuse it), then run the MariaDB-only e2e via
# docker-compose.mariadb.yml. Verifies weewx writes archive rows to
# MariaDB and that the Seasons report is served by nginx. The /dev/log
# syslog-spam guard at the end is identical to the prior maria-n-mqtt
# script — that check belongs here because the maria fixture is the one
# that exercises the most subsystems in one container.
#
# Usage: scripts/test-mariadb.sh          # build + e2e (amd64)
#        BUILD=0 scripts/test-mariadb.sh  # reuse the existing ha-weewx-test image
#        ARCH=aarch64 scripts/test-mariadb.sh
set -euo pipefail
cd "$(dirname "$0")/.."

ARCH="${ARCH:-amd64}"
BUILD="${BUILD:-1}"
COMPOSE=(docker compose -p ha-weewx-mariadb -f docker-compose.mariadb.yml)

cleanup() { "${COMPOSE[@]}" down -v --remove-orphans >/dev/null 2>&1 || true; }
trap cleanup EXIT

if [[ "$BUILD" == "1" ]]; then
  docker build \
    --build-arg "BUILD_FROM=ghcr.io/home-assistant/${ARCH}-base-debian:trixie" \
    -t ha-weewx-test .
fi

mkdir -p test-results

"${COMPOSE[@]}" up --build --abort-on-container-exit --exit-code-from e2e-tests

# Log-cleanliness guard: the /dev/log "Logging error" spam is stderr meta-output
# that never reaches the e2e container, so check it here while logs still exist.
if "${COMPOSE[@]}" logs weewx 2>&1 | grep -qE 'Logging error|/dev/log'; then
  echo "FAIL: syslog (/dev/log) spam in weewx logs"
  exit 1
fi

echo "=== mariadb e2e OK ==="
