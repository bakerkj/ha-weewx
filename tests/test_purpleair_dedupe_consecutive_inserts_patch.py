# Copyright (c) 2026 Kenneth Baker <bakerkj@umich.edu>
# All rights reserved.

"""Behavioural regression test for
patches/extensions/0003-purpleair-dedupe-consecutive-inserts.patch.

``PurpleAirMonitor.save_data`` is called from ``new_archive_record`` (every
~60 s) but the background data thread only refreshes the cached record every
``interval`` seconds (default 300). Without dedupe, the same row is inserted
multiple times producing ``UNIQUE constraint failed: archive.dateTime``.
The patch caches the last inserted ``dateTime`` and skips duplicates.
"""

import importlib
import sys
from unittest.mock import Mock


def _new_monitor():
    sys.modules.pop("purpleair", None)
    purpleair = importlib.import_module("purpleair")
    inst = object.__new__(purpleair.PurpleAirMonitor)
    inst.dbm = Mock()
    return inst


def test_save_data_skips_duplicate_then_admits_new_datetime():
    inst = _new_monitor()
    inst.save_data({"dateTime": 1000})
    inst.save_data({"dateTime": 1000})  # duplicate -> must be skipped
    assert inst.dbm.addRecord.call_count == 1, (
        "save_data must skip a duplicate dateTime so the DB never sees a "
        "UNIQUE-archive.dateTime violation"
    )
    inst.save_data({"dateTime": 2000})  # new ts -> must go through
    assert inst.dbm.addRecord.call_count == 2
    assert inst._last_inserted_ts == 2000
