#!/usr/bin/env python3
# Copyright (c) 2026 Kenneth Baker <bakerkj@umich.edu>
# All rights reserved.

"""In-image behavioural checks for the 14 bundled-extension patches.

Runs inside the built addon image (invoked from ``build/check_image.sh``)
against the actual shipped code at ``/opt/weewx-data/bin/user/``. Each
patch has a dedicated ``check_<name>()`` function that imports the
patched module (``from user.<mod> import ...``) and exercises the
specific changed code path. ``PYTHONPATH=/opt/weewx-data/bin`` must be
set by the caller so ``import user.<mod>`` resolves to the on-disk
file the running addon actually uses.

Output format mirrors the ``check`` helper in ``check_image.sh``:
``PASS patch:<name>`` or ``FAIL patch:<name>: <reason>``. Exit 0 iff
every check passed.
"""

from __future__ import annotations

import importlib
import inspect
import pathlib
import subprocess
import sys
import textwrap
import traceback
from typing import Callable
from unittest.mock import Mock, patch


WEEWX_BIN = pathlib.Path("/opt/weewx-data/bin")


def _import(modname: str):
    """Import ``user.<modname>`` fresh so a check sees a clean module state."""
    sys.modules.pop(f"user.{modname}", None)
    return importlib.import_module(f"user.{modname}")


# ---------------------------------------------------------------------------
# 0001 — previmeteo Py3 queue shim
# ---------------------------------------------------------------------------
def check_0001_previmeteo_py3_queue_shim() -> None:
    previmeteo = _import("previmeteo")
    import queue as stdlib_queue

    assert previmeteo.Queue is stdlib_queue, (
        "patched previmeteo must alias the stdlib `queue` module under "
        "the `Queue` name; bare Py2 `import Queue` crashes Py3 weewxd"
    )
    q = previmeteo.Queue.Queue()
    q.put("x")
    assert q.get() == "x"


# ---------------------------------------------------------------------------
# 0002 — rtgd verbose thread traceback
# ---------------------------------------------------------------------------
def check_0002_rtgd_verbose_thread_traceback() -> None:
    rtgd = _import("rtgd")
    run_src = inspect.getsource(rtgd.RealtimeGaugeDataThread.run)
    loop_start = run_src.index("elif _package['type'] == 'loop':")
    loop_end = run_src.index("# if packets have backed up", loop_start)
    loop_block = run_src[loop_start:loop_end]

    assert (
        "weeutil.logger.log_traceback(log.critical, 'rtgdthread: **** ')" in loop_block
    ), (
        "loop-packet except block must call log_traceback with log.critical "
        "so a KeyError stack reaches production logs without a global "
        "logger-level bump"
    )
    assert (
        "weeutil.logger.log_traceback(log.debug, 'rtgdthread: **** ')" not in loop_block
    ), (
        "loop-packet except block must NOT log the traceback at debug; "
        "that was the bug — the stack stays hidden at production log levels"
    )

    # Wire the patched line to prove the logger method is the one we expect.
    captured: dict = {}

    def fake_log_traceback(level_func, prefix):
        captured["level"] = level_func
        captured["prefix"] = prefix

    real = rtgd.weeutil.logger.log_traceback
    rtgd.weeutil.logger.log_traceback = fake_log_traceback
    try:
        exec_globals = dict(vars(rtgd))
        exec(
            "weeutil.logger.log_traceback(log.critical, 'rtgdthread: **** ')",
            exec_globals,
        )
    finally:
        rtgd.weeutil.logger.log_traceback = real
    assert captured["level"] == rtgd.log.critical
    assert captured["prefix"] == "rtgdthread: **** "


# ---------------------------------------------------------------------------
# 0003 — purpleair dedupe consecutive inserts
# ---------------------------------------------------------------------------
def check_0003_purpleair_dedupe_consecutive_inserts() -> None:
    purpleair = _import("purpleair")
    inst = object.__new__(purpleair.PurpleAirMonitor)
    inst.dbm = Mock()

    inst.save_data({"dateTime": 1000})
    inst.save_data({"dateTime": 1000})  # duplicate -> must be skipped
    assert inst.dbm.addRecord.call_count == 1, (
        "save_data must skip a duplicate dateTime so the DB never sees a "
        "UNIQUE-archive.dateTime violation"
    )
    inst.save_data({"dateTime": 2000})  # new ts -> must go through
    assert inst.dbm.addRecord.call_count == 2
    assert inst._last_inserted_ts == 2000


# ---------------------------------------------------------------------------
# 0004 — forecast uppercase Zambretti SQL
# ---------------------------------------------------------------------------
def check_0004_forecast_uppercase_zambretti_sql() -> None:
    forecast = _import("forecast")
    src = inspect.getsource(forecast.ForecastVariables.zambretti)

    assert (
        "SELECT dateTime,zcode FROM %s WHERE method = 'Zambretti' "
        "ORDER BY dateTime DESC LIMIT 1" in src
    ), (
        "Zambretti SELECT must use uppercase SQL keywords; lowercase `desc` "
        "collides with weedb/mysql.py auto-backticking and mangles the "
        "ORDER BY direction on MariaDB"
    )
    assert "order by dateTime desc limit 1" not in src, (
        "lowercase `desc` direction keyword must not appear in the Zambretti "
        "SQL; weedb/mysql.py would backtick it as a reserved column name"
    )


# ---------------------------------------------------------------------------
# 0005 — previmeteo qualify weewx.restx.get_site_dict
# ---------------------------------------------------------------------------
def check_0005_previmeteo_qualify_get_site_dict() -> None:
    previmeteo = _import("previmeteo")

    with patch.object(
        previmeteo.weewx.restx, "get_site_dict", return_value=None
    ) as gsd:
        cfg = {"Previmeteo": {"station": "S", "password": "P"}}
        engine = Mock()
        svc = previmeteo.StdPrevimeteo(engine=engine, config_dict=cfg)
        assert svc is not None
        gsd.assert_called_once()
        args = gsd.call_args[0]
        assert args[0] is cfg
        assert args[1] == "Previmeteo"
        assert args[2] == "station"
        assert args[3] == "password"


# ---------------------------------------------------------------------------
# 0006 — emoncms skip_upload -> AbortedPost
# ---------------------------------------------------------------------------
def check_0006_emoncms_skip_upload_abortedpost() -> None:
    import queue as stdlib_queue
    import weewx.restx

    emoncms = _import("emoncms")
    t = emoncms.EmonCMSThread(
        queue=stdlib_queue.Queue(),
        token="x",
        skip_upload=True,
        manager_dict=None,
    )
    try:
        t.process_record({"dateTime": 1000, "usUnits": 1}, dbm=None)
    except weewx.restx.AbortedPost:
        return
    raise AssertionError(
        "process_record must raise weewx.restx.AbortedPost when "
        "skip_upload is set; otherwise the RESTThread loop falsely logs "
        "`Published record`"
    )


# ---------------------------------------------------------------------------
# 0007 — rtgd guard Buffer.start_of_day_reset
# ---------------------------------------------------------------------------
def check_0007_rtgd_guard_start_of_day_reset() -> None:
    rtgd = _import("rtgd")

    buf = dict.__new__(rtgd.Buffer)
    dict.__init__(buf)
    buf.manifest = ["outTemp", "humidex"]
    buf["outTemp"] = Mock()

    buf.start_of_day_reset()
    assert buf["outTemp"].day_reset.call_count == 1


# ---------------------------------------------------------------------------
# 0008 — rtldavis low-battery regex
# ---------------------------------------------------------------------------
def check_0008_rtldavis_low_battery_regex() -> None:
    rtl = _import("rtldavis")
    rx = rtl.DATAPacket.IDENTIFIER

    assert rx.match("12:34:56.789012 50FF11223344556677") is not None, (
        "patched regex must still accept normal-battery payloads (2nd nibble 0-7)"
    )
    assert rx.match("12:34:56.789012 58FF11223344556677") is not None, (
        "patched regex must accept low-battery payloads (2nd nibble 8-F); "
        "the unpatched regex restricts position 1 to [0-7] and drops every "
        "packet once the battery goes low, taking the driver silently dark"
    )
    assert rx.match("12:34:56.789012 58FF1122334455") is None, (
        "regex must still reject short payloads (length check intact)"
    )


# ---------------------------------------------------------------------------
# 0009 — rtldavis Python 3.13 r-strings
# ---------------------------------------------------------------------------
def check_0009_rtldavis_python313_rstrings() -> None:
    src_path = WEEWX_BIN / "user" / "rtldavis.py"
    assert src_path.exists(), f"missing {src_path}"

    code = (
        f"import py_compile, sys\npy_compile.compile({str(src_path)!r}, doraise=True)\n"
    )
    # Use the weewx venv Python (the same interpreter weewxd uses to load
    # rtldavis.py at runtime), not sys.executable. check_image.sh invokes us
    # as `python3 check_patches.py` which can resolve to the system Python;
    # if it ever diverges from the venv Python the SyntaxWarning gate would
    # silently test the wrong interpreter.
    result = subprocess.run(
        ["/opt/weewx/bin/python3", "-W", "error::SyntaxWarning", "-c", code],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        "rtldavis.py must compile cleanly under -W error::SyntaxWarning; "
        "unprefixed regex strings raise SyntaxWarning on Py 3.12+ which "
        f"noisies every weewxd start.\nstdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )
    assert "SyntaxWarning" not in result.stderr, (
        f"unexpected SyntaxWarning surfaced:\n{result.stderr}"
    )


# ---------------------------------------------------------------------------
# 0010 — rtldavis transmitters_override
# ---------------------------------------------------------------------------
def _rtldavis_build_driver(override):
    rtl = _import("rtldavis")
    stn = {
        "iss_channel": 1,
        "anemometer_channel": 0,
        "leaf_soil_channel": 0,
        "temp_hum_1_channel": 0,
        "temp_hum_2_channel": 0,
    }
    if override is not None:
        stn["transmitters_override"] = override
    cfg = {"Rtldavis": stn}
    with patch.object(rtl, "ProcManager", lambda *a, **kw: Mock()):
        drv = rtl.RtldavisDriver(engine=None, config_dict=cfg)
    return drv


def check_0010_rtldavis_transmitters_override() -> None:
    drv = _rtldavis_build_driver("255")
    assert drv.transmitters == 255, (
        "transmitters_override='255' must set the bitmask directly, "
        "bypassing the 5-slot channel computation"
    )
    assert drv.tr_count == 8, (
        "successful override must recompute tr_count from the new bitmask"
    )

    drv = _rtldavis_build_driver("not-an-int")
    assert drv.transmitters == 1, (
        "invalid transmitters_override must be logged and skipped, leaving "
        "the slot-derived bitmask intact (not crash driver init)"
    )

    drv = _rtldavis_build_driver(None)
    assert drv.transmitters == 1, (
        "absent transmitters_override must leave the slot-derived bitmask"
    )


# ---------------------------------------------------------------------------
# 0011 — rtgd history_max None guard
# ---------------------------------------------------------------------------
def _rtgd_wgust_slice():
    rtgd = _import("rtgd")
    src = inspect.getsource(rtgd.RealtimeGaugeDataThread.calculate)
    body_start = src.index("# wgust - 10 minute high gust")
    line_start = src.rfind("\n", 0, body_start) + 1
    end = src.index("#        # avgbearing", line_start)
    return rtgd, textwrap.dedent(src[line_start:end])


def check_0011_rtgd_history_max_none_guard() -> None:
    rtgd, body = _rtgd_wgust_slice()
    # Branch A: buffer has windGust, history_max returns None.
    self_mock = Mock()
    self_mock.buffer = {"windGust": Mock()}
    self_mock.buffer["windGust"].history_max = Mock(return_value=None)
    self_mock.packet_unit_dict = {
        "windSpeed": {"units": "km_per_hour", "group": "group_speed"}
    }
    self_mock.wind_group = "km_per_hour"
    self_mock.wind_format = "%.1f"
    data: dict = {}
    ts = 1_700_000_000
    g = dict(vars(rtgd))
    g.update({"self": self_mock, "data": data, "ts": ts})
    exec(body, g)
    assert data["wgust"] == "0.0", (
        "patched wgust branch must fall back to 0.0 when history_max returns "
        "None; unpatched code raises AttributeError on .value and kills the "
        "rtgd thread on every LOOP packet"
    )

    # Branch B: buffer has only windSpeed, history_max returns None.
    self_mock = Mock()
    self_mock.buffer = {"windSpeed": Mock()}
    self_mock.buffer["windSpeed"].history_max = Mock(return_value=None)
    self_mock.packet_unit_dict = {
        "windSpeed": {"units": "km_per_hour", "group": "group_speed"}
    }
    self_mock.wind_group = "km_per_hour"
    self_mock.wind_format = "%.1f"
    data = {}
    g = dict(vars(rtgd))
    g.update({"self": self_mock, "data": data, "ts": ts})
    exec(body, g)
    assert data["wgust"] == "0.0"


# ---------------------------------------------------------------------------
# 0012 — rtldavis merge _last_seen
# ---------------------------------------------------------------------------
def check_0012_rtldavis_merge_last_seen() -> None:
    rtl = _import("rtldavis")
    drv = object.__new__(rtl.RtldavisDriver)
    drv.last_rain_count = None
    drv.rain_per_tip = 0.01
    drv.sensor_map = dict(rtl.RtldavisDriver.DEFAULT_SENSOR_MAP)

    p1 = drv._data_to_packet({"temperature": 20.0})
    assert p1["outTemp"] == 20.0
    assert "outHumidity" not in p1

    p2 = drv._data_to_packet({"humidity": 60.0})
    assert p2["outHumidity"] == 60.0
    assert p2["outTemp"] == 20.0, (
        "patched _data_to_packet must merge last-seen non-rain fields into "
        "every LOOP packet so StdWXCalculate sees both outTemp and "
        "outHumidity together"
    )

    p3 = drv._data_to_packet({"rain_count": 5})
    assert "rain" in p3
    p4 = drv._data_to_packet({"temperature": 21.0})
    assert "rain" not in p4, (
        "rain is an incremental delta; the merge step must skip it so a "
        "subsequent packet without rain_count does not double-count tips"
    )


# ---------------------------------------------------------------------------
# 0013 — rtgd FieldMap deepcopy
# ---------------------------------------------------------------------------
def _rtgd_fieldmap_slice():
    rtgd = _import("rtgd")
    src = inspect.getsource(rtgd.RealtimeGaugeDataThread.__init__)
    needle = "_src_map = rtgd_config_dict.get('FieldMap'"
    body_start = src.index(needle)
    line_start = src.rfind("\n", 0, body_start) + 1
    end = src.index("self.field_map = _field_map", line_start)
    end = src.index("\n", end) + 1
    return rtgd, textwrap.dedent(src[line_start:end])


def _run_fieldmap(rtgd, body, rtgd_config_dict):
    self_mock = Mock()

    class _UnitsDict(dict):
        def __missing__(self, key):
            return "degree_compass"

    self_mock.units_dict = _UnitsDict()
    g = dict(vars(rtgd))
    g.update({"self": self_mock, "rtgd_config_dict": rtgd_config_dict})
    exec(body, g)
    return self_mock.field_map


def check_0013_rtgd_fieldmap_deepcopy() -> None:
    rtgd, body = _rtgd_fieldmap_slice()
    cfg: dict = {}
    fm1 = _run_fieldmap(rtgd, body, cfg)
    # Second run must not crash because DEFAULT_FIELD_MAP was not mutated.
    fm2 = _run_fieldmap(rtgd, body, cfg)
    assert "bearing" in fm1 and "bearing" in fm2
    assert isinstance(fm1["bearing"]["default"], rtgd.ValueTuple)
    assert isinstance(fm2["bearing"]["default"], rtgd.ValueTuple)
    assert rtgd.DEFAULT_FIELD_MAP["bearing"]["default"] == 0, (
        "patched __init__ must not mutate the module-global DEFAULT_FIELD_MAP; "
        "a leaked ValueTuple default trips a TypeError in the second "
        "in-process __init__ via the weewxd engine retry loop"
    )


# ---------------------------------------------------------------------------
# 0014 — rtgd tick_interval
# ---------------------------------------------------------------------------
def check_0014_rtgd_tick_interval() -> None:
    rtgd = _import("rtgd")

    thr = object.__new__(rtgd.RealtimeGaugeDataThread)
    cached_packet = {"dateTime": 0}
    calculate = Mock(return_value={"some": "data"})
    write_data = Mock()
    get_lost_contact = Mock(return_value=False)
    thr.packet_cache = Mock()
    thr.packet_cache.get_packet = Mock(return_value=cached_packet)
    thr.max_cache_age = 600
    thr.calculate = calculate
    thr.write_data = write_data
    thr.get_lost_contact = get_lost_contact
    thr.exporter = None
    thr.last_write = 0

    now = 1234567890.7  # frac > 0.5 — int(now+0.5) rounds up.
    real_time = rtgd.time.time
    rtgd.time.time = lambda: now
    try:
        thr._emit_tick()
    finally:
        rtgd.time.time = real_time

    assert calculate.call_count == 1
    arg_packet = calculate.call_args[0][0]
    assert arg_packet is cached_packet
    get_packet_args = thr.packet_cache.get_packet.call_args[0]
    assert get_packet_args[0] == int(now + 0.5), (
        "ts passed to get_packet must round to the nearest integer second so "
        'calculate()\'s strftime("%S") matches LOOP-packet rounding'
    )
    assert thr.last_write == now, (
        "self.last_write must be the un-rounded float time.time(); using the "
        "rounded ts schedules the next tick from a future timestamp and "
        "re-introduces the 2 s-clock bug at the scheduler layer"
    )
    write_data.assert_called_once_with({"some": "data"})


# ---------------------------------------------------------------------------
# Registry — name -> callable. Names mirror the patch filename stem.
# ---------------------------------------------------------------------------
CHECKS: list[tuple[str, Callable[[], None]]] = [
    ("0001-previmeteo-py3-queue-shim", check_0001_previmeteo_py3_queue_shim),
    ("0002-rtgd-verbose-thread-traceback", check_0002_rtgd_verbose_thread_traceback),
    (
        "0003-purpleair-dedupe-consecutive-inserts",
        check_0003_purpleair_dedupe_consecutive_inserts,
    ),
    (
        "0004-forecast-uppercase-zambretti-sql",
        check_0004_forecast_uppercase_zambretti_sql,
    ),
    (
        "0005-previmeteo-qualify-get-site-dict",
        check_0005_previmeteo_qualify_get_site_dict,
    ),
    (
        "0006-emoncms-skip-upload-abortedpost",
        check_0006_emoncms_skip_upload_abortedpost,
    ),
    ("0007-rtgd-guard-start-of-day-reset", check_0007_rtgd_guard_start_of_day_reset),
    ("0008-rtldavis-low-battery-regex", check_0008_rtldavis_low_battery_regex),
    ("0009-rtldavis-python313-rstrings", check_0009_rtldavis_python313_rstrings),
    ("0010-rtldavis-transmitters-override", check_0010_rtldavis_transmitters_override),
    ("0011-rtgd-history-max-none-guard", check_0011_rtgd_history_max_none_guard),
    ("0012-rtldavis-merge-last-seen", check_0012_rtldavis_merge_last_seen),
    ("0013-rtgd-fieldmap-deepcopy", check_0013_rtgd_fieldmap_deepcopy),
    ("0014-rtgd-tick-interval", check_0014_rtgd_tick_interval),
]


def main() -> int:
    fail = 0
    for name, fn in CHECKS:
        try:
            fn()
        except BaseException as e:
            fail = 1
            # Single-line failure reason; collapse multi-line tracebacks.
            reason = "".join(traceback.format_exception_only(type(e), e)).strip()
            reason = reason.replace("\n", " | ")
            print(f"FAIL  patch:{name}: {reason}")
        else:
            print(f"PASS  patch:{name}")
    return fail


if __name__ == "__main__":
    sys.exit(main())
