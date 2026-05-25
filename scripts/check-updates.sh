#!/usr/bin/env bash
# Check for newer versions of all pinned dependencies.
# Run this periodically and update the Dockerfile when new versions appear.
set -euo pipefail

RED='\033[0;31m'
GRN='\033[0;32m'
YLW='\033[1;33m'
NC='\033[0m'

latest_pypi() { pip index versions "$1" 2>/dev/null | head -1 | grep -oP '\d+\.\d+[\.\d]*' | head -1; }
latest_tag() { curl -sf "https://api.github.com/repos/$1/tags" | python3 -c "import json,sys; t=json.load(sys.stdin); print(t[0]['name'] if t else 'none')"; }
latest_commit() { curl -sf "https://api.github.com/repos/$1/commits?per_page=1" | python3 -c "import json,sys; print(json.load(sys.stdin)[0]['sha'][:7])"; }

check_pypi() {
  local pkg="$1" pinned="$2"
  local latest
  latest=$(latest_pypi "$pkg")
  if [[ "$latest" == "$pinned" ]]; then
    echo -e "  ${GRN}OK${NC}  $pkg  pinned=$pinned  latest=$latest"
  else
    echo -e "  ${YLW}NEW${NC} $pkg  pinned=${RED}$pinned${NC}  latest=${GRN}$latest${NC}"
  fi
}

check_tag() {
  local label="$1" repo="$2" pinned="$3"
  local latest
  latest=$(latest_tag "$repo")
  if [[ "$latest" == "$pinned" ]]; then
    echo -e "  ${GRN}OK${NC}  $label  pinned=$pinned  latest=$latest"
  else
    echo -e "  ${YLW}NEW${NC} $label  pinned=${RED}$pinned${NC}  latest=${GRN}$latest${NC}"
  fi
}

check_commit() {
  local label="$1" repo="$2" pinned="$3"
  local latest
  latest=$(latest_commit "$repo")
  if [[ "$latest" == "$pinned" ]]; then
    echo -e "  ${GRN}OK${NC}  $label  pinned=$pinned  latest=$latest"
  else
    echo -e "  ${YLW}NEW${NC} $label  pinned=${RED}$pinned${NC}  latest=${GRN}$latest${NC}"
  fi
}

echo "=== PyPI packages ==="
check_pypi "weewx" "5.3.1"

echo ""
echo "=== GitHub releases / tags ==="
check_tag "felddy/weewx-home-assistant" "felddy/weewx-home-assistant" "v1.0.0"
check_tag "weewx-forecast" "chaunceygardiner/weewx-forecast" "v4.1"
check_tag "fuzzy-archer" "brewster76/fuzzy-archer" "v4.4"
check_tag "WeeWX-MQTTSubscribe" "bellrichm/WeeWX-MQTTSubscribe" "v3.1.0"
check_tag "weewx-opensensemap" "sbsrouteur/weewx-opensensemap" "V0.3"
check_tag "weewx-previmeteo" "previmeteo/weewx-previmeteo" "v0.1"
check_tag "weewx-purpleair" "bakerkj/weewx-purpleair" "v0.9"
check_tag "realtime-gauge-data" "hoetzgit/weewx-realtime_gauge-data" "v0.6.0"
check_tag "weewx-windy" "matthewwall/weewx-windy" "0.3"

echo ""
echo "=== Pinned commits (check for newer tags or significant changes) ==="
check_commit "weewx-emoncms" "matthewwall/weewx-emoncms" "7c04113"
check_commit "weewx-exfoliation" "matthewwall/weewx-exfoliation" "9f77f4d"
check_commit "weewx-owm" "matthewwall/weewx-owm" "297dd97"
check_commit "weewx-thingspeak" "matthewwall/weewx-thingspeak" "a1ffa8e"
check_commit "weewx-wcloud" "matthewwall/weewx-wcloud" "83ee792"
check_commit "weewx-wetter" "matthewwall/weewx-wetter" "50a7f68"
check_commit "weewx-windfinder" "matthewwall/weewx-windfinder" "07ccbc3"
check_commit "weewx-windguru" "claudobahn/weewx-windguru" "c0a9b04"
