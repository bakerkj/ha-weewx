#!/usr/bin/env bash
# In-image self-checks for the ha-weewx addon image.
#
# Runs inside the built image via `docker run`. Asserts binary version,
# dep imports, patch hunks, bundled extensions, stock skins, weewx-mqtt
# absence, and s6/watchdog wiring. Each assert is named via the `check`
# helper; all run, failures summarized at the end.

set -uo pipefail

# --- in-image self-checks -----------------------------------------------

fail=0
check() {
  local name="$1"
  shift
  if "$@" >/dev/null 2>&1; then
    printf 'PASS  %s\n' "$name"
  else
    printf 'FAIL  %s\n' "$name"
    fail=1
  fi
}
has() { grep -qF "$1" "$2"; }               # literal substring
type_equals() { [ "$(cat "$1")" = "$2" ]; } # file content == value

WEEWX_HA=/opt/weewx/lib/python3.13/site-packages/weewx_ha
WEEDB=/opt/weewx/lib/python3.13/site-packages/weedb
WEEWX_BIN=/opt/weewx-data/bin
S6=/etc/s6-overlay/s6-rc.d

# binary + import health
check "weewxd binary runs" weewxd --version
check "runtime deps importable" python3 -c 'import weewx_ha, paho.mqtt.client, pydantic'
check "user.* modules importable" env PYTHONPATH=$WEEWX_BIN python3 -c 'import user.extensions, user.log_to_file, user.forecast, user.xstats, user.rain24h, user.xaggs'

# MQTT publisher (by felddy) patches applied.
#
# The three highest-value patches (state_class, NO_UNIT_KEYS, NEW_ARCHIVE
# bind) are verified by python behaviour assertions rather than literal
# substring greps: importing the patched module / AST-parsing the patched
# source proves the patch is structurally in place, not just that the
# token appears somewhere in the file. The remaining six still use the
# `has` substring check — they're lower-impact constants/keys where a
# token-match catches the realistic regression (an accidentally dropped
# entry) without needing the heavier scaffolding.
check "patch: MQTT publisher (by felddy): state_class injected in publish_discovery" \
  python3 -c "
import ast, pathlib, sys
src = pathlib.Path('$WEEWX_HA/config_publisher.py').read_text()
tree = ast.parse(src)
fn = next((n for n in ast.walk(tree)
           if isinstance(n, ast.FunctionDef) and n.name == 'publish_discovery'), None)
assert fn is not None, 'publish_discovery not found'
ok = any(
    isinstance(t, ast.Subscript)
    and isinstance(t.value, ast.Name) and t.value.id == 'payload'
    and isinstance(t.slice, ast.Constant) and t.slice.value == 'state_class'
    for node in ast.walk(fn)
    if isinstance(node, ast.Assign)
    for t in node.targets
)
sys.exit(0 if ok else 1)
"
check "patch: MQTT publisher (by felddy): txBatteryStatus int" has 'int(packet["txBatteryStatus"])' "$WEEWX_HA/preprocessor.py"
check "patch: MQTT publisher (by felddy): NO_UNIT_KEYS exported with forecast keys" \
  python3 -c "
from weewx_ha.utils import NO_UNIT_KEYS
import sys
sys.exit(0 if isinstance(NO_UNIT_KEYS, set) and {'forecastIcon', 'forecastRule'} <= NO_UNIT_KEYS else 1)
"
check "patch: MQTT publisher (by felddy): rainAlarm key" has '"rainAlarm"' "$WEEWX_HA/utils.py"
check "patch: MQTT publisher (by felddy): windrun key" has '"windrun"' "$WEEWX_HA/utils.py"
check "patch: MQTT publisher (by felddy): rain24h key" has '"rain24h"' "$WEEWX_HA/utils.py"
check "patch: MQTT publisher (by felddy): NEW_ARCHIVE_RECORD bound to on_weewx_archive" \
  python3 -c "
import ast, pathlib, sys
src = pathlib.Path('$WEEWX_HA/controller.py').read_text()
tree = ast.parse(src)
ok = False
for node in ast.walk(tree):
    if not isinstance(node, ast.Call):
        continue
    f = node.func
    if not (isinstance(f, ast.Attribute) and f.attr == 'bind'
            and isinstance(f.value, ast.Name) and f.value.id == 'self'):
        continue
    if len(node.args) != 2:
        continue
    a0, a1 = node.args
    if (isinstance(a0, ast.Name) and a0.id == 'NEW_ARCHIVE_RECORD'
        and isinstance(a1, ast.Attribute) and a1.attr == 'on_weewx_archive'
        and isinstance(a1.value, ast.Name) and a1.value.id == 'self'):
        ok = True
        break
sys.exit(0 if ok else 1)
"
check "patch: MQTT publisher (by felddy): on_weewx_archive" has 'def on_weewx_archive(self, event):' "$WEEWX_HA/controller.py"
check "patch: MQTT publisher (by felddy): uv_index round(1)" python3 -c "from weewx_ha.utils import UNIT_METADATA; import sys; sys.exit(0 if UNIT_METADATA['uv_index']['value_template'] == '{{ value | round(1) }}' else 1)"

# Bundled extensions installed — assertions derived from `# install: <path>`
# annotations alongside each URL in build/extensions.txt. Adding or removing
# a URL only requires editing extensions.txt, not this script. The
# annotations still have to be kept correct by hand — they're documented
# next to the URL but nothing automatically discovers them from upstream.
while IFS= read -r install_path; do
  case "$install_path" in
    bin/user/*)
      name="${install_path##*/}"
      check "ext: $name present" test -f "/opt/weewx-data/$install_path"
      ;;
    skins/*)
      name="${install_path#skins/}"
      check "ext: $name skin present" test -d "/opt/weewx-data/$install_path"
      ;;
    *)
      echo "FAIL  extensions.txt: unrecognised install path: $install_path"
      fail=1
      ;;
  esac
done < <(grep -E '^# install: ' /work/build/extensions.txt | sed 's/^# install: //')

# rtgd is installed by build/install_rtgd.py (not weectl — its install.py
# uses distutils). Assert both pieces survived.
check "ext: rtgd module present" test -f "$WEEWX_BIN/user/rtgd.py"
check "ext: RealtimeGauges skin present" test -d /opt/weewx-data/skins/RealtimeGauges

# weedb core patch — not under patches/extensions/; keep the substring check.
check "patch: weedb mysql reserved kw" has 're.sub(r"(?<!`)\b(interval|desc|offset)\b(?!`)"' "$WEEDB/mysql.py"

# Bundled-extension patches: behavioural assertions against the shipped
# user/* code. Each patch under patches/extensions/0001..0014 has a
# dedicated check_<name>() in build/check_patches.py that imports the
# patched module and exercises the changed code path — same import path
# (user.<mod>) the running addon uses. The script emits one
# PASS/FAIL line per patch in the same format as the `check` helper
# above, so the trailing fail-summary block catches any of them.
if PYTHONPATH=$WEEWX_BIN python3 /work/build/check_patches.py; then
  :
else
  fail=1
fi

# rtldavis Go binary built in the rtldavis-builder stage; weewx-rtldavis
# popen()s it when station_type=Rtldavis. Image must contain it executable.
check "rtldavis binary present" test -x /opt/rtldavis/bin/rtldavis
# The `|` belongs inside the assertion, not at check()'s shell level --
# otherwise check's stdout (PASS …librtlsdr…) feeds grep silently.
check "rtldavis links to librtlsdr" \
  sh -c 'ldd /opt/rtldavis/bin/rtldavis | grep librtlsdr | grep -qv "not found"'

# xtide built in the xtide-builder stage; weewx-forecast's [Forecast] XTide
# source popen()s /usr/bin/tide (its default prog path) and reads harmonics
# constants from /usr/share/xtide via /etc/xtide.conf. All three must ship.
check "xtide: tide binary present" test -x /usr/bin/tide
check "xtide: harmonics data present" \
  sh -c 'ls /usr/share/xtide/harmonics-dwf-*-free.tcd >/dev/null 2>&1'
check "xtide: conf points to harmonics dir" has "/usr/share/xtide" /etc/xtide.conf
# End-to-end via weewx-forecast's own code path — invokes the exact
# argv weewx uses (XTideForecast.generate) and runs the exact CSV
# parser weewx-forecast will feed into the archive_forecast table
# (XTideForecast.parse). Asserts that at least one tide record with a
# valid H/L hilo comes back — this is the same in-memory record shape
# that would be inserted for the [Forecast] XTide source, so a break
# in tide's output, in the harmonics data, or in the parser catches
# here rather than at runtime on a live station.
# If 'Palo Alto Yacht Harbor' is renamed or removed from the free
# harmonics set in a future release, pick another covered station.
check "xtide: weewx-forecast generate+parse produces tide records" \
  env PYTHONPATH=$WEEWX_BIN python3 -c '
import sys, user.forecast as f
loc = "Palo Alto Yacht Harbor, San Francisco Bay, California"
lines = f.XTideForecast.generate(loc)
assert lines, "generate returned empty/None"
records = f.XTideForecast.parse(lines, location=loc)
assert records, "parse returned no records"
tides = [r for r in records if r.get("hilo") in ("H", "L") and r.get("method") == "XTide"]
assert tides, f"no XTide H/L records in {len(records)} parsed rows"
sys.exit(0)
'

# stock skin + accidentally-installed extension
check "skin: Seasons present" test -d /opt/weewx-data/skins/Seasons
check "weewx-mqtt NOT installed" test ! -f "$WEEWX_BIN/user/mqtt.py"

# nginx
check "nginx: njs module" test -f /usr/lib/nginx/modules/ngx_http_js_module.so
check "nginx: noaa.js filter" test -f /etc/nginx/njs/noaa.js

# s6 service wiring
check "s6: weewxd finish executable" test -x "$S6/weewxd/finish"
check "s6: nginx finish executable" test -x "$S6/nginx/finish"
check "s6: weewxd finish kills init" has 'kill -TERM 1' "$S6/weewxd/finish"
check "s6: nginx finish kills init" has 'kill -TERM 1' "$S6/nginx/finish"
check "s6: watchdog run executable" test -x "$S6/watchdog/run"
check "s6: watchdog script executable" test -x /etc/scripts/watchdog.py
check "s6: watchdog type=longrun" type_equals "$S6/watchdog/type" longrun
check "s6: watchdog depends on nginx" test -f "$S6/watchdog/dependencies.d/nginx"
check "s6: watchdog in user contents" test -f "$S6/user/contents.d/watchdog"
check "watchdog: script parses" /opt/weewx/bin/python3 -c "import ast; ast.parse(open('/etc/scripts/watchdog.py').read())"
check "watchdog: selfcheck passes" /opt/weewx/bin/python3 /etc/scripts/watchdog_selfcheck.py

if [ "$fail" -ne 0 ]; then
  echo
  echo "=== one or more in-image self-checks FAILED — see FAIL lines above ==="
  exit 1
fi
echo
echo "=== in-image self-checks passed ==="
