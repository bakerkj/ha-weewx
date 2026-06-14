# Copyright (c) 2026 Kenneth Baker <bakerkj@umich.edu>
# All rights reserved.

"""Regression tests for patches/extensions/0007-rtgd-guard-start-of-day-reset.patch.

rtgd's ``Buffer.start_of_day_reset()`` iterates the static MANIFEST and
calls ``self[obs].day_reset()`` for every entry. The Buffer (a dict) is
only populated with obs that actually arrive in loop packets, so a station
that doesn't report a manifest obs (e.g. ``humidex`` when StdWXCalculate is
not computing it) raises ``KeyError`` at the first midnight rollover and
the rtgd worker thread exits, freezing ``gauge-data.txt`` until restart.
"""

import pathlib

PATCH = (
    pathlib.Path(__file__).resolve().parent.parent
    / "patches/extensions/0007-rtgd-guard-start-of-day-reset.patch"
)


def test_start_of_day_reset_guards_missing_obs():
    """``start_of_day_reset`` must guard ``self[obs].day_reset()`` with
    ``if obs in self``. Without the guard, the first midnight rollover after
    boot raises KeyError for any MANIFEST obs the station doesn't report,
    killing the rtgd thread and freezing gauge-data.txt.
    """
    src = PATCH.read_text()
    assert (
        "+            if obs in self:\n+                self[obs].day_reset()" in src
    ), (
        "start_of_day_reset must skip obs not in the Buffer dict; "
        "otherwise the first midnight rollover kills the rtgd thread"
    )
    assert "-            self[obs].day_reset()" in src, (
        "patch must remove the unguarded self[obs].day_reset() call"
    )
