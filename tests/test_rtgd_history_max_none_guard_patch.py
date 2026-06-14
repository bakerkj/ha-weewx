# Copyright (c) 2026 Kenneth Baker <bakerkj@umich.edu>
# All rights reserved.

"""Regression tests for patches/extensions/0011-rtgd-history-max-none-guard.patch.

rtgd's ``calculate()`` reads ``self.buffer['windGust'].history_max(ts,
age=600).value``. When no wind packets have landed in the last 10 minutes
(intermittent SDR reception, offline drivers, startup race), ``history_max``
returns None and the bare ``.value`` crashes with AttributeError. The crash
recurs once per LOOP packet until conditions recover, taking down the rtgd
thread and freezing gauge-data.txt. The same fix applies to the windSpeed
fallback path.
"""

import pathlib

PATCH = (
    pathlib.Path(__file__).resolve().parent.parent
    / "patches/extensions/0011-rtgd-history-max-none-guard.patch"
)


def test_windgust_history_max_none_falls_back_to_zero():
    """The windGust branch must capture ``history_max(...)`` into a local,
    check for None, and substitute 0.0 — never blindly take ``.value`` on a
    possibly-None return. The bare ``.value`` is what crashes the thread.
    """
    src = PATCH.read_text()
    assert "_h = self.buffer['windGust'].history_max(ts, age=600)" in src, (
        "windGust branch must capture history_max into a local for the "
        "None check to work; chained .value is the bug"
    )
    assert "wgust = _h.value if _h is not None else 0.0" in src, (
        "windGust branch must fall back to 0.0 when history_max returns None"
    )
    assert (
        "-            wgust = self.buffer['windGust'].history_max(ts, age=600).value"
        in src
    ), "patch must remove the unguarded chained .value that crashed the thread"


def test_windspeed_fallback_also_guarded():
    """The windSpeed fallback branch has the same None-return hazard and
    must be guarded identically; otherwise the bug just relocates to
    stations that report windSpeed without windGust.
    """
    src = PATCH.read_text()
    assert "_h = self.buffer['windSpeed'].history_max(ts, age=600)" in src, (
        "windSpeed fallback must also capture history_max into a local"
    )
    assert (
        "-            wgust = self.buffer['windSpeed'].history_max(ts, age=600).value"
        in src
    ), "patch must remove the unguarded windSpeed .value access"
