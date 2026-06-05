# Copyright (c) 2026 Kenneth Baker <bakerkj@umich.edu>
# All rights reserved.

"""MQTT e2e — asserts the MQTT publisher's (by felddy) HA discovery
surface against the live addon image (SQLite-backed via
test/mqtt/weewx.conf, mosquitto sidecar).

All tests share one session-scoped MQTT subscriber that subscribes to
`homeassistant/#` + `weather/#` and accumulates messages over the session.
The subscriber publishes the HA birth message once, then waits up to ~20 s
for the archive-only signal (`weather/windrun`) to arrive — which means
every assertion lives off the same accumulated dict instead of paying its
own settle-wait. Replaces the prior per-test `_collect(settle=N)` pattern
that summed to ~30 s of waiting across 6 tests.
"""

import json
import os
import time

import paho.mqtt.client as mqtt
import pytest

MQTT_HOST = os.environ.get("MQTT_HOST", "mosquitto")
MQTT_PORT = int(os.environ.get("MQTT_PORT", "1883"))

# Maximum time to wait for the archive-only field (windrun) to appear on
# the broker. test/mqtt/weewx.conf uses archive_interval=5 s +
# archive_delay=3 s, so the first archive can fire ~13 s after weewxd
# init; on a cold runner (esp. aarch64) weewxd init itself is 5-10 s, so
# the budget needs headroom over the naive 1-cycle math.
ARCHIVE_DEADLINE = 40.0


@pytest.fixture(scope="session")
def mqtt_messages() -> dict[str, str]:
    """One-shot subscriber over the whole session.

    Subscribes to ``homeassistant/#`` and ``weather/#``, publishes the HA
    birth message (which makes the MQTT publisher republish all
    non-retained discovery configs), then blocks until either
    ``weather/windrun`` arrives (the archive-only signal that everything
    has had its chance) or the deadline lapses. Returns the accumulated
    {topic: payload} dict.
    """
    seen: dict[str, str] = {}

    def on_connect(client, userdata, flags, reason_code, properties):
        client.subscribe([("homeassistant/#", 0), ("weather/#", 0)])

    def on_message(client, userdata, msg):
        # First message wins — discovery + state topics never change shape
        # mid-session, and retained-availability is delivered immediately
        # on subscribe.
        seen.setdefault(msg.topic, msg.payload.decode(errors="replace"))

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_HOST, MQTT_PORT, 30)
    client.loop_start()
    # Let on_connect run + subscriptions settle before we publish birth.
    time.sleep(1.0)
    # The MQTT publisher (by felddy) publishes discovery configs
    # non-retained, so without the birth message we'd miss them
    # entirely. The status broadcast also triggers the publisher to
    # (re)publish availability.
    client.publish("homeassistant/status", "online")
    deadline = time.monotonic() + ARCHIVE_DEADLINE
    settled = False
    while time.monotonic() < deadline:
        if "weather/windrun" in seen:
            settled = True
            break
        time.sleep(0.5)
    client.loop_stop()
    client.disconnect()
    if not settled:
        # The settle signal didn't arrive in time. Returning a partial
        # dict would let every test except `test_archive_only_windrun_*`
        # pass, hiding the real problem (weewxd slow, archive cycle not
        # firing, MQTT misrouted) behind one misleading failure. Fail
        # the whole session here instead.
        pytest.fail(
            f"setup: weather/windrun never arrived within {ARCHIVE_DEADLINE}s "
            f"({len(seen)} topics seen); most likely cause is slow weewxd "
            f"startup pushing the first archive cycle past the deadline — "
            f"check archive_interval + archive_delay in test/mqtt/weewx.conf "
            f"and weewxd boot time before suspecting MQTT/weewx_ha."
        )
    return seen


# --- discovery + state_class -------------------------------------------


def test_discovery_configs_published(mqtt_messages):
    configs = {t: p for t, p in mqtt_messages.items() if t.endswith("/config")}
    assert len(configs) >= 1, "no HA discovery config topics published"


def test_outTemp_discovery_has_state_class_measurement(mqtt_messages):
    out = next(
        (p for t, p in mqtt_messages.items() if t.endswith("/outTemp/config")),
        None,
    )
    assert out is not None, "no outTemp discovery config"
    cfg = json.loads(out)
    assert cfg.get("state_class") == "measurement", cfg


def test_non_measurement_keys_omit_state_class(mqtt_messages):
    """Battery/enum/timestamp keys must NOT carry a state_class — that's
    the contract patches/venv/0001 (MQTT publisher state_class) enforces."""
    bad = []
    for t, p in mqtt_messages.items():
        if not t.endswith("/config"):
            continue
        if t.endswith("BatteryStatus/config") or t.endswith(
            ("/usUnits/config", "/dateTime/config")
        ):
            cfg = json.loads(p)
            if "state_class" in cfg:
                bad.append((t, cfg.get("state_class")))
    assert not bad, f"keys leaked state_class: {bad}"


# --- availability + xaggs anchor ---------------------------------------


def test_availability_retained(mqtt_messages):
    """The MQTT publisher publishes ``weather/status=online`` retained on connect."""
    assert mqtt_messages.get("weather/status") == "online", mqtt_messages.get(
        "weather/status"
    )


def test_user_xaggs_module_loaded_clean(mqtt_messages):
    """If user.xaggs.XAggsService failed to load at weewx engine start,
    weewx would exit non-zero, its container healthcheck never goes
    healthy, and pytest never runs. Reaching this assertion means xaggs
    loaded cleanly. The `weather/status=online` check is the anchor."""
    assert mqtt_messages.get("weather/status") == "online"


# --- rain24h: discovery payload + state ---------------------------------


def test_rain24h_state_published(mqtt_messages):
    """weewx-rain24h service injects ``rain24h`` into every loop packet,
    so the MQTT publisher (by felddy) publishes the state topic with a
    parseable float."""
    val = mqtt_messages.get("weather/rain24h")
    assert val is not None, (
        "weather/rain24h never published — weewx-rain24h service not "
        "running (extension missing, not in data_services, or [Rain24h] "
        "disabled)"
    )
    try:
        float(val)
    except (TypeError, ValueError):
        pytest.fail(f"weather/rain24h published unparsable value: {val!r}")


def test_rain24h_discovery_metadata(mqtt_messages):
    """patches/venv/0005 (MQTT publisher rain24h KEY_CONFIG): discovery payload
    carries the right device_class, name, and unit_of_measurement."""
    cfg_topic = "homeassistant/sensor/weewx/rain24h/config"
    raw = mqtt_messages.get(cfg_topic)
    assert raw is not None, (
        "no rain24h discovery config — patches/venv/0005 (KEY_CONFIG entry) "
        "likely not applied, or the MQTT publisher never saw rain24h in a packet"
    )
    cfg = json.loads(raw)
    assert cfg.get("device_class") == "precipitation", cfg
    assert cfg.get("name") == "24-Hour Rainfall", cfg
    # METRICWX in [HomeAssistant] maps group_rain to 'mm'.
    assert cfg.get("unit_of_measurement") == "mm", cfg


# --- archive-only field reaches MQTT (patches/venv/0004) ----------------


def test_archive_only_windrun_published(mqtt_messages):
    """patches/venv/0004 binds weewx_ha.Controller to NEW_ARCHIVE_RECORD
    so archive-only fields (windrun is computed by StdWXXTypes only on
    archive records, not loop packets) actually reach the broker.
    Without the patch, weather/windrun is never published and the HA
    entity stays unavailable."""
    val = mqtt_messages.get("weather/windrun")
    assert val is not None, (
        "weather/windrun never published — bind-archive patch likely "
        "missing (the MQTT publisher is processing only loop packets, not archive "
        "records)"
    )
    try:
        float(val)
    except (TypeError, ValueError):
        pytest.fail(f"weather/windrun published unparsable value: {val!r}")
