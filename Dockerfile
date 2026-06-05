ARG BUILD_FROM=ghcr.io/home-assistant/base-debian:trixie

# ---------------------------------------------------------------------------
# Single-stage build. apt provides only OS-level bits (python3, libusb, and the
# mariadb/nginx/ssh/rsync runtime tools); every Python library — weewx, felddy's
# weewx_ha, and their dependencies (Pillow, Cheetah, pyephem, pyserial, pyusb,
# PyMySQL, paho, pydantic) — is installed by uv as wheels. Nothing compiles, so
# there are no gcc/-dev headers and no separate builder stage; uv is bind-mounted
# for the build only and is never shipped in the image.
# ---------------------------------------------------------------------------
FROM ${BUILD_FROM} AS addon

LABEL \
    org.opencontainers.image.title="WeeWX" \
    org.opencontainers.image.description="WeeWX weather station server with bundled extensions, MQTT Home Assistant discovery, and nginx ingress web reports. Configured by editing weewx.conf." \
    org.opencontainers.image.source="https://github.com/bakerkj/ha-weewx" \
    org.opencontainers.image.licenses="MIT"

# Only OS-level bits come from apt: python3 (the interpreter uv builds the venv
# on), libusb (the C library pyusb binds at runtime for USB drivers), and the
# runtime tools — mariadb-client-core (the `mariadb` CLI for DB setup; the full
# mariadb-client metapackage drags in perl, ~120 MB, and weewx talks to the DB
# via the library anyway), nginx (ingress) plus its brotli filter module
# (better-than-gzip compression of the report text payload; zstd is not
# packaged for nginx in trixie) and njs (libnginx-mod-http-js, used for the
# per-request NOAA Cache-Control filter), openssh-client / rsync (report
# uploads), patch (build-time extension patching). Every Python library is
# installed by uv below, as wheels — nothing compiles.
RUN apt-get update && apt-get install -y --no-install-recommends \
    bash=5.2.37-2+b9 \
    curl=8.14.1-2+deb13u3 \
    libnginx-mod-http-brotli-filter=1.0.0~rc-6 \
    libnginx-mod-http-js=0.8.9-1 \
    libusb-1.0-0=2:1.0.28-1 \
    mariadb-client-core=1:11.8.6-0+deb13u1 \
    nginx-light=1.26.3-3+deb13u5 \
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
# python3 and installs the locked deps from uv.lock (weewx + felddy + Pillow/
# pydantic/Cheetah/pyephem/pyserial/pyusb/PyMySQL/paho) as wheels — nothing
# compiles. pyproject.toml/uv.lock are bind-mounted, so they add no image layer.
RUN --mount=from=ghcr.io/astral-sh/uv:0.11.19,source=/uv,target=/usr/local/bin/uv \
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
# /config/weewx.conf only. See build/seed_build_conf.py for full rationale
# (incl. why /config must exist at build time and why root logger is WARNING).
RUN --mount=type=bind,source=build/seed_build_conf.py,target=/build/seed_build_conf.py \
    python3 /build/seed_build_conf.py

# ---------------------------------------------------------------------------
# Install extensions (pinned versions).
# Failures are warned but do NOT abort the build — a broken extension should
# not prevent the image from being usable.
# ---------------------------------------------------------------------------
RUN for url in \
      "https://github.com/matthewwall/weewx-emoncms/archive/7c04113.zip" \
      "https://github.com/matthewwall/weewx-exfoliation/archive/9f77f4d.zip" \
      "https://github.com/chaunceygardiner/weewx-forecast/archive/v4.1.zip" \
      "https://github.com/brewster76/fuzzy-archer/archive/v4.4.zip" \
      "https://github.com/bellrichm/WeeWX-MQTTSubscribe/archive/v3.1.0.zip" \
      "https://github.com/sbsrouteur/weewx-opensensemap/archive/V0.3.zip" \
      "https://github.com/matthewwall/weewx-owm/archive/297dd97.zip" \
      "https://github.com/previmeteo/weewx-previmeteo/archive/v0.1.zip" \
      "https://github.com/bakerkj/weewx-purpleair/archive/v0.9.zip" \
      "https://github.com/chaunceygardiner/weewx-rain24h/archive/a37f6bb.zip" \
      "https://github.com/matthewwall/weewx-thingspeak/archive/a1ffa8e.zip" \
      "https://github.com/matthewwall/weewx-wcloud/archive/83ee792.zip" \
      "https://github.com/matthewwall/weewx-wetter/archive/50a7f68.zip" \
      "https://github.com/matthewwall/weewx-windfinder/archive/07ccbc3.zip" \
      "https://github.com/claudobahn/weewx-windguru/archive/c0a9b04.zip" \
      "https://github.com/matthewwall/weewx-windy/archive/0.3.zip" \
      "https://github.com/tkeffer/weewx-xaggs/archive/d361456.zip" \
    ; do \
        echo ""; \
        echo "=== Installing: $url ==="; \
        weectl extension install "$url" \
            --config /opt/weewx-data/weewx.conf \
            --yes \
        || echo "WARNING: weectl extension install failed for $(basename $url) — skipping"; \
    done

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
ADD https://raw.githubusercontent.com/weewx/weewx/v5.3.1/src/weewx_data/examples/xstats/bin/user/xstats.py \
    /opt/weewx-data/bin/user/xstats.py

# ---------------------------------------------------------------------------
# Apply patches. Each .patch is a unified diff applied with `patch -p1` in
# lexical order; a single failure aborts the build. See patches/README.md.
#   patches/*.patch       -> /opt/weewx-data (extensions installed there via
#                            weectl); paths relative to /opt/weewx-data/.
#   patches/weewx/*.patch -> weewx core in the /opt/weewx venv's site-packages
#                            (weedb, weewx, ...); paths relative to that dir.
#   patches/venv/*.patch  -> the weewx_ha pip package in the venv (felddy is
#                            pip-installed, not under /opt/weewx-data); paths
#                            relative to the weewx_ha package directory.
# ---------------------------------------------------------------------------
COPY patches/ /tmp/patches/
RUN set -eu && \
    for p in /tmp/patches/*.patch; do \
        echo "Applying (data) $(basename "$p")"; \
        patch --batch -d /opt/weewx-data -p1 < "$p"; \
    done && \
    WEEWX_LIB_DIR="$(python3 -c 'import os, weedb; print(os.path.dirname(os.path.dirname(weedb.__file__)))')" && \
    for p in /tmp/patches/weewx/*.patch; do \
        [ -e "$p" ] || continue; \
        echo "Applying (weewx) $(basename "$p") -> $WEEWX_LIB_DIR"; \
        patch --batch -d "$WEEWX_LIB_DIR" -p1 < "$p"; \
    done && \
    WEEWX_HA_DIR="$(python3 -c 'import os, weewx_ha; print(os.path.dirname(weewx_ha.__file__))')" && \
    for p in /tmp/patches/venv/*.patch; do \
        [ -e "$p" ] || continue; \
        echo "Applying (venv) $(basename "$p") -> $WEEWX_HA_DIR"; \
        patch --batch -d "$WEEWX_HA_DIR" -p1 < "$p"; \
    done && \
    rm -rf /tmp/patches

# Drop the build-time stub conf and the build-time log it produced — runtime
# uses /config/weewx.conf only, and /config is the addon_config mount.
RUN rm -f /opt/weewx-data/weewx.conf && rm -rf /config

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

# Build-time self-checks live in Dockerfile.test — kept out of this file
# so the HA builder / `docker build` produce the add-on image with no
# test concerns. Run with:
#   docker buildx build -t ha-weewx . && \
#       docker buildx build --build-arg BASE_IMAGE=ha-weewx \
#           -f Dockerfile.test .
