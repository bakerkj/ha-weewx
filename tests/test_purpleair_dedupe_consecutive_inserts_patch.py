# Copyright (c) 2026 Kenneth Baker <bakerkj@umich.edu>
# All rights reserved.

"""Regression tests for patches/extensions/0003-purpleair-dedupe-consecutive-inserts.patch.

PurpleAirMonitor.new_archive_record() runs on every NEW_ARCHIVE_RECORD
event (e.g. every 60 s), but the background data thread only refreshes
the cached record every ``interval`` seconds (default 300). Between
refreshes the same record is re-inserted with the same dateTime, producing
``UNIQUE constraint failed: archive.dateTime`` errors. The fix tracks the
last successfully-inserted dateTime and short-circuits duplicates.
"""

import pathlib

PATCH = (
    pathlib.Path(__file__).resolve().parent.parent
    / "patches/extensions/0003-purpleair-dedupe-consecutive-inserts.patch"
)


def test_save_data_skips_duplicate_datetime():
    """``save_data`` must compare ``record['dateTime']`` against the cached
    ``_last_inserted_ts`` and return without calling ``addRecord`` on a hit.
    Without this guard, every NEW_ARCHIVE_RECORD event between refreshes
    re-inserts the stale row and the DB rejects it with a UNIQUE violation.
    """
    src = PATCH.read_text()
    assert (
        "if record['dateTime'] == getattr(self, '_last_inserted_ts', None):" in src
    ), (
        "save_data must skip when record['dateTime'] equals the cached "
        "_last_inserted_ts; otherwise duplicate inserts hit UNIQUE archive.dateTime"
    )


def test_save_data_records_inserted_datetime():
    """After ``addRecord`` succeeds, the new dateTime must be cached on
    ``self._last_inserted_ts`` so the *next* call can short-circuit. Without
    this write, the dedupe guard above never matches and the bug persists.
    """
    src = PATCH.read_text()
    assert "self._last_inserted_ts = record['dateTime']" in src, (
        "save_data must record the inserted dateTime; without this write "
        "the dedupe guard above can never match"
    )
