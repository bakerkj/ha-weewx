ARG BUILD_FROM=ghcr.io/home-assistant/base-debian:trixie-2026.06.1@sha256:3256be70f2e53c1b259e45fdc938ef4ca709623eadbf9cbabd5ed99ef644188b

# ---------------------------------------------------------------------------
# rtldavis Go binary — RTL-SDR demodulator for Davis ISS. The Python
# rtldavis driver popen()s it when station_type = Rtldavis is selected.
# Built as a separate stage so the Go toolchain never ships in the
# final image. Pinned to upstream master since the project has no
# release tags and the protocol has been stable since 2020.
# Built on debian:trixie so every apt package in the build stage falls
# under the same debian_13/<pkg> Renovate manager that governs the
# runtime stage.
# ---------------------------------------------------------------------------
FROM debian:trixie-20260623 AS rtldavis-builder
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates=20250419 \
    gcc=4:14.2.0-1 \
    git=1:2.47.3-0+deb13u1 \
    golang-go=2:1.24~2 \
    libc6-dev=2.41-12+deb13u3 \
    librtlsdr-dev=2.0.2-2+b1 \
    libusb-1.0-0-dev=2:1.0.28-1 \
    pkg-config=1.8.1-4 \
 && rm -rf /var/lib/apt/lists/*
ARG RTLDAVIS_REF=b95d5d734e4666c90f3d7539d5e2acd9f80f7e43
ENV GOPATH=/go GO111MODULE=off
RUN git clone https://github.com/lheijst/rtldavis \
      "$GOPATH/src/github.com/lheijst/rtldavis"
WORKDIR /go/src/github.com/lheijst/rtldavis
RUN git checkout "$RTLDAVIS_REF" && git submodule update --init --recursive \
 && go build -trimpath -ldflags="-s -w" -o /out/rtldavis .

# ---------------------------------------------------------------------------
# Single-stage runtime image. apt provides only OS-level bits (python3,
# libusb, librtlsdr0, and the mariadb/nginx/ssh/rsync runtime tools); every
# Python library — weewx, the MQTT publisher (by felddy), and their
# dependencies (Pillow, Cheetah, pyephem, pyserial, pyusb, PyMySQL, paho,
# pydantic) — is installed by uv as wheels. Nothing compiles in this stage,
# so there are no gcc/-dev headers; uv is bind-mounted for the build only
# and is never shipped in the image.
# ---------------------------------------------------------------------------
FROM ${BUILD_FROM} AS addon

# HA Supervisor passes BUILD_VERSION=<config.json version> on installs; CI
# does the same in addon-build.yaml. Local builds (e2e, BUILD=1 in
# test-watchdog.sh) leave it at the default so they don't claim a real tag.
ARG BUILD_VERSION=dev
ENV HA_WEEWX_VERSION="${BUILD_VERSION}"

LABEL \
    org.opencontainers.image.title="WeeWX" \
    org.opencontainers.image.description="WeeWX weather station server with bundled extensions, MQTT Home Assistant discovery, and nginx ingress web reports. Configured by editing weewx.conf." \
    org.opencontainers.image.source="https://github.com/bakerkj/ha-weewx" \
    org.opencontainers.image.licenses="MIT" \
    org.opencontainers.image.version="${BUILD_VERSION}"

# Only OS-level bits come from apt: python3 (the interpreter uv builds the venv
# on), libusb (the C library pyusb binds at runtime for USB drivers), and the
# runtime tools — nginx (ingress) plus its brotli filter module (better-than-
# gzip compression of the report text payload; zstd is not packaged for nginx
# in trixie) and njs (libnginx-mod-http-js, used for the per-request NOAA
# Cache-Control filter), openssh-client / rsync (report uploads), patch
# (build-time extension patching). MariaDB access at runtime goes through
# PyMySQL (Python lib, installed by uv below), so no mariadb CLI is needed.
# Every Python library is installed by uv below, as wheels — nothing compiles.
RUN apt-get update && apt-get install -y --no-install-recommends \
    bash=5.2.37-2+b9 \
    curl=8.14.1-2+deb13u3 \
    libnginx-mod-http-brotli-filter=1.0.0~rc-6 \
    libnginx-mod-http-js=0.8.9-1 \
    librtlsdr0=2.0.2-2+b1 \
    libusb-1.0-0=2:1.0.28-1 \
    nginx-light=1.26.3-3+deb13u7 \
    openssh-client=1:10.0p1-7+deb13u4 \
    patch=2.8-2 \
    procps=2:4.0.4-9 \
    python3=3.13.5-1 \
    rsync=3.4.1+ds1-5+deb13u3 \
 && rm -rf /var/lib/apt/lists/*

# Replace the distro nginx config with our ingress-port server. The user
# never edits this — they put files in /config/www/ and nginx serves them.
COPY nginx.conf /etc/nginx/nginx.conf

ENV PATH="/opt/weewx/bin:$PATH" \
    VIRTUAL_ENV="/opt/weewx" \
    UV_PROJECT_ENVIRONMENT="/opt/weewx"
# uv is bind-mounted from its image for this layer only (never shipped in the
# final image). `uv sync --frozen` builds the venv at /opt/weewx on the system
# python3 and installs the locked deps from uv.lock (weewx + the MQTT
# publisher (by felddy) + Pillow/pydantic/Cheetah/pyephem/pyserial/pyusb/
# PyMySQL/paho) as wheels — nothing compiles. pyproject.toml/uv.lock are
# bind-mounted, so they add no image layer.
RUN --mount=from=ghcr.io/astral-sh/uv:0.11.26,source=/uv,target=/usr/local/bin/uv \
    --mount=type=bind,source=pyproject.toml,target=/build/pyproject.toml \
    --mount=type=bind,source=uv.lock,target=/build/uv.lock \
    --mount=type=bind,source=.python-version,target=/build/.python-version \
    uv sync --frozen --no-dev --no-install-project \
      --project /build --python /usr/bin/python3

# ---------------------------------------------------------------------------
# Prepare weewx data directory
# Extensions are installed here so WeeWX can find their user modules and skins
# at runtime via WEEWX_ROOT = /opt/weewx-data.
# ---------------------------------------------------------------------------
RUN mkdir -p /opt/weewx-data/user /opt/weewx-data/skins

# Seed stock skins (Seasons, Standard, Mobile, …) and stock user-package
# stubs (extensions.py, __init__.py) into WEEWX_ROOT. See build/seed_skins.py
# for the rationale and the existing-entry preservation contract.
RUN --mount=type=bind,source=build/seed_skins.py,target=/build/seed_skins.py \
    python3 /build/seed_skins.py

# Build-time stub weewx.conf so weectl extension install knows where to drop
# user modules and skins. Removed at the end of the build — runtime uses
# /config/weewx.conf only. See build/seed_build_conf.py for the rationale
# (why a [Logging] block is needed and why root logger is WARNING).
RUN --mount=type=bind,source=build/seed_build_conf.py,target=/build/seed_build_conf.py \
    python3 /build/seed_build_conf.py

# ---------------------------------------------------------------------------
# Install extensions listed in build/extensions.txt (pinned versions).
# build/install_extensions.sh iterates the list under `set -euo pipefail`,
# so the first `weectl extension install` that fails aborts the build —
# silent skips would let a broken or missing extension ship in the image
# (the in-image self-checks only assert presence of a subset).
# ---------------------------------------------------------------------------
RUN --mount=type=bind,source=build/extensions.txt,target=/build/extensions.txt \
    --mount=type=bind,source=build/install_extensions.sh,target=/build/install_extensions.sh \
    bash /build/install_extensions.sh

# ---------------------------------------------------------------------------
# realtime-gauge-data: manual install — install.py uses distutils (removed
# in Python 3.12) and old WeeWX 3/4 ExtensionInstaller API. The script
# unpacks bin/user/rtgd.py + skins/RealtimeGauges/ directly from the zip.
# ---------------------------------------------------------------------------
RUN --mount=type=bind,source=build/install_rtgd.py,target=/build/install_rtgd.py \
    python3 /build/install_rtgd.py

# ---------------------------------------------------------------------------
# xstats: extended-statistics search-list extension shipped with WeeWX as an
# example. Some skins reference user.xstats but it is not installed by
# default. Pull it from the upstream tag.
# ---------------------------------------------------------------------------
ADD https://raw.githubusercontent.com/weewx/weewx/v5.4.0/src/weewx_data/examples/xstats/bin/user/xstats.py \
    /opt/weewx-data/bin/user/xstats.py

# ---------------------------------------------------------------------------
# Apply patches. Each .patch is a unified diff applied with `patch -p1` in
# lexical order; a single failure aborts the build. See patches/README.md.
#   patches/extensions/*.patch -> /opt/weewx-data (bundled extensions installed
#                                 there via weectl); paths relative to
#                                 /opt/weewx-data/.
#   patches/weewx/*.patch      -> weewx core in the /opt/weewx venv's
#                                 site-packages (weedb, weewx, ...); paths
#                                 relative to that dir.
#   patches/venv/*.patch       -> the MQTT publisher (by felddy) pip package
#                                 in the venv (pip-installed, not under
#                                 /opt/weewx-data); paths relative to the
#                                 weewx_ha package dir.
# ---------------------------------------------------------------------------
RUN --mount=type=bind,source=patches,target=/build/patches \
    set -eu && \
    for p in /build/patches/extensions/*.patch; do \
        [ -e "$p" ] || continue; \
        echo "Applying (extensions) $(basename "$p")"; \
        patch --batch -d /opt/weewx-data -p1 < "$p"; \
    done && \
    WEEWX_LIB_DIR="$(python3 -c 'import os, weedb; print(os.path.dirname(os.path.dirname(weedb.__file__)))')" && \
    for p in /build/patches/weewx/*.patch; do \
        [ -e "$p" ] || continue; \
        echo "Applying (weewx) $(basename "$p") -> $WEEWX_LIB_DIR"; \
        patch --batch -d "$WEEWX_LIB_DIR" -p1 < "$p"; \
    done && \
    WEEWX_HA_DIR="$(python3 -c 'import os, weewx_ha; print(os.path.dirname(weewx_ha.__file__))')" && \
    for p in /build/patches/venv/*.patch; do \
        [ -e "$p" ] || continue; \
        echo "Applying (venv) $(basename "$p") -> $WEEWX_HA_DIR"; \
        patch --batch -d "$WEEWX_HA_DIR" -p1 < "$p"; \
    done

# Drop the build-time stub conf — runtime uses /config/weewx.conf (the
# addon_config mount). /config itself is not created at build time.
RUN rm -f /opt/weewx-data/weewx.conf

# ---------------------------------------------------------------------------
# rtldavis binary built in the rtldavis-builder stage above. The
# weewx-rtldavis driver (installed via build/extensions.txt) popen()s this
# path when station_type=Rtldavis in /config/weewx.conf.
# ---------------------------------------------------------------------------
COPY --from=rtldavis-builder /out/rtldavis /opt/rtldavis/bin/rtldavis

# ---------------------------------------------------------------------------
# Bundled extra extension: log_to_file (per-record CSV file writer, bakerkj).
# Custom skins are NOT baked in — they are user customizations supplied at
# runtime (e.g. under /config), not part of the generic add-on.
# ---------------------------------------------------------------------------
COPY extensions/log_to_file.py /opt/weewx-data/bin/user/log_to_file.py

# ---------------------------------------------------------------------------
# s6-overlay services + the bundled conf template
#
# Services (in /etc/s6-overlay/s6-rc.d/):
#   nginx-init  (oneshot) → mkdir, seed placeholder index.html, nginx -t
#   nginx       (longrun) → exec nginx -g "daemon off;"; depends on nginx-init
#   weewx-init  (oneshot) → seed weewx.conf from template, install runtime extras
#   weewxd      (longrun) → exec weewxd --config /config/weewx.conf;
#                           depends on weewx-init
#
# Both longruns are auto-restarted on crash by s6. CMD is the base image's
# default /init (s6 supervisor), so we don't override it here.
# ---------------------------------------------------------------------------
COPY rootfs/ /
