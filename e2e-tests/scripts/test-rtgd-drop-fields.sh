#!/usr/bin/env bash
# E2E: assert the 0015 `[[[<field>]]] source =` escape hatch actually drops
# the field from gauge-data.txt (and the 0014/0016 patches keep rtgd healthy
# while it does so). Includes an explicit baseline phase so the test fails
# loudly if rtgd's default output ever changes to *not* include the indoor
# fields on its own (which would make the "after" assertion meaningless).
#
# Strategy:
#   Phase 1 — boot the locally-built ha-weewx-test image with the shipped
#             template + archive_interval=5s so an archive row lands quickly.
#             This pre-populates day_stats so rtgd.setup() doesn't trip the
#             upstream `stats_unit_system=None` startup race on a fresh DB.
#             (Unrelated to the patches under test — just gets rtgd to a
#             point where the LOOP thread is alive and emitting.)
#   Phase 2 — BASELINE: inject [RealtimeGaugeData] with NO FieldMap
#             overrides, restart, wait for gauge-data.txt, assert that
#             indoor fields ARE present. This is what fails if upstream
#             ever changes the default field set out from under us.
#   Phase 3 — APPLY OVERRIDES: add [[FieldMapExtensions]] entries setting
#             `source =` (empty) for every indoor (intemp/inhum) field,
#             restart, wait for gauge-data.txt.
#   Phase 4 — assert: zero indoor fields, all expected non-indoor fields
#             present, no KeyError / Thread exiting noise in the addon log
#             (would indicate the 0016 buffer-source guard regressed).
#
# Usage:  e2e-tests/scripts/test-rtgd-drop-fields.sh
#         BUILD=0 IMAGE=ha-weewx-test e2e-tests/scripts/test-rtgd-drop-fields.sh
set -uo pipefail

IMAGE="${IMAGE:-ha-weewx-test}"
BUILD="${BUILD:-1}"
ARCH="${ARCH:-amd64}"

if [[ "$BUILD" == "1" ]]; then
  docker build --build-arg "BUILD_FROM=ghcr.io/home-assistant/${ARCH}-base-debian:trixie" -t "$IMAGE" "$(dirname "$0")/../.."
fi
CTR="ha-weewx-e2e-intemp"
SEED_TIMEOUT=60
ARCHIVE_TIMEOUT=90
GAUGE_TIMEOUT=60

cleanup() { docker rm -f "$CTR" >/dev/null 2>&1 || true; }
trap cleanup EXIT
cleanup

CFG=$(mktemp -d)
chmod 777 "$CFG"
echo "config dir: $CFG"

# Shared helper: minimal [RealtimeGaugeData] block. $1 = extra body
# appended inside the section (e.g. the [[FieldMapExtensions]] block in
# Phase 3). Phase 2 calls this with an empty arg for a clean baseline.
rtgd_section() {
  cat <<RTGD

##############################################################################
[RealtimeGaugeData]
    rtgd_path = /dev/shm/weewx
    rtgd_path_create = true
    tick_interval = 1
    [[StringFormats]]
        degree_compass = %.0f
        inHg = %.3f
        inch = %.2f
        inch_per_hour = %.2f
        mile_per_hour = %.0f
    [[Groups]]
        group_altitude = foot
        group_pressure = inHg
        group_rain = inch
        group_speed = mile_per_hour
        group_temperature = degree_F
${1:-}
RTGD
}

# Strip any prior [RealtimeGaugeData] section from /config/weewx.conf and
# re-append a fresh one (so successive phases don't accumulate stale
# blocks).
write_rtgd() {
  local section_body="$1"
  docker exec -i "$CTR" python3 <<PYEOF
import re
p = "/config/weewx.conf"
src = open(p).read()
src = re.sub(
    r"\n##{20,}\n\[RealtimeGaugeData\][\s\S]*?(?=\n#{20,}\[|\Z)",
    "",
    src,
)
if "user.rtgd.RealtimeGaugeData" not in src:
    src = src.replace(
        "        report_services  = weewx.engine.StdReport",
        "        report_services  = weewx.engine.StdReport, user.rtgd.RealtimeGaugeData",
    )
src += """$section_body"""
open(p, "w").write(src)
PYEOF
}

# Fetch gauge-data.txt out of the container and into /tmp/gd.json. Wait
# up to GAUGE_TIMEOUT for it to exist + be non-trivial in size. Empty
# file ($1=stale_ok) means "must be newer than this size" — caller passes
# the previous bytes value to force the next emit cycle.
wait_for_gauge_data() {
  local start sz min_size="${1:-100}"
  start=$(date +%s)
  while [ $(($(date +%s) - start)) -lt "$GAUGE_TIMEOUT" ]; do
    if docker exec "$CTR" test -f /dev/shm/weewx/gauge-data.txt 2>/dev/null; then
      sz=$(docker exec "$CTR" stat -c %s /dev/shm/weewx/gauge-data.txt 2>/dev/null)
      if [ "${sz:-0}" -gt "$min_size" ] 2>/dev/null; then
        echo "  gauge-data.txt ready at $(($(date +%s) - start))s (${sz} bytes)"
        docker exec "$CTR" cat /dev/shm/weewx/gauge-data.txt >/tmp/gd.json
        return 0
      fi
    fi
    sleep 2
  done
  return 1
}

# --- Phase 1: boot, let weewx-init seed the shipped template ---
docker run -d --name "$CTR" -v "$CFG:/config" -e S6_KEEP_ENV=1 "$IMAGE" >/dev/null

start=$(date +%s)
while [ $(($(date +%s) - start)) -lt "$SEED_TIMEOUT" ]; do
  docker exec "$CTR" test -f /config/weewx.conf 2>/dev/null && {
    echo "seeded at $(($(date +%s) - start))s"
    break
  }
  sleep 1
done

# Drop archive_interval to 5s so we hit the first archive fast (bypasses
# the unrelated stats_unit_system=None startup race in rtgd).
docker exec -i "$CTR" python3 <<'PYEOF'
import re
p = "/config/weewx.conf"
src = open(p).read()
src = re.sub(r"(\[StdArchive\].*?archive_interval\s*=\s*)\d+",
             r"\g<1>5", src, count=1, flags=re.S)
open(p, "w").write(src)
print("archive_interval=5")
PYEOF
docker restart "$CTR" >/dev/null

start=$(date +%s)
while [ $(($(date +%s) - start)) -lt "$ARCHIVE_TIMEOUT" ]; do
  n=$(docker exec "$CTR" /opt/weewx/bin/python3 -c '
import sqlite3
try:
    print(sqlite3.connect("/config/db/weewx.sdb").execute("SELECT COUNT(*) FROM archive").fetchone()[0])
except Exception: print(0)' 2>/dev/null)
  if [ "${n:-0}" -ge 1 ] 2>/dev/null; then
    echo "first archive landed at $(($(date +%s) - start))s (rows=$n)"
    break
  fi
  sleep 2
done

# --- Phase 2: BASELINE — rtgd with NO FieldMap overrides ---
echo
echo "### Phase 2: BASELINE — rtgd enabled, no [[FieldMapExtensions]]"
write_rtgd "$(rtgd_section)"
docker exec "$CTR" rm -f /dev/shm/weewx/gauge-data.txt 2>/dev/null
docker restart "$CTR" >/dev/null
wait_for_gauge_data || {
  echo "FAIL  baseline gauge-data.txt never appeared"
  exit 1
}

python3 - <<'PYEOF'
import json, sys
d = json.load(open("/tmp/gd.json"))
print(f"  baseline total fields: {len(d)}")
indoor = sorted(k for k in d if "intemp" in k.lower() or "inhum" in k.lower())
if not indoor:
    print(
        "FAIL  baseline gauge-data.txt has NO indoor fields — the after-state "
        "assertion is meaningless. Upstream rtgd may have changed its "
        "default field set; this test needs a different baseline obs."
    )
    sys.exit(1)
print(f"PASS  baseline has indoor fields ({len(indoor)} of them): {indoor}")
# Stash baseline field set so Phase 4 can compare.
open("/tmp/gd-baseline-fields.txt", "w").write("\n".join(sorted(d.keys())))
PYEOF

# --- Phase 3: APPLY OVERRIDES — same rtgd, plus empty-source entries ---
echo
echo "### Phase 3: APPLY 0015 OVERRIDES — empty-source for indoor fields"
write_rtgd "$(rtgd_section "    [[FieldMapExtensions]]
        [[[intemp]]]
            source =
        [[[intempTH]]]
            source =
        [[[intempTL]]]
            source =
        [[[TintempTH]]]
            source =
        [[[TintempTL]]]
            source =
        [[[inhum]]]
            source =
        [[[inhumTH]]]
            source =
        [[[inhumTL]]]
            source =
        [[[TinhumTH]]]
            source =
        [[[TinhumTL]]]
            source =")"
docker exec "$CTR" rm -f /dev/shm/weewx/gauge-data.txt 2>/dev/null
docker restart "$CTR" >/dev/null
wait_for_gauge_data || {
  echo "FAIL  after-overrides gauge-data.txt never appeared (boot loop?)"
  exit 1
}

# --- Phase 4: assertions ---
python3 - <<'PYEOF'
import json, sys
d = json.load(open("/tmp/gd.json"))
baseline = open("/tmp/gd-baseline-fields.txt").read().splitlines()
print(f"  after-override total fields: {len(d)} (baseline was {len(baseline)})")

indoor = sorted(k for k in d if "intemp" in k.lower() or "inhum" in k.lower())
if indoor:
    print(f"FAIL  indoor fields STILL in gauge-data.txt: {indoor}")
    sys.exit(1)
print("PASS  indoor fields dropped")

required = ["temp", "hum", "press", "dew", "apptemp", "heatindex", "wgust", "date", "timeUTC", "tempunit"]
missing = [k for k in required if k not in d]
if missing:
    print(f"FAIL  required fields missing: {missing}")
    sys.exit(1)
print(f"PASS  required fields present ({', '.join(required)})")

dropped = sorted(set(baseline) - set(d.keys()))
indoor_dropped = [k for k in dropped if "intemp" in k.lower() or "inhum" in k.lower()]
non_indoor_dropped = [k for k in dropped if k not in indoor_dropped]
if non_indoor_dropped:
    print(
        "FAIL  the override dropped non-indoor fields too — overreach: "
        f"{non_indoor_dropped}"
    )
    sys.exit(1)
print(f"PASS  only the requested indoor fields were dropped ({len(indoor_dropped)} of them)")

print(f"  sample: temp={d.get('temp')!r}  hum={d.get('hum')!r}  press={d.get('press')!r}  apptemp={d.get('apptemp')!r}")
PYEOF
rc=$?

# 0016 LOOP-thread guard assertion: no KeyError storm during the
# rtgd-thread startup window (cached LOOP packet w/ aggregate-field
# source not yet in self.buffer would pre-0016 raise `KeyError: 'appTemp'`
# and exit the thread with `Thread exiting. Reason: None`).
if docker logs "$CTR" 2>&1 | grep -qE 'KeyError|Thread exiting'; then
  echo "FAIL  KeyError / Thread exiting in addon log (0016 regression?):"
  docker logs "$CTR" 2>&1 | grep -E 'KeyError|Thread exiting' | head -5
  rc=1
else
  echo "PASS  no KeyError / Thread exiting (0016 loop-thread guard holds)"
fi

if [ $rc -eq 0 ]; then echo "==== ALL PASS ===="; else echo "==== FAILED ===="; fi
exit $rc
