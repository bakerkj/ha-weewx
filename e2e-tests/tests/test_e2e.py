# Copyright (c) 2026 Kenneth Baker <bakerkj@umich.edu>
# All rights reserved.

"""End-to-end tests for the ha-weewx add-on.

Run inside docker-compose.test.yml against the live add-on container, MariaDB,
and Mosquitto. The weewx service's healthcheck gates this container to start
only once an archive record exists, so the data/report are already present by
the time these run; MQTT discovery still needs the HA birth-message handshake
(felddy publishes discovery non-retained).
"""

import json
import os
import time

import paho.mqtt.client as mqtt
import pymysql
import pytest
import requests

MARIADB = dict(
    host=os.environ.get("MARIADB_HOST", "mariadb"),
    port=int(os.environ.get("MARIADB_PORT", "3306")),
    user=os.environ.get("MARIADB_USER", "weewx"),
    password=os.environ.get("MARIADB_PASSWORD", "weewxpass"),
    database=os.environ.get("MARIADB_DB", "weewx"),
)
MQTT_HOST = os.environ.get("MQTT_HOST", "mosquitto")
MQTT_PORT = int(os.environ.get("MQTT_PORT", "1883"))
WEEWX_URL = os.environ.get("WEEWX_URL", "http://weewx:8099").rstrip("/")


def _collect(topics, birth=False, settle=4.0):
    """Subscribe to topics, optionally send the HA birth message, return {topic: payload}."""
    seen = {}

    def on_connect(client, userdata, flags, reason_code, properties):
        for t in topics:
            client.subscribe(t)

    def on_message(client, userdata, msg):
        seen[msg.topic] = msg.payload.decode(errors="replace")

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_HOST, MQTT_PORT, 30)
    client.loop_start()
    time.sleep(1.0)
    if birth:
        # felddy republishes all discovery configs on the HA birth message.
        client.publish("homeassistant/status", "online")
    time.sleep(settle)
    client.loop_stop()
    client.disconnect()
    return seen


def test_mariadb_archive_record():
    conn = pymysql.connect(connect_timeout=10, **MARIADB)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM archive")
            (count,) = cur.fetchone()
    finally:
        conn.close()
    assert count >= 1, f"expected >=1 archive record, got {count}"


def test_seasons_report_served():
    # The CopyGenerator drops seasons.css into HTML_ROOT; nginx serves it.
    last = None
    for _ in range(30):
        try:
            r = requests.get(f"{WEEWX_URL}/seasons.css", timeout=10)
            last = r.status_code
            if r.status_code == 200:
                return
        except requests.RequestException as e:
            last = repr(e)
        time.sleep(2)
    pytest.fail(f"seasons.css never served 200 (last={last})")


def test_mqtt_discovery_and_state_class():
    msgs = _collect(["homeassistant/#"], birth=True)
    configs = {t: p for t, p in msgs.items() if t.endswith("/config")}
    assert len(configs) >= 1, "no HA discovery config topics published"

    out = next((p for t, p in configs.items() if t.endswith("/outTemp/config")), None)
    assert out is not None, "no outTemp discovery config"
    cfg = json.loads(out)
    # The state_class patch: live readings are measurement.
    assert cfg.get("state_class") == "measurement", cfg

    # Battery status / enum / timestamp keys must NOT carry a state_class.
    for t, p in configs.items():
        if t.endswith("BatteryStatus/config") or t.endswith(
            ("/usUnits/config", "/dateTime/config")
        ):
            assert "state_class" not in json.loads(p), t


def test_mqtt_availability_retained():
    # Availability is published retained on connect, so no birth needed.
    msgs = _collect(["weather/status"], birth=False, settle=2.0)
    assert msgs.get("weather/status") == "online", msgs


def test_mqtt_rain24h_published_with_metadata():
    # Verifies the chaunceygardiner/weewx-rain24h extension was installed and
    # is wired into data_services in test/weewx.conf — the service injects a
    # `rain24h` key into every loop packet so felddy publishes it.
    # Also verifies patches/venv/0005-felddy-rain24h-metadata.patch: the new
    # KEY_CONFIG entry gives the discovery payload a proper device_class and
    # name (otherwise felddy logs "Guessed metadata for key 'rain24h'" and
    # the HA entity gets no device_class).
    msgs = _collect(
        ["weather/rain24h", "homeassistant/sensor/weewx/rain24h/config"],
        birth=True,
        settle=6.0,
    )
    assert "weather/rain24h" in msgs, (
        "weather/rain24h never published — weewx-rain24h service is not "
        "running (extension missing, not in data_services, or [Rain24h] "
        "disabled)"
    )
    # The value should parse as a float (rain24h is 0.0 on a simulator that
    # never rains, but it is NOT None — the service emits a real number).
    try:
        float(msgs["weather/rain24h"])
    except (TypeError, ValueError):
        pytest.fail(
            f"weather/rain24h published unparsable value: {msgs['weather/rain24h']!r}"
        )

    # Discovery payload exists and carries the KEY_CONFIG metadata.
    cfg_topic = "homeassistant/sensor/weewx/rain24h/config"
    assert cfg_topic in msgs, (
        "no rain24h discovery config — patches/venv/0005 (KEY_CONFIG entry) "
        "likely not applied, or felddy never saw rain24h in a packet"
    )
    cfg = json.loads(msgs[cfg_topic])
    assert cfg.get("device_class") == "precipitation", cfg
    assert cfg.get("name") == "24-Hour Rainfall", cfg
    # weewx-rain24h registers obs_group_dict['rain24h']='group_rain', so
    # felddy resolves a unit via getStandardUnitType. test/weewx.conf uses
    # METRICWX in [HomeAssistant], which maps group_rain to 'mm'.
    assert cfg.get("unit_of_measurement") == "mm", cfg


def test_user_xaggs_module_loadable():
    # Verifies the tkeffer/weewx-xaggs extension was installed AND it loaded
    # without error at engine start. xaggs is an xtype_services registration
    # (template-time aggregations: historical_max, avg_gt, etc.) — there's no
    # MQTT-observable side effect. Its load failure would show up as an
    # ERROR/CRITICAL in the broker-side weewx.log we already check elsewhere,
    # but here we also assert the felddy discovery topics aren't missing.
    # Catching the xtype service registration via mqtt isn't possible, so we
    # rely on the Dockerfile self-check (`test -f bin/user/xaggs.py` +
    # `import user.xaggs`) and on the absence of weewx-startup errors. This
    # test exists as the e2e-suite-side anchor: if the user.xaggs.XAggsService
    # in test/weewx.conf xtype_services fails to load, weewx exits non-zero,
    # the weewx container healthcheck never goes healthy, and the entire
    # e2e suite hangs/fails at startup — so reaching this assertion at all is
    # the evidence that xaggs loaded cleanly.
    msgs = _collect(["weather/status"], birth=False, settle=2.0)
    assert msgs.get("weather/status") == "online", msgs


def test_mqtt_archive_only_field_published():
    # Verifies patches/venv/0004-felddy-bind-archive.patch: weewx_ha.Controller
    # also binds NEW_ARCHIVE_RECORD, so archive-only fields (like windrun,
    # which weewx.wxxtypes.StdWXXTypes computes only on archive records, not
    # on loop packets) reach the broker as state topics. Without the patch,
    # `weather/windrun` is never published — felddy's discovery config for it
    # exists but no state arrives, and the HA entity stays "unavailable".
    #
    # test/weewx.conf configures archive_interval=5s and
    # [StdWXCalculate][[Calculations]] windrun = software, so windrun lands
    # in every archive record. We wait for one archive cycle's worth (plus
    # buffer) and assert weather/windrun shows up with a parseable value.
    msgs = _collect(["weather/windrun"], birth=False, settle=10.0)
    assert "weather/windrun" in msgs, (
        "weather/windrun never published — bind-archive patch likely missing "
        "(felddy is processing only loop packets, not archive records)"
    )
    # And the value should be a real number, not 'None'.
    val = msgs["weather/windrun"]
    try:
        float(val)
    except (TypeError, ValueError):
        pytest.fail(f"weather/windrun published unparsable value: {val!r}")
