#!/usr/bin/env bash
# First-boot smoke test: start the add-on with an EMPTY /config and verify the
# default new-user experience that the docker-compose e2e bypasses (it mounts
# test/weewx.conf and uses MariaDB). Here weewx-init seeds the shipped template,
# weewxd runs on the template's Simulator + SQLite defaults, writes an archive
# record, and the Seasons report is generated and served by nginx.
#
# The template ships archive_interval=300, so the first archive record (and the
# report that follows) can take up to ~5 min; the fast checks (seeding, SQLite
# schema) run first so a failure pinpoints the template/seeding vs. the cycle.
#
# Usage: scripts/test-firstboot.sh                          # build + test
#        BUILD=0 IMAGE=ha-weewx-test scripts/test-firstboot.sh
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1

IMAGE="${IMAGE:-ha-weewx-firstboot-test}"
PORT="${PORT:-18098}"
CTR="ha-weewx-firstboot-ctr"
BUILD="${BUILD:-1}"
ARCH="${ARCH:-amd64}"
RECORD_TIMEOUT="${RECORD_TIMEOUT:-420}" # max wait for the first archive record + report

if [[ "$BUILD" == "1" ]]; then
  docker build \
    --build-arg "BUILD_FROM=ghcr.io/home-assistant/${ARCH}-base-debian:trixie" \
    -t "$IMAGE" .
fi

docker rm -f "$CTR" >/dev/null 2>&1 || true
cleanup() { docker rm -f "$CTR" >/dev/null 2>&1 || true; }
trap cleanup EXIT

fail=0
ok() { echo "PASS  $1"; }
bad() {
  echo "FAIL  $1"
  fail=1
}

dexec() { docker exec "$CTR" "$@"; }
archive_count() {
  dexec /opt/weewx/bin/python3 -c 'import sqlite3
try: print(sqlite3.connect("/config/weewx.sdb").execute("SELECT COUNT(*) FROM archive").fetchone()[0])
except Exception: print("noschema")' 2>/dev/null
}

# Start the FULL add-on (s6 -> weewx-init seeds template, weewxd + nginx run)
# with /config empty (no mounted conf) — the genuine first-boot state.
docker run -d --name "$CTR" -e S6_KEEP_ENV=1 -p "$PORT:8099" "$IMAGE" >/dev/null

# --- Phase 1: fast checks (seeding + SQLite schema), within ~60s ---
for _ in $(seq 1 30); do
  dexec test -f /config/weewx.conf 2>/dev/null && break
  sleep 2
done
if dexec test -f /config/weewx.conf 2>/dev/null; then
  ok "template seeded to /config/weewx.conf"
else
  bad "weewx.conf was not seeded"
fi
# Confirm it is the shipped template (Simulator default), not some other conf.
if dexec grep -q "station_type = Simulator" /config/weewx.conf 2>/dev/null; then
  ok "seeded conf is the shipped template (Simulator default)"
else
  bad "seeded conf is not the shipped template"
fi

for _ in $(seq 1 30); do
  [[ "$(archive_count)" != noschema ]] && break
  sleep 2
done
if [[ "$(archive_count)" != noschema ]]; then
  ok "SQLite DB + archive table created (/config/weewx.sdb)"
else
  bad "SQLite archive table not created"
fi

# --- Phase 2: the full first-boot cycle (archive record + report) ---
deadline=$(($(date +%s) + RECORD_TIMEOUT))
rec="" css=""
while [[ "$(date +%s)" -lt "$deadline" ]]; do
  c="$(archive_count)"
  s="$(curl -s -o /dev/null -w '%{http_code}' "http://localhost:$PORT/seasons.css" 2>/dev/null)"
  [[ "$c" =~ ^[0-9]+$ && "$c" -ge 1 ]] && rec=1
  [[ "$s" == 200 ]] && css=1
  [[ -n "$rec" && -n "$css" ]] && break
  sleep 10
done
if [[ -n "$rec" ]]; then ok "archive record written to SQLite (count>=1)"; else bad "no archive record within ${RECORD_TIMEOUT}s"; fi
if [[ -n "$css" ]]; then ok "Seasons report generated + served (seasons.css 200)"; else bad "seasons.css not served within ${RECORD_TIMEOUT}s"; fi

echo
if [[ "$fail" == 0 ]]; then
  echo "=== first-boot OK ==="
else
  echo "=== first-boot FAILED ==="
  docker logs "$CTR" 2>&1 | tail -30
  exit 1
fi
