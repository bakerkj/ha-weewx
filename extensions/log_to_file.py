# Copyright (c) 2026 Kenneth Baker <bakerkj@umich.edu>
# All rights reserved.

# Originally by Ken Baker (bakerkj). Ported from Python 2 / WeeWX 3 to
# Python 3 / WeeWX 5 for the ha-weewx Home Assistant add-on.
"""LogToFile: append a one-line summary of each archive record / loop packet
to a local file.

Wired into weewx as a `restful_services` entry. Format per line:

    <timestamp>,key:value:label,key:value:label,...

Tokens are sorted; `dateTime` and `usUnits` are never emitted; identical
output within 60s is suppressed (a single-line dedup cache).
"""

from __future__ import annotations

import logging
import queue
from dataclasses import dataclass
from typing import Any

import weeutil.weeutil
import weewx
import weewx.manager
import weewx.restx
import weewx.units
from weeutil.weeutil import accumulateLeaves, to_bool

log = logging.getLogger(__name__)


# --------------------------------------------------------------------------
# Per-key formatting overrides.
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class FieldMap:
    """Override for one record key.

    label: the suffix that follows the value in the output token. Empty
        string is "no label" and (combined with the field NOT being in
        ``_data_map``) means the field is silently dropped.
    fmt:   a `%`-style format string applied to the raw value, or None to
        keep weewx's default ValueHelper formatting.
    """

    label: str
    fmt: str | None = None


# Keys whose value should never appear in the output as a normal field.
SKIP_KEYS: frozenset[str] = frozenset({"usUnits", "dateTime"})

# A short label aliases for raw weewx unit strings — applied when no
# entry in FIELD_MAP overrides the label.
UNIT_LABEL_ALIAS: dict[str, str] = {
    "degree_F": "F",
    "degree_compass": "degree",
    "watt_per_meter_squared": "watts/m^2",
}

# Per-key label/format overrides; consulted after the default ValueHelper
# formatting + UNIT_LABEL_ALIAS lookup.
FIELD_MAP: dict[str, FieldMap] = {
    "UV": FieldMap(label="UV"),
    "dayET": FieldMap(label="ET", fmt="%.3f"),
    "forecastRule": FieldMap(label="rule", fmt="%d"),
    "monthET": FieldMap(label="ET", fmt="%.3f"),
    "txBatteryStatus": FieldMap(label="status", fmt="%d"),
    "yearET": FieldMap(label="ET", fmt="%.3f"),
    "sunrise": FieldMap(label="time", fmt="%d"),
    "sunset": FieldMap(label="time", fmt="%d"),
    "interval": FieldMap(label="minutes", fmt="%d"),
}


class LogToFile(weewx.restx.StdRESTful):
    """weewx restx service entry; configured under ``[[LogToFile]]``."""

    def __init__(self, engine, config_dict):
        super().__init__(engine, config_dict)

        try:
            site_dict = accumulateLeaves(
                config_dict["StdRESTful"]["LogToFile"], max_level=1
            )
            site_dict["path"]
        except KeyError as e:
            log.debug("LogToFile: data will not be logged: missing option %s", e)
            return

        manager_dict = weewx.manager.get_manager_dict(
            config_dict["DataBindings"], config_dict["Databases"], "wx_binding"
        )

        site_dict.setdefault("log_success", False)
        site_dict.setdefault("log_failure", False)
        site_dict.setdefault("max_backlog", 0)
        site_dict.setdefault("max_tries", 1)

        self.loop_queue: queue.Queue = queue.Queue()
        self.loop_thread = LogToFileThread(self.loop_queue, manager_dict, **site_dict)
        self.loop_thread.start()

        self.bind(weewx.NEW_LOOP_PACKET, self.new_loop_packet)
        self.bind(weewx.NEW_ARCHIVE_RECORD, self.new_archive_record)

        log.info("LogToFile: data will be logged to file %s", site_dict["path"])

    def new_loop_packet(self, event):
        self.loop_queue.put(event.packet)

    def new_archive_record(self, event):
        self.loop_queue.put(event.record)


class LogToFileThread(weewx.restx.RESTThread):
    """Worker thread: drain queue, format each record, write one line per record."""

    def __init__(
        self,
        q,
        manager_dict,
        path,
        skip_upload: bool = False,
        post_interval=None,
        max_backlog: int = 0,
        stale=None,
        log_success: bool = True,
        log_failure: bool = True,
        timeout: int = 60,
        max_tries: int = 3,
        retry_wait: int = 5,
    ):
        super().__init__(
            q,
            protocol_name="LogToFile",
            manager_dict=manager_dict,
            post_interval=post_interval,
            max_backlog=max_backlog,
            stale=stale,
            log_success=log_success,
            log_failure=log_failure,
            timeout=timeout,
            max_tries=max_tries,
            retry_wait=retry_wait,
        )
        self.path = path
        self.skip_upload = to_bool(skip_upload)
        # Single-line dedup cache.
        self._last_tokens: list[str] | None = None
        self._last_ts: float | None = None

    # ----------------------------------------------------------------------
    # weewx entry point
    # ----------------------------------------------------------------------

    def process_record(self, record: dict, archive) -> None:
        """Log one weewx record to disk."""
        # Normalize to the database's unit system BEFORE handing off to
        # RESTThread.get_record(), which does a strict unit-system equality
        # check between the incoming record and the database and would
        # otherwise raise "Inconsistent units …" — killing the worker thread.
        # This matters for loop packets that arrive before StdConvert has
        # run, and for drivers that emit a unit system different from the
        # one the archive stores.
        if (
            archive is not None
            and getattr(archive, "std_unit_system", None) is not None
            and record.get("usUnits") != archive.std_unit_system
        ):
            record = weewx.units.to_std_system(record, archive.std_unit_system)

        full_record = self.get_record(record, archive)
        us_record = weewx.units.to_US(full_record)

        if self.skip_upload:
            return

        try:
            tokens = self._format_tokens(us_record)
            if self._should_write(us_record["dateTime"], tokens):
                self._write_line(us_record["dateTime"], tokens)
        except OSError:
            # I/O errors get logged but do not kill the thread — RESTThread
            # restarts us anyway, but losing one record is preferable to a
            # restart loop.
            log.exception("LogToFile: failed to write %s", self.path)

    # ----------------------------------------------------------------------
    # internals
    # ----------------------------------------------------------------------

    def _format_tokens(self, record: dict) -> list[str]:
        """Build the sorted list of ``key:value:label`` tokens for a record."""
        out: list[str] = []
        for key, raw_value in record.items():
            if key in SKIP_KEYS or raw_value is None:
                continue
            token = _format_one(record, key)
            if token is not None:
                out.append(token)
        out.sort()
        return out

    def _should_write(self, ts: float, tokens: list[str]) -> bool:
        """True if this record differs from the cached one OR >60s have passed."""
        if self._last_tokens is None or self._last_ts is None:
            return True
        if ts - self._last_ts > 60.0:
            return True
        return tokens != self._last_tokens

    def _write_line(self, ts: float, tokens: list[str]) -> None:
        self._last_ts = ts
        self._last_tokens = tokens
        line = ",".join([weeutil.weeutil.timestamp_to_string(ts), *tokens])
        with open(self.path, "a") as out:
            out.write(line + "\n")


def _format_one(record: dict, key: str) -> str | None:
    """Format a single record field as ``key:value:label`` (or None to drop)."""
    raw_value_tuple = weewx.units.as_value_tuple(record, key)
    value_helper = weewx.units.ValueHelper(raw_value_tuple)

    label = UNIT_LABEL_ALIAS.get(
        raw_value_tuple[1],
        value_helper.formatter.get_label_string(raw_value_tuple[1]).strip(),
    )

    try:
        value: Any = value_helper.toString(addLabel=False)
    except TypeError:
        # ValueHelper.toString() raises TypeError on non-numeric primitives.
        # Pass-through if the raw value is a string; otherwise drop the field.
        if isinstance(raw_value_tuple[0], str):
            value = raw_value_tuple[0]
        else:
            return None

    field_map = FIELD_MAP.get(key)
    if field_map is not None:
        label = field_map.label
        if field_map.fmt is not None:
            value = field_map.fmt % (raw_value_tuple[0],)

    if label == "" and field_map is None:
        # No unit, no override → field carries no information; drop.
        return None

    return f"{key}:{value}:{label}"
