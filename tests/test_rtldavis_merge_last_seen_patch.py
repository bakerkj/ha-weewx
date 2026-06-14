# Copyright (c) 2026 Kenneth Baker <bakerkj@umich.edu>
# All rights reserved.

"""Regression tests for patches/extensions/0012-rtldavis-merge-last-seen.patch.

The Davis ISS over-the-air protocol rotates through sensor types: a single
8-byte message carries one of {temperature, humidity, wind, rain, solar,
UV, ...} at a time, and the driver's ``_data_to_packet`` emits a LOOP
packet containing only that sensor. ``StdWXCalculate`` then can't compute
dewpoint/cloudbase/heatindex/windchill because it sees a packet with
outTemp but no outHumidity (or vice versa), and gauge-data.txt shows
dew=0.0, cloudbasevalue=0.0, apptemp=0.0 indefinitely. Cache the last-
seen value per gauge field and merge into every LOOP packet. ``rain`` is
excluded — it's an incremental delta, re-emitting it double-counts tips.
"""

import pathlib

PATCH = (
    pathlib.Path(__file__).resolve().parent.parent
    / "patches/extensions/0012-rtldavis-merge-last-seen.patch"
)


def test_last_seen_cache_initialized_and_updated():
    """The driver must lazily allocate ``self._last_seen`` and update it
    from each LOOP packet's non-None fields. Without the cache, every
    LOOP packet only carries the rotating sensor type and StdWXCalculate
    cannot compute derived values.
    """
    src = PATCH.read_text()
    assert "if not hasattr(self, '_last_seen'):" in src, (
        "driver must lazily initialise self._last_seen so the cache "
        "survives across calls without an __init__ change"
    )
    assert "self._last_seen[k] = v" in src, (
        "cache must be updated from each LOOP packet's non-None fields"
    )


def test_last_seen_merge_skips_rain():
    """Cached values must be merged into each LOOP via ``packet.setdefault``
    so a freshly-sampled field is preserved. ``rain`` must be excluded
    from the cache — it is an incremental delta per packet, and re-emitting
    the last-seen value double-counts tips.
    """
    src = PATCH.read_text()
    assert "packet.setdefault(k, v)" in src, (
        "cached values must merge via setdefault so fresh samples win"
    )
    assert "if v is not None and k not in ('rain',):" in src, (
        "rain must be excluded from the cache; it is an incremental "
        "delta and re-emitting it double-counts tips"
    )
