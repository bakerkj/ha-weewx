#!/usr/bin/env bash
# SQLite + Template e2e — the default new-user path (the maria+mqtt e2e instead
# mounts test/weewx.conf + MariaDB). Boots the image with an empty /config.
#
#   Phase 1 — start with an EMPTY /config so weewx-init seeds the *shipped*
#             template, and assert the seeding + the SQLite schema init.
#   Phase 2 — drop archive_interval to 5s (the template ships 300s, which would
#             make the first archive record take up to ~5 min) and restart, then
#             assert the full loop -> archive -> report -> nginx cycle, which is
#             the same code path regardless of the interval.
#
# Usage: scripts/test-sqlite-n-template.sh                  # build + test
#        BUILD=0 IMAGE=ha-weewx-test scripts/test-sqlite-n-template.sh
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1

IMAGE="${IMAGE:-ha-weewx-sqlite-template-test}"
PORT="${PORT:-18098}"
CTR="ha-weewx-sqlite-template-ctr"
BUILD="${BUILD:-1}"
ARCH="${ARCH:-amd64}"
SEED_TIMEOUT="${SEED_TIMEOUT:-60}"    # wait for seeding + SQLite schema
CYCLE_TIMEOUT="${CYCLE_TIMEOUT:-120}" # wait for the archive record + report (at 15s interval)

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
try: print(sqlite3.connect("/config/db/weewx.sdb").execute("SELECT COUNT(*) FROM archive").fetchone()[0])
except Exception: print("noschema")' 2>/dev/null
}

# --- Phase 1: first boot from an empty /config (seeds the shipped template) ---
echo "### Phase 1: first boot — seed shipped template + init SQLite"
docker run -d --name "$CTR" -e S6_KEEP_ENV=1 -p "$PORT:8099" "$IMAGE" >/dev/null
start=$(date +%s)
seeded="" schema=""
while [[ $(($(date +%s) - start)) -lt "$SEED_TIMEOUT" ]]; do
  conf=no
  dexec test -f /config/weewx.conf 2>/dev/null && conf=yes
  n="$(archive_count)"
  echo "  [$(($(date +%s) - start))s] weewx.conf=${conf}  sqlite_archive=${n}"
  [[ "$conf" == yes ]] && seeded=1
  [[ "$n" != noschema ]] && schema=1
  [[ -n "$seeded" && -n "$schema" ]] && break
  sleep 3
done
if [[ -n "$seeded" ]] && dexec grep -q "station_type = Simulator" /config/weewx.conf 2>/dev/null; then
  ok "shipped template seeded to /config/weewx.conf"
else
  bad "template was not seeded"
fi
[[ -n "$schema" ]] && ok "SQLite DB + archive table created (/config/db/weewx.sdb)" || bad "SQLite archive table not created"

# --- Phase 2: shorten the interval and restart, then exercise the cycle ---
echo "### Phase 2: set archive_interval=5s, restart, run the archive+report cycle"
# sed (byte-level) rather than configobj: the template's comments contain em
# dashes, and configobj.write() defaults to ASCII and would choke on them.
dexec sed -i -E 's/^( *archive_interval *=).*/\1 5/; s/^( *archive_delay *=).*/\1 3/' /config/weewx.conf ||
  bad "could not rewrite archive_interval"
if dexec grep -q "archive_interval = 5" /config/weewx.conf 2>/dev/null; then
  ok "archive_interval lowered to 5s for the cycle"
else
  bad "archive_interval edit did not apply"
fi
docker restart "$CTR" >/dev/null
start=$(date +%s)
rec="" css=""
while [[ $(($(date +%s) - start)) -lt "$CYCLE_TIMEOUT" ]]; do
  c="$(archive_count)"
  s="$(curl -s -o /dev/null -w '%{http_code}' "http://localhost:$PORT/seasons.css" 2>/dev/null)"
  echo "  [$(($(date +%s) - start))s] sqlite_archive=${c}  seasons.css=${s}"
  [[ "$c" =~ ^[0-9]+$ && "$c" -ge 1 ]] && rec=1
  [[ "$s" == 200 ]] && css=1
  [[ -n "$rec" && -n "$css" ]] && break
  sleep 5
done
[[ -n "$rec" ]] && ok "archive record written to SQLite (count>=1)" || bad "no archive record within ${CYCLE_TIMEOUT}s"
[[ -n "$css" ]] && ok "Seasons report generated + served by nginx (seasons.css 200)" || bad "seasons.css not served within ${CYCLE_TIMEOUT}s"

# weewxd must log no ERROR/CRITICAL across first boot. Match the space-delimited
# level field so an INFO line that merely mentions "error" (e.g. "Clock error
# is ...") is not a false positive.
if docker logs "$CTR" 2>&1 | grep -qE ' (ERROR|CRITICAL) '; then
  bad "weewxd logged ERROR/CRITICAL on first boot:"
  docker logs "$CTR" 2>&1 | grep -E ' (ERROR|CRITICAL) ' | head
else
  ok "no ERROR/CRITICAL in the weewxd log"
fi

# Syslog-spam guard: the "Logging error" / "/dev/log" Python-logging
# traceback (from a [Logging] config that falls back to syslog) is
# stderr meta-output that never appears as an INFO/ERROR level line,
# so the grep above misses it.
if docker logs "$CTR" 2>&1 | grep -qE 'Logging error|/dev/log'; then
  bad "syslog (/dev/log) spam in weewxd log"
  docker logs "$CTR" 2>&1 | grep -E 'Logging error|/dev/log' | head
else
  ok "no syslog (/dev/log) spam in the weewxd log"
fi

echo
if [[ "$fail" == 0 ]]; then
  echo "=== sqlite + template e2e OK ==="
else
  echo "=== sqlite + template e2e FAILED ==="
  docker logs "$CTR" 2>&1 | tail -30
  exit 1
fi
