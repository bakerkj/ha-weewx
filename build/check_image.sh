#!/usr/bin/env bash
# Self-contained build-time checks for the ha-weewx addon image.
#
# Runs inside the built image via `docker run`; expects the repo root to
# be bind-mounted at /work so this script and build/check_felddy_units.py
# are reachable.
#
# Two phases:
#   1) Cheap in-image asserts: binary version, dep imports, patch hunks
#      present, bundled extensions installed, stock skins present,
#      weewx-mqtt removed, s6 services + watchdog wired.
#   2) Felddy unit/device_class sweep against a transient homeassistant
#      install. Heavy (gcc + ~250 MB pip install) — uses uv with the
#      cache dir bind-mounted from the host (CI: gha-cached via
#      actions/cache), so wheels are reused between runs when HA_VERSION
#      is unchanged.

set -euo pipefail

HA_VERSION="${HA_VERSION:-2026.1.3}"

# --- 1. in-image self-checks ---------------------------------------------
weewxd --version
python3 -c "import weewx_ha, paho.mqtt.client, pydantic"
PYTHONPATH=/opt/weewx-data/bin python3 -c "import user.extensions, user.log_to_file, user.forecast, user.xstats, user.rain24h, user.xaggs"
grep -qF '"state_class"' /opt/weewx/lib/python3.13/site-packages/weewx_ha/config_publisher.py
grep -qF 'int(packet["txBatteryStatus"])' /opt/weewx/lib/python3.13/site-packages/weewx_ha/preprocessor.py
grep -qF 'NO_UNIT_KEYS' /opt/weewx/lib/python3.13/site-packages/weewx_ha/utils.py
grep -qF '"rainAlarm"' /opt/weewx/lib/python3.13/site-packages/weewx_ha/utils.py
grep -qF '"windrun"' /opt/weewx/lib/python3.13/site-packages/weewx_ha/utils.py
grep -qF 'self.bind(NEW_ARCHIVE_RECORD, self.on_weewx_archive)' /opt/weewx/lib/python3.13/site-packages/weewx_ha/controller.py
grep -qF 'def on_weewx_archive(self, event):' /opt/weewx/lib/python3.13/site-packages/weewx_ha/controller.py
grep -qF '"rain24h"' /opt/weewx/lib/python3.13/site-packages/weewx_ha/utils.py
python3 -c "from weewx_ha.utils import UNIT_METADATA; assert UNIT_METADATA['uv_index']['value_template'] == '{{ value | round(1) }}', UNIT_METADATA['uv_index']"
test -f /opt/weewx-data/bin/user/rain24h.py
test -f /opt/weewx-data/bin/user/xaggs.py
grep -qF 'weewx.restx.get_site_dict' /opt/weewx-data/bin/user/previmeteo.py
grep -qF 'AbortedPost("skip_upload")' /opt/weewx-data/bin/user/emoncms.py
grep -qF 'if obs in self:' /opt/weewx-data/bin/user/rtgd.py
grep -qF "ORDER BY dateTime DESC LIMIT 1\" % dbm.table_name" /opt/weewx-data/bin/user/forecast.py
grep -qF "(interval|desc|offset)" /opt/weewx/lib/python3.13/site-packages/weedb/mysql.py
test -d /opt/weewx-data/skins/Seasons
test ! -f /opt/weewx-data/bin/user/mqtt.py
test -f /usr/lib/nginx/modules/ngx_http_js_module.so
test -f /etc/nginx/njs/noaa.js
test -x /etc/s6-overlay/s6-rc.d/weewxd/finish
test -x /etc/s6-overlay/s6-rc.d/nginx/finish
grep -qF 'kill -TERM 1' /etc/s6-overlay/s6-rc.d/weewxd/finish
grep -qF 'kill -TERM 1' /etc/s6-overlay/s6-rc.d/nginx/finish
test -x /etc/s6-overlay/s6-rc.d/watchdog/run
test -x /etc/scripts/watchdog.py
[ "$(cat /etc/s6-overlay/s6-rc.d/watchdog/type)" = "longrun" ]
test -f /etc/s6-overlay/s6-rc.d/watchdog/dependencies.d/nginx
test -f /etc/s6-overlay/s6-rc.d/user/contents.d/watchdog
/opt/weewx/bin/python3 -c "import ast; ast.parse(open('/etc/scripts/watchdog.py').read())"
/opt/weewx/bin/python3 /etc/scripts/watchdog_selfcheck.py
echo "build-time self-checks passed"

# --- 2. felddy unit/device_class sweep against transient HA install ------
# gcc + python3-dev for the couple of small wheels HA pulls in
# (propcache, etc.) that don't ship platform binaries for our arch.
apt-get update
apt-get install -y --no-install-recommends gcc python3-dev
# Install uv inline (not shipped in the addon image; ~5 s warm).
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="${HOME}/.local/bin:$PATH"
# The host's uv cache is bind-mounted at /root/.cache/uv so the HA
# wheel set is reused between CI runs when HA_VERSION is unchanged.
uv pip install --python /opt/weewx/bin/python3 "homeassistant==${HA_VERSION}"
PYTHONPATH=/opt/weewx-data/bin python3 /work/build/check_felddy_units.py
