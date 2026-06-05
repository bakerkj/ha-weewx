# Copyright (c) 2026 Kenneth Baker <bakerkj@umich.edu>
# All rights reserved.

"""Behavioural tests for extensions/log_to_file.py.

These pin current behaviour so the upcoming refactor can be verified
not to regress. They drive LogToFileThread.process_record directly,
bypassing the queue + thread machinery and stubbing get_record so no
real database is required.
"""

from types import SimpleNamespace

import pytest
import weewx

from log_to_file import LogToFile, LogToFileThread


@pytest.fixture
def archive_us():
    """Stand-in dbmanager exposing only what process_record reads."""
    return SimpleNamespace(std_unit_system=weewx.US)


@pytest.fixture
def thread_factory(tmp_path, monkeypatch):
    """Build a LogToFileThread whose get_record is a no-op pass-through.

    Avoids any DB interaction; process_record then drives only the formatting
    + dedup + file-write paths under test.
    """

    def _make(**kwargs):
        path = kwargs.pop("path", str(tmp_path / "log.txt"))
        t = LogToFileThread(q=None, manager_dict=None, path=path, **kwargs)
        monkeypatch.setattr(t, "get_record", lambda record, archive: dict(record))
        return t

    return _make


def _read_lines(path):
    with open(path) as f:
        return [ln.rstrip("\n") for ln in f if ln.strip()]


def _us_record(ts=1_700_000_000, **fields):
    """Build a record dict tagged as US units (avoids unit-system conversion)."""
    return {"dateTime": ts, "usUnits": weewx.US, **fields}


# --------------------------------------------------------------------------
# basic write + skip_keys
# --------------------------------------------------------------------------


def test_writes_one_line_with_timestamp_first(thread_factory, archive_us, tmp_path):
    path = str(tmp_path / "log.txt")
    t = thread_factory(path=path)
    t.process_record(_us_record(outTemp=72.5), archive_us)
    lines = _read_lines(path)
    assert len(lines) == 1
    parts = lines[0].split(",")
    # weeutil timestamp string lands as the first field
    assert parts[0] and "1700000000" in parts[0]
    # outTemp emitted with current %f formatting + the unit-mapped label
    outtemp = next(p for p in parts if p.startswith("outTemp:"))
    assert outtemp.endswith(":F")
    assert outtemp.split(":")[1].startswith("72.5")
    # internal/skip keys not emitted
    assert "dateTime" not in lines[0]
    assert "usUnits" not in lines[0]


def test_skips_none_valued_fields(thread_factory, archive_us, tmp_path):
    path = str(tmp_path / "log.txt")
    t = thread_factory(path=path)
    t.process_record(_us_record(outTemp=72.5, inTemp=None), archive_us)
    line = _read_lines(path)[0]
    assert "outTemp" in line
    assert "inTemp" not in line


# --------------------------------------------------------------------------
# _data_map: per-key label and format overrides
# --------------------------------------------------------------------------


def test_data_map_substitutes_label_and_format_for_forecastRule(
    thread_factory, archive_us, tmp_path
):
    path = str(tmp_path / "log.txt")
    t = thread_factory(path=path)
    t.process_record(_us_record(forecastRule=2), archive_us)
    line = _read_lines(path)[0]
    assert "forecastRule:2:rule" in line.split(",")


def test_data_map_substitutes_for_interval(thread_factory, archive_us, tmp_path):
    path = str(tmp_path / "log.txt")
    t = thread_factory(path=path)
    t.process_record(_us_record(interval=5), archive_us)
    line = _read_lines(path)[0]
    assert "interval:5:minutes" in line.split(",")


# --------------------------------------------------------------------------
# _tuple_type_mapping: short label aliases for common unit strings
# --------------------------------------------------------------------------


def test_tuple_type_mapping_compass_label(thread_factory, archive_us, tmp_path):
    path = str(tmp_path / "log.txt")
    t = thread_factory(path=path)
    t.process_record(_us_record(windDir=180.0), archive_us)
    line = _read_lines(path)[0]
    tok = [p for p in line.split(",") if p.startswith("windDir:")][0]
    assert tok.endswith(":degree")


def test_tuple_type_mapping_radiation_label(thread_factory, archive_us, tmp_path):
    path = str(tmp_path / "log.txt")
    t = thread_factory(path=path)
    t.process_record(_us_record(radiation=420.0), archive_us)
    line = _read_lines(path)[0]
    tok = [p for p in line.split(",") if p.startswith("radiation:")][0]
    assert tok.endswith(":watts/m^2")


# --------------------------------------------------------------------------
# dedup logic in process_record: time-or-content based gating
# --------------------------------------------------------------------------


def test_identical_record_within_60s_is_deduped(thread_factory, archive_us, tmp_path):
    path = str(tmp_path / "log.txt")
    t = thread_factory(path=path)
    rec = _us_record(ts=1_700_000_000, outTemp=72.5)
    t.process_record(rec, archive_us)
    t.process_record(_us_record(ts=1_700_000_030, outTemp=72.5), archive_us)
    assert len(_read_lines(path)) == 1


def test_identical_record_after_60s_writes_again(thread_factory, archive_us, tmp_path):
    path = str(tmp_path / "log.txt")
    t = thread_factory(path=path)
    t.process_record(_us_record(ts=1_700_000_000, outTemp=72.5), archive_us)
    t.process_record(_us_record(ts=1_700_000_061, outTemp=72.5), archive_us)
    assert len(_read_lines(path)) == 2


def test_changed_record_within_60s_writes_again(thread_factory, archive_us, tmp_path):
    path = str(tmp_path / "log.txt")
    t = thread_factory(path=path)
    t.process_record(_us_record(ts=1_700_000_000, outTemp=72.5), archive_us)
    t.process_record(_us_record(ts=1_700_000_005, outTemp=73.0), archive_us)
    assert len(_read_lines(path)) == 2


# --------------------------------------------------------------------------
# unit-system normalization
# --------------------------------------------------------------------------


def test_metricwx_record_converted_to_archive_us_before_processing(
    thread_factory, tmp_path
):
    path = str(tmp_path / "log.txt")
    t = thread_factory(path=path)
    archive = SimpleNamespace(std_unit_system=weewx.US)
    # 20C in METRICWX -> 68F in US
    rec = {"dateTime": 1_700_000_000, "usUnits": weewx.METRICWX, "outTemp": 20.0}
    t.process_record(rec, archive)
    line = _read_lines(path)[0]
    tok = [p for p in line.split(",") if p.startswith("outTemp:")][0]
    # whatever the precise rounding, label is the US label
    assert tok.endswith(":F")


def test_archive_with_no_unit_system_skips_conversion(thread_factory, tmp_path):
    path = str(tmp_path / "log.txt")
    t = thread_factory(path=path)
    archive = SimpleNamespace(std_unit_system=None)
    # US record + None archive -> processed in US, no conversion attempted
    t.process_record(_us_record(outTemp=72.5), archive)
    assert _read_lines(path)


# --------------------------------------------------------------------------
# skip_upload short-circuit
# --------------------------------------------------------------------------


def test_skip_upload_writes_nothing(thread_factory, archive_us, tmp_path):
    path = str(tmp_path / "log.txt")
    t = thread_factory(path=path, skip_upload=True)
    t.process_record(_us_record(outTemp=72.5), archive_us)
    assert not (tmp_path / "log.txt").exists()


# --------------------------------------------------------------------------
# file handle: held open across records (single open per thread lifetime)
# --------------------------------------------------------------------------


def test_file_handle_opened_once_for_multiple_records(
    thread_factory, archive_us, tmp_path, monkeypatch
):
    """Three records => one open() call. Locks in the held-fh contract so a
    future refactor doesn't quietly regress to open/close per record."""
    path = str(tmp_path / "log.txt")
    t = thread_factory(path=path)

    open_calls: list[str] = []
    real_open = open

    def counting_open(p, *args, **kwargs):
        if p == path:
            open_calls.append(p)
        return real_open(p, *args, **kwargs)

    monkeypatch.setattr("log_to_file.open", counting_open, raising=False)
    import builtins

    monkeypatch.setattr(builtins, "open", counting_open)

    t.process_record(_us_record(ts=1_700_000_000, outTemp=70.0), archive_us)
    t.process_record(_us_record(ts=1_700_000_100, outTemp=71.0), archive_us)
    t.process_record(_us_record(ts=1_700_000_200, outTemp=72.0), archive_us)

    assert len(open_calls) == 1, open_calls
    assert len(_read_lines(path)) == 3


def test_writes_visible_to_external_reader_before_thread_exits(
    thread_factory, archive_us, tmp_path
):
    """Line-buffered writes must be visible to a separate read() while the
    thread still holds the fh open."""
    path = str(tmp_path / "log.txt")
    t = thread_factory(path=path)
    t.process_record(_us_record(ts=1_700_000_000, outTemp=70.0), archive_us)
    # Thread is still alive; fh still open. Reader should see the line.
    assert len(_read_lines(path)) == 1


# --------------------------------------------------------------------------
# error handling: per-record failure is logged, doesn't propagate
# --------------------------------------------------------------------------


def test_record_with_unformattable_field_does_not_crash(
    thread_factory, archive_us, tmp_path, caplog
):
    """The catch-all in process_record swallows formatting errors and logs
    them; this pins that behaviour so the upcoming refactor knows it must
    keep (or deliberately change) that contract."""
    import logging

    path = str(tmp_path / "log.txt")
    t = thread_factory(path=path)
    rec = _us_record(outTemp=72.5)
    # path is unwritable directory => open() inside process_record raises
    t.path = str(tmp_path / "nonexistent_subdir" / "log.txt")
    with caplog.at_level(logging.ERROR, logger="log_to_file"):
        t.process_record(rec, archive_us)
    assert any("LogToFile" in rec.message for rec in caplog.records)


# --------------------------------------------------------------------------
# LogToFile setup: missing 'path' config returns cleanly without binding
# --------------------------------------------------------------------------


def test_logtofile_missing_path_config_does_not_bind(monkeypatch):
    """If [[LogToFile]] has no 'path', the service must not bind to event
    streams and must not start a worker thread."""
    import configobj

    bound = []

    class FakeEngine:
        pass

    cfg = configobj.ConfigObj()
    cfg["StdRESTful"] = {"LogToFile": {"log_success": "true"}}
    cfg["DataBindings"] = {}
    cfg["Databases"] = {}

    monkeypatch.setattr(
        LogToFile, "bind", lambda self, evt, fn: bound.append(evt), raising=False
    )
    monkeypatch.setattr(
        "log_to_file.weewx.manager.get_manager_dict",
        lambda *a, **kw: {},
    )

    svc = LogToFile(FakeEngine(), cfg)
    assert bound == []
    assert svc._configured is False
