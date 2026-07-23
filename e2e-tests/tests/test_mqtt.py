# Copyright (c) 2026 Kenneth Baker <bakerkj@umich.edu>
# All rights reserved.

"""MQTT e2e — asserts the MQTT publisher's (by felddy) HA discovery
surface against the live addon image (SQLite-backed via
e2e-tests/configs/mqtt/weewx.conf, mosquitto sidecar).

All tests share one session-scoped MQTT subscriber that subscribes to
`homeassistant/#` + `weather/#` and accumulates messages over the session.
The subscriber gates the HA birth publish on retained `weather/status`,
retries it every 2 s until at least one discovery config lands, then
waits up to ARCHIVE_DEADLINE for the archive-only signal
(`weather/windrun`) — which means every assertion lives off the same
accumulated dict instead of paying its own settle-wait. Replaces the
prior per-test `_collect(settle=N)` pattern that summed to ~30 s of
waiting across 6 tests.
"""

import json
import os
import time

import paho.mqtt.client as mqtt
import pytest

MQTT_HOST = os.environ.get("MQTT_HOST", "mosquitto")
MQTT_PORT = int(os.environ.get("MQTT_PORT", "1883"))

# Maximum time to wait for the archive-only field (windrun) to appear on
# the broker. e2e-tests/configs/mqtt/weewx.conf uses archive_interval=5 s +
# archive_delay=3 s, so the first archive can fire ~13 s after weewxd
# init; on a cold runner (esp. aarch64) weewxd init itself is 5-10 s, so
# the budget needs headroom over the naive 1-cycle math.
ARCHIVE_DEADLINE = 40.0


@pytest.fixture(scope="session")
def mqtt_messages() -> dict[str, str]:
    """One-shot subscriber over the whole session.

    Subscribes to ``homeassistant/#`` and ``weather/#``, republishes the
    HA birth message on a 2 s cadence until at least one discovery config
    lands, then blocks until ``weather/windrun`` (the archive-only signal
    that everything has had its chance) also arrives or the deadline
    lapses. Returns the accumulated {topic: payload} dict.

    Two races the retry+prereq loop closes:

    * The felddy publisher publishes its initial discovery configs
      non-retained, before we subscribe — so those first copies are lost.
      Our birth publish makes the publisher republish them, but only if
      the publisher has already subscribed to ``homeassistant/status``.
      A single fire-and-forget birth loses that race on a slow runner.
    * Retained ``weather/status=online`` is the only signal that the
      publisher has connected to the broker at all; without gating birth
      on it we'd start retrying into a broker with no subscriber.
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

    deadline = time.monotonic() + ARCHIVE_DEADLINE
    next_birth = 0.0
    have_configs = False
    have_archive = False
    while time.monotonic() < deadline:
        # Snapshot keys before iterating: on_message runs on the paho
        # network thread and mutates `seen` via setdefault. Iterating a
        # dict while another thread grows it raises RuntimeError, and
        # right after birth is exactly when felddy bursts out dozens of
        # discovery configs.
        have_configs = any(t.endswith("/config") for t in list(seen))
        have_archive = "weather/windrun" in seen
        if have_configs and have_archive:
            break
        publisher_ready = seen.get("weather/status") == "online"
        now = time.monotonic()
        if publisher_ready and not have_configs and now >= next_birth:
            client.publish("homeassistant/status", "online")
            next_birth = now + 2.0
        time.sleep(0.5)

    client.loop_stop()
    client.disconnect()

    if not (have_configs and have_archive):
        # Returning a partial dict would let unrelated tests pass and
        # hide the real cause (weewxd slow, publisher never connected,
        # birth-loop lost) behind one misleading failure. Fail loudly.
        cfg_count = sum(1 for t in seen if t.endswith("/config"))
        pytest.fail(
            f"setup: MQTT session did not settle within {ARCHIVE_DEADLINE}s. "
            f"weather/status={seen.get('weather/status')!r}, "
            f"discovery configs={cfg_count}, "
            f"weather/windrun={'yes' if have_archive else 'no'} "
            f"({len(seen)} topics total). Check weewxd boot time and that "
            f"the felddy publisher is connecting to mosquitto before "
            f"suspecting MQTT/weewx_ha."
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
