#!/usr/bin/env bash
# Build the add-on image, then run the pytest e2e suite against it (MariaDB +
# Mosquitto + weewx via docker-compose.test.yml). The heavy lifting — waiting
# for data, the MQTT birth-handshake, the assertions — lives in the e2e-tests
# pytest container; this script just orchestrates and adds the one check pytest
# can't see: /dev/log syslog spam (stderr-only, never reaches the e2e container).
#
# Usage: scripts/test.sh            # build + e2e (amd64)
#        BUILD=0 scripts/test.sh    # reuse the existing ha-weewx-test image
#        ARCH=aarch64 scripts/test.sh
set -euo pipefail
cd "$(dirname "$0")/.."

ARCH="${ARCH:-amd64}"
BUILD="${BUILD:-1}"
COMPOSE=(docker compose -p ha-weewx-test -f docker-compose.test.yml)

cleanup() { "${COMPOSE[@]}" down -v --remove-orphans >/dev/null 2>&1 || true; }
trap cleanup EXIT

if [[ "$BUILD" == "1" ]]; then
  docker build \
    --build-arg "BUILD_FROM=ghcr.io/home-assistant/${ARCH}-base-debian:trixie" \
    -t ha-weewx-test .
fi

mkdir -p test-results

# Brings up mariadb + mosquitto + weewx (all healthchecked), then the
# e2e-tests pytest container; the whole run exits with pytest's code.
"${COMPOSE[@]}" up --build --abort-on-container-exit --exit-code-from e2e-tests

# Log-cleanliness guard: the /dev/log "Logging error" spam is stderr meta-output
# that never reaches the e2e container, so check it here while logs still exist.
if "${COMPOSE[@]}" logs weewx 2>&1 | grep -qE 'Logging error|/dev/log'; then
  echo "FAIL: syslog (/dev/log) spam in weewx logs"
  exit 1
fi

echo "=== integration OK ==="
