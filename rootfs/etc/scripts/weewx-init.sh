#!/command/with-contenv bash
# shellcheck shell=bash
set -euo pipefail

WEEWX_CONF="/config/weewx.conf"

mkdir -p /config

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
