#!/command/with-contenv bash
# shellcheck shell=bash
set -euo pipefail

echo "ha-weewx version=${HA_WEEWX_VERSION:-unknown}"

WEEWX_CONF="/config/weewx.conf"

# Subdirs the bundled template references for SQLite DBs and log files. Make
# sure they exist before weewxd starts so it doesn't fail to open the SDBs or
# the RotatingFileHandler at first boot.
mkdir -p /config /config/db /config/log

# Seed weewx.conf from the bundled template on first start. Subsequent starts
# leave the file alone — edit it directly to change WeeWX configuration.
# Delete the file to force a re-seed.
if [[ ! -f "$WEEWX_CONF" ]]; then
  echo "First start: copying template to $WEEWX_CONF"
  echo "  Edit $WEEWX_CONF to configure your station, then restart the add-on."
  cp /etc/weewx.conf.template "$WEEWX_CONF"
else
  echo "Using existing $WEEWX_CONF (edit directly to change WeeWX configuration)"
fi
