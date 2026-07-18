#!/usr/bin/env bash
# Cache-behavior test for the add-on's nginx layer. Runs the REAL add-on image's
# nginx (via nginx-init.sh, bypassing s6/weewxd) against fixture report files and
# asserts: the Cache-Control tiers, brotli/gzip negotiation, the NOAA njs filter
# (current month/year vs. immutable history), and the /config/nginx-cache.conf
# override + its fallback when broken.
#
# Usage: e2e-tests/scripts/test-cache.sh                          # build + test
#        BUILD=0 IMAGE=ha-weewx-test e2e-tests/scripts/test-cache.sh   # reuse an image
set -uo pipefail
cd "$(dirname "$0")/../.." || exit 1

IMAGE="${IMAGE:-ha-weewx-cache-test}"
PORT="${PORT:-18099}"
CTR="ha-weewx-cache-test-ctr"
BUILD="${BUILD:-1}"
ARCH="${ARCH:-amd64}"

if [[ "$BUILD" == "1" ]]; then
  docker build \
    --build-arg "BUILD_FROM=ghcr.io/home-assistant/${ARCH}-base-debian:trixie" \
    -t "$IMAGE" .
fi

# UTC everywhere so the host-generated NOAA filenames and the njs filter's notion
# of "current month/year" agree regardless of where this runs.
CY="$(date -u +%Y)"
CYM="$(date -u +%Y-%m)"

WORK="$(mktemp -d)"
cleanup() {
  docker rm -f "$CTR" >/dev/null 2>&1 || true
  rm -rf "$WORK"
}
trap cleanup EXIT

# Build a fixture /config (weewx.conf with a distinct archive_interval, plus a
# www/ tree exercising every tier). Optional arg: an nginx-cache.conf override.
make_config() {
  local override="${1:-}"
  rm -rf "$WORK/config"
  mkdir -p "$WORK/config/www/NOAA" "$WORK/config/www/icons" "$WORK/config/www/font"
  cat >"$WORK/config/weewx.conf" <<'CONF'
[StdArchive]
    archive_interval = 120
CONF
  # HTML/CSS/JS padded past brotli_min_length (1024) so compression engages.
  {
    echo "<!doctype html><title>home</title>"
    head -c 2000 /dev/zero | tr '\0' x
  } >"$WORK/config/www/index.html"
  printf 'body{color:#000}/*%s*/\n' "$(head -c 1500 /dev/zero | tr '\0' x)" >"$WORK/config/www/seasons.css"
  printf 'console.log(1);//%s\n' "$(head -c 1500 /dev/zero | tr '\0' x)" >"$WORK/config/www/exfoliation.js"
  for f in daybarometer weekbarometer monthbarometer yearbarometer custombarometer; do
    echo PNG >"$WORK/config/www/$f.png"
  done
  echo "<!doctype html><title>forecast</title>" >"$WORK/config/www/forecast.html"
  echo PNG >"$WORK/config/www/icons/AF.png"
  echo WOFF >"$WORK/config/www/font/Roboto.woff2"
  printf 'User-agent: *\nDisallow:\n' >"$WORK/config/www/robots.txt"
  touch -d "60 days ago" "$WORK/config/www/robots.txt" # immutable, aged mtime
  echo "current year" >"$WORK/config/www/NOAA/NOAA-$CY.txt"
  echo "current month" >"$WORK/config/www/NOAA/NOAA-$CYM.txt"
  echo "ancient" >"$WORK/config/www/NOAA/NOAA-2020.txt"
  # The njs filter decides "fresh vs. immutable" from the file's mtime (parsed
  # out of the ETag), so the rollover-rewrite case stays correct independent of
  # the container TZ. Age the ancient NOAA file's mtime to match what its
  # 2020-era filename implies, the way a real WeeWX-on-disk archive would look.
  touch -d "2020-12-31 12:00:00 UTC" "$WORK/config/www/NOAA/NOAA-2020.txt"
  [[ -n "$override" ]] && cp "$override" "$WORK/config/nginx-cache.conf"
  return 0
}

# Start nginx-only from the add-on image (skip s6/weewxd), with gauge-data.txt
# seeded where the alias expects it. Returns once nginx answers.
start_nginx() {
  docker rm -f "$CTR" >/dev/null 2>&1 || true
  docker run --rm -d --name "$CTR" -e TZ=UTC -p "$PORT:8099" \
    -v "$WORK/config:/config" \
    --entrypoint bash "$IMAGE" \
    -c "mkdir -p /dev/shm/weewx && printf '{\"timeUTC\":\"x\"}' >/dev/shm/weewx/gauge-data.txt && bash /etc/scripts/nginx-init.sh && exec nginx -g 'daemon off;'" >/dev/null
  for _ in $(seq 1 40); do
    curl -fsS -o /dev/null "http://localhost:$PORT/seasons.css" 2>/dev/null && return 0
    sleep 0.5
  done
  echo "FAIL: nginx did not come up"
  docker logs "$CTR" 2>&1 | tail -20
  return 1
}

fail=0
cc_of() {
  curl -s -D - -o /dev/null "http://localhost:$PORT$1" |
    grep -i '^cache-control:' | tr -d '\r' | sed 's/^[^:]*: *//' | paste -sd', ' -
}
maxage_of() { grep -o 'max-age=[0-9]*' <<<"$1" | head -1 | cut -d= -f2; }

# exact <path> <max-age>   — assert exact max-age + public
exact() {
  local cc n
  cc="$(cc_of "$1")"
  n="$(maxage_of "$cc")"
  if [[ "$n" == "$2" && "$cc" == *public* ]]; then
    echo "PASS  $1 -> $cc"
  else
    echo "FAIL  $1 -> [$cc], want max-age=$2 + public"
    fail=1
  fi
}
# range <path> <min> <max> — assert max-age in range + public (mtime-based tiers)
range() {
  local cc n
  cc="$(cc_of "$1")"
  n="$(maxage_of "$cc")"
  if [[ -n "$n" && "$n" -ge "$2" && "$n" -le "$3" && "$cc" == *public* ]]; then
    echo "PASS  $1 -> $cc"
  else
    echo "FAIL  $1 -> [$cc], want max-age in [$2,$3] + public"
    fail=1
  fi
}
# enc <path> <accept-encoding> <expected> — assert negotiated Content-Encoding
enc() {
  local ce
  ce="$(curl -s -D - -o /dev/null -H "Accept-Encoding: $2" "http://localhost:$PORT$1" |
    grep -i '^content-encoding:' | tr -d '\r' | awk '{print $2}')"
  if [[ "$ce" == "$3" ]]; then
    echo "PASS  $1 ($2) -> Content-Encoding: $ce"
  else
    echo "FAIL  $1 ($2) -> got [${ce:-none}], want [$3]"
    fail=1
  fi
}

echo "### Scenario 1: default cache tiers (archive_interval=120)"
make_config ""
start_nginx || exit 1
range /index.html 90 120       # HTML: expires modified +archive_interval
range /forecast.html 3510 3570 # skin regenerates hourly (stale_age=3570)
range /daybarometer.png 90 120
range /weekbarometer.png 3540 3600
range /monthbarometer.png 10740 10800 # month_images aggregate_interval=10800
range /yearbarometer.png 86340 86400
# /icons/ directory listing must return 200 (autoindex), matching the behavior
# already in place for location / and /NOAA/. A 404 here would break any client
# that enumerates the icon set.
icons_code="$(curl -s -o /dev/null -w '%{http_code}' "http://localhost:$PORT/icons/")"
if [[ "$icons_code" == "200" ]]; then
  echo "PASS  /icons/ (autoindex) -> HTTP $icons_code"
else
  echo "FAIL  /icons/ (autoindex) -> got HTTP $icons_code, want 200"
  fail=1
fi
range /custombarometer.png 90 120 # unprefixed png -> day-tier fallback
exact /seasons.css 3600
exact /exfoliation.js 3600
exact /icons/AF.png 3600        # static, NOT treated as a plot
exact /robots.txt 86400         # flat 24h despite 60-day-old mtime
exact "/NOAA/NOAA-$CY.txt" 120  # current year  -> njs archive_interval
exact "/NOAA/NOAA-$CYM.txt" 120 # current month -> njs archive_interval
exact /NOAA/NOAA-2020.txt 86400 # immutable     -> njs 24h
exact /NOAA/ 120                # autoindex listing -> njs archive_interval
exact /gauge-data.txt 1
# stale-while-revalidate ties to archive_interval (=120 in this fixture) so a
# client can serve the cached copy immediately while revalidating in the
# background. The directive expands from $archive_interval, set at server
# scope by nginx-init.sh via /tmp/nginx-archive-interval.conf.
cc_gd="$(cc_of /gauge-data.txt)"
if [[ "$cc_gd" == *stale-while-revalidate=120* ]]; then
  echo "PASS  /gauge-data.txt -> stale-while-revalidate=120"
else
  echo "FAIL  /gauge-data.txt -> [$cc_gd], want stale-while-revalidate=120"
  fail=1
fi
enc /index.html "br,gzip" br
enc /index.html "gzip" gzip

echo "### Scenario 2: /config/nginx-cache.conf override (with __ARCHIVE__ token)"
cat >"$WORK/override.conf" <<'OVR'
location ~* \.png$ {
    expires modified +__ARCHIVE__s;
    add_header Cache-Control "public" always;
}
OVR
make_config "$WORK/override.conf"
start_nginx || exit 1
# The override replaces the whole tier set with one png rule; week/year drop from
# 3600/86400 to the archive_interval (120) — proving both the override took and
# __ARCHIVE__ expanded.
range /weekbarometer.png 90 120
range /yearbarometer.png 90 120

echo "### Scenario 3: broken override -> fallback to generated defaults"
printf 'location ~* { this is not valid nginx\n' >"$WORK/override-bad.conf"
make_config "$WORK/override-bad.conf"
start_nginx || {
  echo "FAIL: a broken override must fall back, not break startup"
  exit 1
}
range /yearbarometer.png 86340 86400 # default per-period tier restored

echo
if [[ "$fail" == 0 ]]; then
  echo "=== cache tests OK ==="
else
  echo "=== cache tests FAILED ==="
  exit 1
fi
