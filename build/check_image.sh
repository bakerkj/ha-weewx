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

# MQTT publisher (by felddy) patches applied
check "patch: MQTT publisher (by felddy): state_class" has '"state_class"' "$WEEWX_HA/config_publisher.py"
check "patch: MQTT publisher (by felddy): txBatteryStatus int" has 'int(packet["txBatteryStatus"])' "$WEEWX_HA/preprocessor.py"
check "patch: MQTT publisher (by felddy): NO_UNIT_KEYS" has 'NO_UNIT_KEYS' "$WEEWX_HA/utils.py"
check "patch: MQTT publisher (by felddy): rainAlarm key" has '"rainAlarm"' "$WEEWX_HA/utils.py"
check "patch: MQTT publisher (by felddy): windrun key" has '"windrun"' "$WEEWX_HA/utils.py"
check "patch: MQTT publisher (by felddy): rain24h key" has '"rain24h"' "$WEEWX_HA/utils.py"
check "patch: MQTT publisher (by felddy): NEW_ARCHIVE bind" has 'self.bind(NEW_ARCHIVE_RECORD, self.on_weewx_archive)' "$WEEWX_HA/controller.py"
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

# Bundled-extension patches: assert the post-patch hunk is on disk.
check "patch: previmeteo get_site_dict" has 'weewx.restx.get_site_dict' "$WEEWX_BIN/user/previmeteo.py"
check "patch: emoncms skip_upload" has 'AbortedPost("skip_upload")' "$WEEWX_BIN/user/emoncms.py"
check "patch: rtgd obs-in-self guard" has 'if obs in self:' "$WEEWX_BIN/user/rtgd.py"
check "patch: forecast Zambretti SQL" has 'ORDER BY dateTime DESC LIMIT 1" % dbm.table_name' "$WEEWX_BIN/user/forecast.py"
check "patch: weedb mysql reserved kw" has 're.sub(r"(?<!`)\b(interval|desc|offset)\b(?!`)"' "$WEEDB/mysql.py"

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
