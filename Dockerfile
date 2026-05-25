ARG BUILD_FROM=ghcr.io/home-assistant/base-debian:trixie

# ---------------------------------------------------------------------------
# Stage 1 — builder: install uv, compile mysqlclient + any sdists into a
# self-contained venv at /opt/weewx. Build-only deps (gcc, -dev headers) live
# only in this layer and never reach the final image.
# ---------------------------------------------------------------------------
FROM ${BUILD_FROM} AS builder

COPY --from=ghcr.io/astral-sh/uv:0.11.16 /uv /uvx /usr/local/bin/

RUN apt-get update && apt-get install -y --no-install-recommends \
    default-libmysqlclient-dev=1.1.1 \
    gcc=4:14.2.0-1 \
    git=1:2.47.3-0+deb13u1 \
    pkg-config=1.8.1-4 \
    python3=3.13.5-1 \
    python3-dev=3.13.5-1 \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY pyproject.toml uv.lock .python-version ./
ENV UV_PROJECT_ENVIRONMENT=/opt/weewx \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1
RUN uv sync --frozen --no-dev --no-install-project

# ---------------------------------------------------------------------------
# Stage 2 — runtime: minimal base + the prebuilt venv.
#   python3, libmariadb3: interpreter + dynamic dep of compiled mysqlclient
#   mariadb-client, bash, curl, git: db creation + weectl extension installs
# uv is retained because run.sh uses `uv pip install` to add user-supplied
# extras at startup.
# ---------------------------------------------------------------------------
FROM ${BUILD_FROM} AS addon

LABEL \
    org.opencontainers.image.title="WeeWX" \
    org.opencontainers.image.description="WeeWX weather station server with bundled extensions, MQTT Home Assistant discovery, and nginx ingress web reports. Configured by editing weewx.conf." \
    org.opencontainers.image.source="https://github.com/bakerkj/ha-weewx" \
    org.opencontainers.image.licenses="MIT"

COPY --from=ghcr.io/astral-sh/uv:0.11.16 /uv /uvx /usr/local/bin/

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash=5.2.37-2+b9 \
    curl=8.14.1-2+deb13u3 \
    git=1:2.47.3-0+deb13u1 \
    libmariadb3=1:11.8.6-0+deb13u1 \
    mariadb-client=1:11.8.6-0+deb13u1 \
    nginx-light=1.26.3-3+deb13u5 \
    openssh-client=1:10.0p1-7+deb13u4 \
    patch=2.8-2 \
    python3=3.13.5-1 \
    rsync=3.4.1+ds1-5+deb13u3 \
 && rm -rf /var/lib/apt/lists/*

# Replace the distro nginx config with our ingress-port server. The user
# never edits this — they put files in /config/www/ and nginx serves them.
COPY nginx.conf /etc/nginx/nginx.conf

COPY --from=builder /opt/weewx /opt/weewx
ENV PATH="/opt/weewx/bin:$PATH" \
    VIRTUAL_ENV="/opt/weewx"

# ---------------------------------------------------------------------------
# Prepare weewx data directory
# Extensions are installed here so WeeWX can find their user modules and skins
# at runtime via WEEWX_ROOT = /opt/weewx-data.
# ---------------------------------------------------------------------------
RUN mkdir -p /opt/weewx-data/user /opt/weewx-data/skins

# Copy WeeWX's stock skins (Seasons, Standard, Mobile, …) out of the package
# data dir into WEEWX_ROOT/skins. The default template enables SeasonsReport,
# and weewxd resolves SKIN_ROOT relative to WEEWX_ROOT — without this, a default
# install crashes with "skins/Seasons: No such file or directory". Existing
# (extension-installed) skins are never overwritten.
RUN python3 - <<'PYEOF'
import os, shutil, weewx

site_packages = os.path.dirname(os.path.dirname(weewx.__file__))
src = os.path.join(site_packages, "weewx_data", "skins")
dst = "/opt/weewx-data/skins"
for name in sorted(os.listdir(src)):
    s, d = os.path.join(src, name), os.path.join(dst, name)
    if os.path.isdir(s) and not os.path.exists(d):
        shutil.copytree(s, d)
        print(f"Copied stock skin {name} -> {d}")

# WeeWX's stock user-package stubs (extensions.py + __init__.py). We build
# bin/user with `weectl extension install` rather than `weectl station create`,
# so these are never placed and weewxd logs "Cannot load user extensions: No
# module named 'user.extensions'" at every startup. Copy them in without
# clobbering anything an extension installs alongside.
user_src = os.path.join(site_packages, "weewx_data", "bin", "user")
user_dst = "/opt/weewx-data/bin/user"
os.makedirs(user_dst, exist_ok=True)
for name in ("extensions.py", "__init__.py"):
    s, d = os.path.join(user_src, name), os.path.join(user_dst, name)
    if os.path.exists(s) and not os.path.exists(d):
        shutil.copy2(s, d)
        print(f"Copied stock user stub {name} -> {d}")
PYEOF

# Build-time stub weewx.conf so weectl extension install knows where to drop
# user modules (WEEWX_ROOT/bin/user/) and skins (WEEWX_ROOT/skins/). Removed
# at the end of the build — runtime uses /config/weewx.conf only.
RUN python3 - <<'PYEOF'
import configobj

c = configobj.ConfigObj()
c["WEEWX_ROOT"] = "/opt/weewx-data"
c["Station"] = {
    "station_type": "Simulator",
    "location": "Build",
    "latitude": "0",
    "longitude": "0",
    "altitude": "0, meter",
}
c["Simulator"] = {"driver": "weewx.drivers.simulator", "mode": "simulator"}
c["StdRESTful"] = {"StationRegistry": {"register_this_station": "False"}}
c["StdReport"] = {
    "HTML_ROOT": "/tmp/html",
    "SKIN_ROOT": "skins",
    "data_binding": "wx_binding",
}
c["StdConvert"] = {"target_unit": "METRICWX"}
c["StdCalibrate"] = {"Corrections": {}}
c["StdQC"] = {"MinMax": {}}
c["StdArchive"] = {
    "archive_interval": "300",
    "archive_delay": "15",
    "no_catchup": "False",
    "data_binding": "wx_binding",
}
c["DataBindings"] = {
    "wx_binding": {
        "database": "archive_sqlite",
        "table_name": "archive",
        "manager": "weewx.manager.DaySummaryManager",
        "schema": "schemas.wview_extended.schema",
    }
}
c["Databases"] = {
    "archive_sqlite": {
        "database_name": "/tmp/weewx-build.sdb",
        "driver": "weedb.sqlite",
    }
}
c["Engine"] = {
    "Services": {
        "prep_services": "weewx.engine.StdTimeSynch",
        "data_services": "",
        "process_services": (
            "weewx.engine.StdConvert, weewx.engine.StdCalibrate, "
            "weewx.engine.StdQC, weewx.wxservices.StdWXCalculate"
        ),
        "xtype_services": (
            "weewx.wxxtypes.StdWXXTypes, weewx.wxxtypes.StdPressureCooker, "
            "weewx.wxxtypes.StdRainRater, weewx.wxxtypes.StdDelta"
        ),
        "archive_services": "weewx.engine.StdArchive",
        "restful_services": "weewx.restx.StdStationRegistry",
        "report_services": (
            "weewx.engine.StdPrint, weewx.engine.StdReport, weewx_ha.Controller"
        ),
    }
}
c.filename = "/opt/weewx-data/weewx.conf"
c.write()
print("Generated build-time weewx.conf")
PYEOF

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
      "https://github.com/matthewwall/weewx-thingspeak/archive/a1ffa8e.zip" \
      "https://github.com/matthewwall/weewx-wcloud/archive/83ee792.zip" \
      "https://github.com/matthewwall/weewx-wetter/archive/50a7f68.zip" \
      "https://github.com/matthewwall/weewx-windfinder/archive/07ccbc3.zip" \
      "https://github.com/claudobahn/weewx-windguru/archive/c0a9b04.zip" \
      "https://github.com/matthewwall/weewx-windy/archive/0.3.zip" \
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
# in Python 3.12) and old WeeWX 3/4 ExtensionInstaller API.
# Files: bin/user/rtgd.py + skins/RealtimeGauges/
# ---------------------------------------------------------------------------
RUN python3 - <<'PYEOF'
import io, os, urllib.request, zipfile

URL    = "https://github.com/hoetzgit/weewx-realtime_gauge-data/archive/v0.6.0.zip"
PREFIX = "weewx-realtime_gauge-data-0.6.0/"
print(f"Manually installing realtime-gauge-data from {URL}")

with urllib.request.urlopen(URL) as r:
    data = r.read()

with zipfile.ZipFile(io.BytesIO(data)) as z:
    for name in z.namelist():
        if name == PREFIX + "bin/user/rtgd.py":
            dest = "/opt/weewx-data/bin/user/rtgd.py"
            with open(dest, "wb") as f:
                f.write(z.read(name))
            print(f"  Copied {name} -> {dest}")
        elif name.startswith(PREFIX + "skins/RealtimeGauges/") and not name.endswith("/"):
            rel  = name[len(PREFIX + "skins/RealtimeGauges/"):]
            dest = os.path.join("/opt/weewx-data/skins/RealtimeGauges", rel)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with open(dest, "wb") as f:
                f.write(z.read(name))
            print(f"  Copied {name} -> {dest}")
PYEOF

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
#   patches/*.patch      -> /opt/weewx-data (extensions installed there via
#                           weectl); paths relative to /opt/weewx-data/.
#   patches/venv/*.patch -> the weewx_ha pip package in the venv (felddy is
#                           pip-installed, not under /opt/weewx-data); paths
#                           relative to the weewx_ha package directory.
# ---------------------------------------------------------------------------
COPY patches/ /tmp/patches/
RUN set -eu && \
    for p in /tmp/patches/*.patch; do \
        echo "Applying (data) $(basename "$p")"; \
        patch --batch -d /opt/weewx-data -p1 < "$p"; \
    done && \
    WEEWX_HA_DIR="$(python3 -c 'import os, weewx_ha; print(os.path.dirname(weewx_ha.__file__))')" && \
    for p in /tmp/patches/venv/*.patch; do \
        [ -e "$p" ] || continue; \
        echo "Applying (venv) $(basename "$p") -> $WEEWX_HA_DIR"; \
        patch --batch -d "$WEEWX_HA_DIR" -p1 < "$p"; \
    done && \
    rm -rf /tmp/patches

# Drop the build-time stub conf — runtime uses /config/weewx.conf only.
RUN rm /opt/weewx-data/weewx.conf

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

# ---------------------------------------------------------------------------
# Self-contained build-time checks. Run with:
#   docker buildx build --target test --build-arg BUILD_FROM=<base> .
# No external services — validates the image was assembled correctly (binary
# runs, venv + user extensions import, patches applied, stock skins copied,
# weewx-mqtt removed). NOT on the default build path: BuildKit only builds the
# final stage's dependencies, so the HA builder and `docker build` produce the
# add-on image (the trailing `FROM addon`) without this layer.
# ---------------------------------------------------------------------------
FROM addon AS test
RUN set -eu; \
    weewxd --version; \
    python3 -c "import weewx_ha, paho.mqtt.client, pydantic"; \
    PYTHONPATH=/opt/weewx-data/bin python3 -c "import user.extensions, user.log_to_file, user.forecast, user.xstats"; \
    grep -qF '"state_class"' /opt/weewx/lib/python3.13/site-packages/weewx_ha/config_publisher.py; \
    grep -qF 'weewx.restx.get_site_dict' /opt/weewx-data/bin/user/previmeteo.py; \
    grep -qF 'AbortedPost("skip_upload")' /opt/weewx-data/bin/user/emoncms.py; \
    test -d /opt/weewx-data/skins/Seasons; \
    test ! -f /opt/weewx-data/bin/user/mqtt.py; \
    echo "build-time self-checks passed"

# Final stage = the add-on image. Keeps `test` off the default build path so the
# HA builder / `docker build` produce the add-on image, not the test layer.
FROM addon
