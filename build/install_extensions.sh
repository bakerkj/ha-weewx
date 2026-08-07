#!/usr/bin/env bash
# Install every WeeWX extension listed in extensions.txt via
# `weectl extension install`. A failed install aborts the build — silent
# skips let a broken/missing extension ship in the image undetected, and
# the in-image self-checks only assert presence of a handful of these.
#
# Expects:
#   /build/extensions.txt   — one URL per line; '#' comments allowed
#   /opt/weewx-data/weewx.conf — the build-time stub conf
#
# Bind-mounted into the Dockerfile RUN that consumes it; see Dockerfile
# for the corresponding --mount lines.

set -euo pipefail

LIST="${1:-/build/extensions.txt}"

# Retry each install on failure. weectl extension install downloads the
# archive from github via urllib, which surfaces transient github.com 5xx
# errors as fatal (no built-in retry). Those hiccups happen often enough to
# burn CI runs on unrelated PRs — retry with exponential backoff so a
# genuine failure still fails after MAX_ATTEMPTS, but a transient one
# doesn't.
#
# Retries the WHOLE weectl call: the failure mode we care about is a 5xx
# during download, before weectl has touched /opt/weewx-data (see the
# successful-install log lines — download precedes any state change).
# A later-stage failure (partial extract or install) will still bail
# after MAX_ATTEMPTS, which is what current behavior does after 1.
MAX_ATTEMPTS=4
INITIAL_SLEEP=2

install_one() {
  local url="$1"
  local attempt=1
  local sleep_s="${INITIAL_SLEEP}"
  while true; do
    if weectl extension install "${url}" \
      --config /opt/weewx-data/weewx.conf \
      --yes; then
      return 0
    fi
    if [ "${attempt}" -ge "${MAX_ATTEMPTS}" ]; then
      echo "FAILED after ${MAX_ATTEMPTS} attempts: ${url}" >&2
      return 1
    fi
    echo "attempt ${attempt} failed; retrying in ${sleep_s}s..." >&2
    sleep "${sleep_s}"
    attempt=$((attempt + 1))
    sleep_s=$((sleep_s * 2))
  done
}

# Read non-comment, non-blank lines. Using a while-read loop (not `for url
# in $(...)`) so URLs with shell-special characters are safe.
while IFS= read -r url; do
  case "${url}" in
    '' | '#'*) continue ;;
  esac
  echo
  echo "=== Installing: ${url} ==="
  install_one "${url}"
done <"${LIST}"
