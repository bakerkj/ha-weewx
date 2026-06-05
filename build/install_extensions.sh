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

# Read non-comment, non-blank lines. Using a while-read loop (not `for url
# in $(...)`) so URLs with shell-special characters are safe.
while IFS= read -r url; do
  case "${url}" in
    '' | '#'*) continue ;;
  esac
  echo
  echo "=== Installing: ${url} ==="
  weectl extension install "${url}" \
    --config /opt/weewx-data/weewx.conf \
    --yes
done <"${LIST}"
