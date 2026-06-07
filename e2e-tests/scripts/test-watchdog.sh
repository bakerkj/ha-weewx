#!/usr/bin/env bash
# Watchdog e2e -- verifies that the addon container exits when
#   Phase 1: weewxd is killed (s6 finish script halts the tree)
#   Phase 2: nginx is killed (s6 finish script halts the tree)
#   Phase 3: the configurable HTTP-poll watchdog stays stale long enough
# and that the container does NOT exit when
#   Phase 4: watchdog is enabled, target is fresh, everything is healthy
#
# Each phase runs in its own container instance so a failed phase doesn't
# poison the next. The watchdog uses /data/options.json as HA Supervisor
# would; we mount a synthetic file for Phases 3 and 4.
#
# Usage: e2e-tests/scripts/test-watchdog.sh                       # build + test
#        BUILD=0 IMAGE=ha-weewx-test e2e-tests/scripts/test-watchdog.sh
set -uo pipefail
cd "$(dirname "$0")/../.." || exit 1

IMAGE="${IMAGE:-ha-weewx-watchdog-test}"
PORT="${PORT:-18099}"
CTR="ha-weewx-watchdog-ctr"
BUILD="${BUILD:-1}"
ARCH="${ARCH:-amd64}"
INIT_TIMEOUT="${INIT_TIMEOUT:-90}" # nginx must be up by here
EXIT_TIMEOUT="${EXIT_TIMEOUT:-15}" # how long to wait for the container to die after the kill

if [[ "$BUILD" == "1" ]]; then
  docker build \
    --build-arg "BUILD_FROM=ghcr.io/home-assistant/${ARCH}-base-debian:trixie" \
    -t "$IMAGE" .
fi

fail=0
ok() { echo "PASS  $1"; }
bad() {
  echo "FAIL  $1"
  fail=1
}

cleanup() {
  docker rm -f "$CTR" >/dev/null 2>&1 || true
  rm -rf "${TMPDIR_OPTS:-/nonexistent}" "${TMPDIR_OPTS4:-/nonexistent}" \
    "${TMPDIR_CONF4:-/nonexistent}"
}
trap cleanup EXIT

wait_for_nginx() {
  local start
  start=$(date +%s)
  while [[ $(($(date +%s) - start)) -lt "$INIT_TIMEOUT" ]]; do
    curl -fso /dev/null "http://localhost:$PORT/index.html" && return 0
    sleep 0.5
  done
  return 1
}

# nginx-init/nginx and weewx-init/weewxd are independent s6 chains, so
# nginx can be serving before weewxd has spawned. On slow runners (cold
# cache, aarch64) `pkill weewxd` can fire before the process exists.
wait_for_weewxd() {
  local start
  start=$(date +%s)
  while [[ $(($(date +%s) - start)) -lt "$INIT_TIMEOUT" ]]; do
    docker exec "$CTR" pgrep -x weewxd >/dev/null 2>&1 && return 0
    sleep 0.5
  done
  return 1
}

wait_for_exit() {
  # Returns the container's exit code, or "TIMEOUT".
  local code
  code=$(timeout "$EXIT_TIMEOUT" docker wait "$CTR" 2>/dev/null || true)
  if [[ -z "$code" ]]; then
    echo "TIMEOUT"
  else
    echo "$code"
  fi
}

run_phase() {
  local label=$1
  shift
  echo "### $label"
  docker rm -f "$CTR" >/dev/null 2>&1 || true
  docker run -d --name "$CTR" -e S6_KEEP_ENV=1 -p "$PORT:8099" "$@" "$IMAGE" >/dev/null
}

# ---------------------------------------------------------------------------
# Phase 1: kill weewxd, expect the addon to exit (finish script semantics)
# ---------------------------------------------------------------------------
run_phase "Phase 1: kill weewxd -> addon exits"
if ! wait_for_nginx; then
  bad "nginx did not come up within ${INIT_TIMEOUT}s"
elif ! wait_for_weewxd; then
  bad "weewxd did not start within ${INIT_TIMEOUT}s"
else
  ok "nginx + weewxd are running"
  # weewxd is a python process; the supervised PID is the immediate child of run.
  # pkill -x -9 weewxd kills it without giving s6 time to interpose.
  if docker exec "$CTR" pkill -x -9 weewxd; then
    ok "weewxd killed"
    code=$(wait_for_exit)
    if [[ "$code" == "TIMEOUT" ]]; then
      bad "container did not exit within ${EXIT_TIMEOUT}s after killing weewxd"
      docker logs "$CTR" 2>&1 | tail -15
    else
      ok "container exited (status=$code) after weewxd kill"
    fi
  else
    bad "could not pkill weewxd inside container"
  fi
fi
docker rm -f "$CTR" >/dev/null 2>&1 || true

# ---------------------------------------------------------------------------
# Phase 2: kill nginx, expect the addon to exit
# ---------------------------------------------------------------------------
run_phase "Phase 2: kill nginx -> addon exits"
if ! wait_for_nginx; then
  bad "nginx did not come up within ${INIT_TIMEOUT}s"
else
  ok "nginx is serving"
  if docker exec "$CTR" pkill -x -9 nginx; then
    ok "nginx killed"
    code=$(wait_for_exit)
    if [[ "$code" == "TIMEOUT" ]]; then
      bad "container did not exit within ${EXIT_TIMEOUT}s after killing nginx"
      docker logs "$CTR" 2>&1 | tail -15
    else
      ok "container exited (status=$code) after nginx kill"
    fi
  else
    bad "could not pkill nginx inside container"
  fi
fi
docker rm -f "$CTR" >/dev/null 2>&1 || true

# ---------------------------------------------------------------------------
# Phase 3: HTTP watchdog with a bogus path -> consecutive failures -> exit
# ---------------------------------------------------------------------------
echo "### Phase 3: watchdog stays stale -> addon exits"
TMPDIR_OPTS=$(mktemp -d)
# Aggressive thresholds so the test resolves in ~10-15s once nginx is up:
#   probe a path that 404s (never fresh), allow 2 failures at 3s apart.
cat >"$TMPDIR_OPTS/options.json" <<'JSON'
{
  "watchdog_path": "/does-not-exist.txt",
  "watchdog_max_age_seconds": 5,
  "watchdog_consecutive_failures": 2,
  "watchdog_interval_seconds": 3,
  "watchdog_startup_grace_seconds": 0
}
JSON
run_phase "" -v "$TMPDIR_OPTS/options.json:/data/options.json:ro"
if ! wait_for_nginx; then
  bad "nginx did not come up within ${INIT_TIMEOUT}s"
else
  ok "nginx is serving"
  # threshold(2) * interval(3) ~ 6-9s after watchdog start; give 30s
  EXIT_TIMEOUT=30 code=$(wait_for_exit)
  if [[ "$code" == "TIMEOUT" ]]; then
    bad "watchdog did not trigger exit within 30s"
    docker logs "$CTR" 2>&1 | tail -20
  else
    ok "watchdog triggered exit (status=$code) on bogus path"
  fi
fi

docker rm -f "$CTR" >/dev/null 2>&1 || true

# ---------------------------------------------------------------------------
# Phase 4: healthy nginx + a fresh, weewxd-written /index.html -> watchdog
# does NOT trigger exit. Exercises both the structural probe path (header
# inheritance, Last-Modified parsing) AND the freshness comparison.
#
# nginx-init.sh seeds /config/www/index.html at container start, but only
# as a placeholder; its mtime is fixed at T=0 and would go stale inside a
# tight max_age. To get a meaningful freshness assertion we override
# weewx.conf with archive_interval=10s + archive_delay=0 so weewxd's first
# report cycle rewrites /index.html within ~12s of container start, then
# poll Last-Modified until it advances past phase4_start+5s -- so only a
# real weewxd write satisfies the gate, not the seeded stub.
# ---------------------------------------------------------------------------
echo "### Phase 4: healthy weewx -> watchdog does NOT exit"
TMPDIR_OPTS4=$(mktemp -d)
TMPDIR_CONF4=$(mktemp -d)
# Extract the runtime template from the image and tighten the archive
# cadence. --entrypoint cat sidesteps s6-overlay's init for this one-off.
docker run --rm --entrypoint cat "$IMAGE" /etc/weewx.conf.template \
  >"$TMPDIR_CONF4/weewx.conf"
sed -i \
  -e 's/^\([[:space:]]*archive_interval[[:space:]]*=[[:space:]]*\)[0-9]\+/\110/' \
  -e 's/^\([[:space:]]*archive_delay[[:space:]]*=[[:space:]]*\)[0-9]\+/\10/' \
  "$TMPDIR_CONF4/weewx.conf"
# grace=25 covers nginx-init + weewxd startup + first archive cycle on a
# cold CI runner. max_age=15 is tight enough that a regression in the age
# comparison (wrong sign, wrong timezone, off-by-one) would fail this
# phase.
cat >"$TMPDIR_OPTS4/options.json" <<'JSON'
{
  "watchdog_path": "/index.html",
  "watchdog_max_age_seconds": 15,
  "watchdog_consecutive_failures": 2,
  "watchdog_interval_seconds": 1,
  "watchdog_startup_grace_seconds": 25
}
JSON
phase4_start=$(date +%s)
run_phase "" \
  -v "$TMPDIR_OPTS4/options.json:/data/options.json:ro" \
  -v "$TMPDIR_CONF4/weewx.conf:/config/weewx.conf:ro"
if ! wait_for_nginx; then
  bad "nginx did not come up within ${INIT_TIMEOUT}s"
else
  ok "nginx is serving"
  # Poll Last-Modified until weewxd's first report-engine run overwrites
  # the nginx-init stub. Stub mtime is within ~1s of phase4_start; gate on
  # lm_epoch > phase4_start+5 so only a real weewxd write trips the check.
  wrote_deadline=$((phase4_start + 45))
  wrote=0
  while [[ $(date +%s) -lt $wrote_deadline ]]; do
    lm=$(curl -sI "http://localhost:$PORT/index.html" |
      sed -n 's/^[Ll]ast-[Mm]odified:[[:space:]]*//p' | tr -d '\r\n')
    if [[ -n "$lm" ]]; then
      lm_epoch=$(date -d "$lm" +%s 2>/dev/null || echo 0)
      if [[ $lm_epoch -gt $((phase4_start + 5)) ]]; then
        wrote=1
        break
      fi
    fi
    sleep 1
  done
  if [[ $wrote -ne 1 ]]; then
    bad "weewxd did not refresh /index.html within 45s"
    docker logs "$CTR" 2>&1 | tail -30
  else
    ok "weewxd refreshed /index.html (first archive cycle ran)"
    # Watchdog timeline from phase4_start: grace=25 -> first probe T+25,
    # threshold*interval=2 -> SIGTERM-if-failing by T+27. Observe until
    # T+30 (3s buffer for the kill path).
    observe_until=$((phase4_start + 30))
    now=$(date +%s)
    if [[ $now -lt $observe_until ]]; then
      sleep $((observe_until - now))
    fi
    if [[ "$(docker inspect -f '{{.State.Running}}' "$CTR" 2>/dev/null)" != "true" ]]; then
      bad "container exited despite healthy weewx + fresh /index.html"
      docker logs "$CTR" 2>&1 | tail -30
    else
      ok "container still running after watchdog observation"
    fi
    if docker logs "$CTR" 2>&1 | grep -qE "watchdog: failure [0-9]+/"; then
      bad "watchdog logged a probe failure against a healthy /index.html"
      docker logs "$CTR" 2>&1 | grep "watchdog:" | tail -10
    else
      ok "no watchdog probe failures logged"
    fi
  fi
fi
rm -rf "$TMPDIR_OPTS4" "$TMPDIR_CONF4"

echo
if [[ "$fail" == 0 ]]; then
  echo "=== watchdog e2e OK ==="
else
  echo "=== watchdog e2e FAILED ==="
  exit 1
fi
