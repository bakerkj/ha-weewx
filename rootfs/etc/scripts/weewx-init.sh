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
# leave the file alone - edit it directly to change WeeWX configuration.
# Delete the file to force a re-seed.
if [[ ! -f "$WEEWX_CONF" ]]; then
  echo "First start: copying template to $WEEWX_CONF"
  echo "  Edit $WEEWX_CONF to configure your station, then restart the add-on."
  cp /etc/weewx.conf.template "$WEEWX_CONF"
else
  echo "Using existing $WEEWX_CONF (edit directly to change WeeWX configuration)"
fi

# LoopData and weewx-celestial write /dev/shm/weewx/loop-data.txt every
# LOOP packet. Ensure the directory exists on tmpfs before weewxd boots
# (weewx-loopdata refuses to start if its output dir is missing).
mkdir -p /dev/shm/weewx

# Create marine_data's three tables (coops_realtime, tide_table,
# ndbc_data) if marine is enabled. The shim owns the DDL itself
# (portable across MariaDB + SQLite). Idempotent; no-op when the
# tables already exist or marine isn't enabled. Soft-fail: a shim
# error must not block weewxd from starting under set -euo pipefail.
# If tables never get created, the marine service will surface it at
# first write; other reports/services keep running.
WEEWX_CONF="$WEEWX_CONF" python3 /etc/scripts/init_marine_schema.py ||
  echo "WARNING: init_marine_schema.py failed; marine tables may not exist" >&2
