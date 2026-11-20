#!/usr/bin/env python3
# Copyright (c) 2026 Kenneth Baker <bakerkj@umich.edu>
# All rights reserved.

"""In-image behavioural checks for the 16 bundled-extension patches.

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
from collections.abc import Callable
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
        # exec: patch verifier deliberately runs an extracted snippet in
        # a controlled globals dict — this is not user input.
        exec(  # noqa: S102
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
        check=False,
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
# 0013 — rtgd field map copied into plain dicts before deepcopy
# ---------------------------------------------------------------------------
def _rtgd_fieldmap_body(rtgd) -> str:
    """The constructor's field-map block, _group_map through self.field_map."""
    src = inspect.getsource(rtgd.RealtimeGaugeDataThread.__init__)
    s = src.index("_group_map = copy.deepcopy(DEFAULT_GROUP_MAP)")
    line_start = src.rfind("\n", 0, s) + 1
    e = src.index("self.field_map = updated_field_map", line_start)
    e = src.index("\n", e) + 1
    return textwrap.dedent(src[line_start:e])


def check_0013_rtgd_fieldmap_deepcopy() -> None:
    """A weewx.conf read the way weewxd reads it (ConfigParser interpolation)
    with a [Logging] formatter and [[FieldMapExtensions]] must build the field
    map, twice in one process (weewxd's engine retry loop), without mutating
    DEFAULT_FIELD_MAP. Pre-0013, deep-copying the configobj sections raised
    MissingInterpolationOption on %(asctime)s.
    """
    import copy
    import tempfile

    import weecfg

    rtgd = _import("rtgd")
    body = _rtgd_fieldmap_body(rtgd)
    conf = textwrap.dedent(
        """\
        WEEWX_ROOT = /opt/weewx-data
        [RealtimeGaugeData]
            [[FieldMapExtensions]]
                [[[rrate]]]
                    source = rainRate
                    format = %.2f
        [Logging]
            [[formatters]]
                [[[standard]]]
                    format = '%(asctime)s %(levelname)s %(message)s'
        """
    )
    before = copy.deepcopy(rtgd.DEFAULT_FIELD_MAP)
    with tempfile.NamedTemporaryFile("w", suffix=".conf") as f:
        f.write(conf)
        f.flush()
        _, config_dict = weecfg.read_config(f.name)
    for run in (1, 2):
        self_mock = Mock()
        self_mock.get_unit_group = rtgd.RealtimeGaugeDataThread.get_unit_group
        g = dict(vars(rtgd))
        g.update(
            {"self": self_mock, "rtgd_config_dict": config_dict["RealtimeGaugeData"]}
        )
        exec(body, g)  # noqa: S102 -- patch verifier
        fm = self_mock.field_map
        assert isinstance(fm["temp"]["default"], rtgd.ValueTuple), (
            f"run {run}: defaults must be converted to ValueTuples"
        )
        assert fm["rrate"]["format"] == "%.2f", (
            f"run {run}: the FieldMapExtensions entry must be merged"
        )
    assert rtgd.DEFAULT_FIELD_MAP == before, (
        "building the field map must not mutate the module-global DEFAULT_FIELD_MAP"
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
# 0015 — rtgd skip-empty-source FieldMap entries
# ---------------------------------------------------------------------------
def check_0015_rtgd_skip_empty_source() -> None:
    rtgd = _import("rtgd")

    # --- emit-loop site (in calculate): empty-source fields skipped ---
    src = inspect.getsource(rtgd.RealtimeGaugeDataThread.calculate)
    needle = "for field in self.field_map:"
    start = src.index(needle)
    end = src.index("return data", start)
    loop_body = textwrap.dedent(src[start:end])

    self_mock = Mock()
    self_mock.field_map = {
        "temp": {"source": "outTemp", "format": "%.1f"},
        "inhum": {"source": ""},  # operator override -> must be skipped
        "intemp": {},  # missing source key entirely -> must be skipped
        "press": {"source": "barometer", "format": "%.3f"},
    }
    self_mock.get_field_value = Mock(side_effect=lambda f, p: f"<{f}>")

    data: dict = {}
    g = {"self": self_mock, "data": data, "packet": {}}
    exec(loop_body, g)  # noqa: S102  # patch verifier: exec of extracted snippet

    assert "temp" in data and "press" in data, (
        "fields with a populated source must still be emitted to gauge-data.txt"
    )
    assert "inhum" not in data, (
        "field with empty `source =` must be dropped from gauge-data.txt — "
        "that's the whole point of the operator-facing override; falling "
        "back to None/default leaves the field visible"
    )
    assert "intemp" not in data, (
        "field with no `source` key at all must also be dropped (defence "
        "in depth: empty-string and missing both mean 'do not emit')"
    )
    assert self_mock.get_field_value.call_count == 2, (
        "skipped fields must not invoke get_field_value — the skip has to "
        "short-circuit before the lookup, otherwise units-dict access on "
        "an empty source raises and the loop dies"
    )

    # --- constructor site (in __init__): empty-source fields skipped too ---
    # Without this, get_unit_group('') returns None and _group_map[None]
    # KeyErrors at boot. Confirm by exec'ing the constructor's field-map
    # block with an empty-source FieldMapExtensions entry.
    body = _rtgd_fieldmap_body(rtgd)

    self2 = Mock()
    self2.get_unit_group = rtgd.RealtimeGaugeDataThread.get_unit_group
    cfg = {
        "FieldMapExtensions": {
            "inhum": {"source": ""},
        }
    }
    g = dict(vars(rtgd))
    g.update({"self": self2, "rtgd_config_dict": cfg})
    try:
        exec(body, g)  # noqa: S102 -- patch verifier
    except KeyError as exc:
        raise AssertionError(
            "constructor must skip an empty-source FieldMapExtensions entry "
            "before get_unit_group('') -> None reaches _group_map[None] "
            f"(got KeyError {exc!r})"
        ) from exc
    assert "inhum" in self2.field_map, (
        "empty-source override should still land in self.field_map so the "
        "calculate() emit-loop skips it (rather than processing it and "
        "falling back to a default value)"
    )
    assert not self2.field_map["inhum"].get("source"), (
        "merged field_map['inhum']['source'] must remain empty/missing — "
        "the patch must not silently fill in a default source"
    )


# ---------------------------------------------------------------------------
# 0016 — rtgd buffer-source guard in get_field_value aggregate branches
# ---------------------------------------------------------------------------
def check_0016_rtgd_buffer_source_guard() -> None:
    """get_field_value must NOT KeyError when an aggregate field's source obs
    isn't yet in self.buffer. self.buffer is populated lazily by
    process_new_loop_packet as obs arrive; derived obs (appTemp from
    StdWXCalculate, etc.) may be absent during the startup window where
    _emit_tick fires against a cached packet. Pre-0016 the bare
    self.buffer[source] lookup raised:
        KeyError: 'appTemp'
        File "rtgd.py", in get_field_value, _result_vt = ValueTuple(
            getattr(self.buffer[source], agg), ...)
    """
    rtgd = _import("rtgd")

    thr = object.__new__(rtgd.RealtimeGaugeDataThread)
    # buffer has 'outTemp' but is MISSING 'appTemp' — mirrors the real
    # boot race after my hass restart that hit this exact KeyError.
    out_temp = Mock()
    out_temp.max = 72.5
    out_temp.min = 60.1
    out_temp.sum = 1500.0
    out_temp.last = 70.0
    out_temp.maxtime = 1781508000  # epoch -> "HH:MM" via strftime
    out_temp.mintime = 1781490000
    out_temp.lasttime = 1781508000
    out_temp.count = 42
    thr.buffer = {"outTemp": out_temp}
    # rtgd's default output groups (as in production), in degree_F to match
    # the packet units. get_unit_group(source, 'count') resolves to
    # group_count, which DEFAULT_GROUP_MAP lacks; add it so the count
    # aggregate is covered.
    thr.group_map = dict(
        rtgd.DEFAULT_GROUP_MAP, group_temperature="degree_F", group_count="count"
    )
    thr.packet_unit_dict = {
        "outTemp": {"units": "degree_F", "group": "group_temperature"}
    }
    # Field map exercises EVERY aggregate type the 0016 guard touches.
    # The pre-0016 production crash was `KeyError: 'appTemp'`; the
    # SECOND production crash (after my half-fix shipped in 0.1.19/0.1.20)
    # was `ValueError: unsupported format character 'H'` from the
    # TapptempTH (maxtime) path falling to the default-fallback with a
    # strftime-style format. This test must cover ALL aggregate types
    # used in DEFAULT_FIELD_MAP so a per-type regression can't slip
    # through again.
    base = {
        "aggregate_period": "day",
        "default": rtgd.ValueTuple(0, "degree_F", "group_temperature"),
    }
    # Time aggregates resolve to group_time, so the constructor builds their
    # defaults in unix_epoch; mirror that here.
    base_time = {**base, "default": rtgd.ValueTuple(0, "unix_epoch", "group_time")}
    # Likewise count resolves to group_count (needs group_count in [[Groups]]).
    base_count = {**base, "default": rtgd.ValueTuple(0, "count", "group_count")}
    thr.field_map = {
        # numeric-format aggregates (value-producing)
        "tempTH": {"source": "outTemp", "format": "%.1f", "aggregate": "max", **base},
        "tempTL": {"source": "outTemp", "format": "%.1f", "aggregate": "min", **base},
        "tempsum": {"source": "outTemp", "format": "%.1f", "aggregate": "sum", **base},
        "templast": {
            "source": "outTemp",
            "format": "%.1f",
            "aggregate": "last",
            **base,
        },
        "tempcount": {
            "source": "outTemp",
            "format": "%.0f",
            "aggregate": "count",
            **base_count,
        },
        # strftime-format aggregates (time-producing) — these are the
        # T* fields (TtempTH, TapptempTH, TwgustTM, etc.) that crashed
        # the rtgd thread in 0.1.20 with `ValueError: unsupported
        # format character 'H'`.
        "TtempTH": {
            "source": "outTemp",
            "format": "%H:%M",
            "aggregate": "maxtime",
            **base_time,
        },
        "TtempTL": {
            "source": "outTemp",
            "format": "%H:%M",
            "aggregate": "mintime",
            **base_time,
        },
        "Ttemplast": {
            "source": "outTemp",
            "format": "%H:%M",
            "aggregate": "lasttime",
            **base_time,
        },
        # missing-source counterparts of each — the actual race
        "apptempTH": {
            "source": "appTemp",
            "format": "%.1f",
            "aggregate": "max",
            **base,
        },
        "apptempTL": {
            "source": "appTemp",
            "format": "%.1f",
            "aggregate": "min",
            **base,
        },
        "TapptempTH": {
            "source": "appTemp",
            "format": "%H:%M",
            "aggregate": "maxtime",
            **base_time,
        },
        "TapptempTL": {
            "source": "appTemp",
            "format": "%H:%M",
            "aggregate": "mintime",
            **base_time,
        },
        "Tapptemplast": {
            "source": "appTemp",
            "format": "%H:%M",
            "aggregate": "lasttime",
            **base_time,
        },
        "apptempcount": {
            "source": "appTemp",
            "format": "%.0f",
            "aggregate": "count",
            **base_count,
        },
    }
    packet = {"dateTime": 1781508000, "usUnits": 1}

    # --- present-source aggregates: all paths must return real values ---
    for name in (
        "tempTH",
        "tempTL",
        "tempsum",
        "templast",
        "tempcount",
        "TtempTH",
        "TtempTL",
        "Ttemplast",
    ):
        result = thr.get_field_value(name, packet)
        assert result is not None, (
            f"present-source aggregate {name!r} returned None — guard must "
            f"not affect the in-buffer path"
        )
        if "T" in name and name.startswith("T"):
            # time-aggregate should produce HH:MM (or HH:MM:SS depending
            # on the format, but always digits + colon, never raise)
            assert ":" in result, (
                f"time-aggregate {name!r} should format via strftime → "
                f"contain a ':' (got {result!r})"
            )

    # --- missing-source aggregates: all paths must fall to the default
    # value without raising. PRE-PATCH crashes per aggregate type:
    #   max/min/sum/last:  KeyError: 'appTemp'
    #   maxtime/mintime/lasttime: KeyError (pre-0016) -> after my
    #     half-fix, ValueError: unsupported format character 'H'
    #   count:             KeyError: 'appTemp'
    for name in (
        "apptempTH",
        "apptempTL",
        "TapptempTH",
        "TapptempTL",
        "Tapptemplast",
        "apptempcount",
    ):
        try:
            result = thr.get_field_value(name, packet)
        except KeyError as e:
            raise AssertionError(
                f"get_field_value({name!r}) raised KeyError on a missing-buffer "
                f"source — 0016a guard regressed (got {e!r})"
            )
        except ValueError as e:
            raise AssertionError(
                f"get_field_value({name!r}) raised ValueError on the "
                f"default-fallback path for a time-aggregate — 0016b "
                f"strftime route regressed. This is the exact "
                f"`unsupported format character 'H'` storm that hit prod "
                f"in 0.1.20 after the half-fix shipped (got {e!r})"
            )
        assert result is not None, (
            f"missing-source path for {name!r} should fall to the field's "
            f"default value, not None"
        )
        if name.startswith("T"):
            # Time-aggregate default-fallback must produce a HH:MM string
            # (the field's format is '%H:%M' and the default is a
            # numeric ts; 0016b routes through time.localtime + strftime).
            assert ":" in result, (
                f"time-aggregate {name!r} default-fallback must produce "
                f"a strftime-formatted HH:MM string (got {result!r}); "
                f"a numeric result means the patch fell back to the "
                f"`%`-formatter on a `%H:%M` format, which is the bug"
            )


# ---------------------------------------------------------------------------
# 0019 — fuzzy-archer (Bootstrap skin) [Skyfield] data_dir
# ---------------------------------------------------------------------------
def check_0019_fuzzy_archer_ephemeris_data_dir() -> None:
    """With the shipped Bootstrap skin.conf, the ephemeris directory must be
    /opt/weewx-data/ephemeris (where the image ships de440s.bsp) even when
    SQLITE_ROOT is absolute. Pre-0019 it resolved to
    os.path.join(WEEWX_ROOT, SQLITE_ROOT, "skyfield") = /var/lib/weewx/skyfield
    and os.mkdir raised FileNotFoundError because /var/lib/weewx is absent.
    """
    import configobj

    jsonengine = _import("jsonengine")
    seen: list[tuple[str, str]] = []

    class FakeSunEvents:
        def __init__(self, start, end, lon, lat, elev, path, ephemeris):
            seen.append((path, ephemeris))

        def get_transits(self, _angle):
            return None

    gen = object.__new__(jsonengine.JSONGenerator)
    gen.show_daynight = True
    gen.transition_angle = 8
    gen.skin_dict = configobj.ConfigObj(
        "/opt/weewx-data/skins/Bootstrap/skin.conf", encoding="utf-8"
    )
    gen.config_dict = {
        "WEEWX_ROOT": "/opt/weewx-data",
        "DatabaseTypes": {"SQLite": {"SQLITE_ROOT": "/var/lib/weewx"}},
    }
    with patch.object(jsonengine, "SunEvents", FakeSunEvents):
        gen.get_day_night_events(0, 1, 0.0, 0.0, 0)
    assert seen == [("/opt/weewx-data/ephemeris", "de440s.bsp")], seen


# ---------------------------------------------------------------------------
# 0020 — rtgd windrun skips LOOP packets without a wind speed
# ---------------------------------------------------------------------------
def check_0020_rtgd_windrun_null_windspeed() -> None:
    """A Vantage LOOP packet with windSpeed=None (0xff) and windrun=None (set
    by StdWXCalculate with windrun = prefer_hardware) must not raise in
    calc_windrun; windrun must restart on the next valid speed rather than
    span the gap. Pre-0020 this raised TypeError and killed the rtgd thread.
    """
    rtgd = _import("rtgd")
    buf = rtgd.Buffer(rtgd.MANIFEST, {}, None)

    def pkt(ts, speed):
        return {
            "dateTime": ts,
            "usUnits": 1,
            "windSpeed": speed,
            "windDir": 90.0 if speed is not None else None,
            "windrun": None,
        }

    buf.add_packet(pkt(1000, 6.0))
    try:
        buf.add_packet(pkt(1002, None))
    except TypeError as exc:
        raise AssertionError(
            f"a None windSpeed must not reach calc_windrun (got {exc!r})"
        ) from exc
    buf.add_packet(pkt(1004, 6.0))
    assert buf["windrun"].last is None, (
        "the first speed after a gap must restart the interval, not add a "
        "windrun value spanning the gap"
    )
    buf.add_packet(pkt(1006, 6.0))
    windrun = buf["windrun"].last
    assert windrun is not None and abs(windrun - 6.0 * 2 / 3600.0) < 1e-9, (
        "windrun must resume from the restarted interval (6 mph for 2 s)"
    )


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
    ("0012-rtldavis-merge-last-seen", check_0012_rtldavis_merge_last_seen),
    ("0013-rtgd-fieldmap-deepcopy", check_0013_rtgd_fieldmap_deepcopy),
    ("0014-rtgd-tick-interval", check_0014_rtgd_tick_interval),
    ("0015-rtgd-skip-empty-source", check_0015_rtgd_skip_empty_source),
    ("0016-rtgd-buffer-source-guard", check_0016_rtgd_buffer_source_guard),
    (
        "0020-rtgd-windrun-null-windspeed",
        check_0020_rtgd_windrun_null_windspeed,
    ),
    (
        "0019-fuzzy-archer-ephemeris-data-dir",
        check_0019_fuzzy_archer_ephemeris_data_dir,
    ),
]


def main() -> int:
    fail = 0
    for name, fn in CHECKS:
        try:
            fn()
        except BaseException as e:  # noqa: BLE001  # test-runner catch: convert any check failure (incl. AssertionError, SystemExit) to a FAIL row instead of aborting the harness
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
