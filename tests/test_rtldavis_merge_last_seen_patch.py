# Copyright (c) 2026 Kenneth Baker <bakerkj@umich.edu>
# All rights reserved.

"""Behavioural regression test for
patches/extensions/0012-rtldavis-merge-last-seen.patch.

The Davis ISS over-the-air protocol rotates through sensor types: each
8-byte message carries one of {temperature, humidity, wind, rain, solar, ...}.
Without the patch ``_data_to_packet`` emits a LOOP packet with only the
sensor present in that message, and StdWXCalculate cannot compute derived
values (dewpoint, cloudbase, etc.). The patch caches the last-seen value
per gauge field and merges cached values into every LOOP packet. ``rain`` is
excluded because it is an incremental delta.
"""

import importlib
import sys


def _make_driver():
    sys.modules.pop("rtldavis", None)
    rtl = importlib.import_module("rtldavis")
    drv = object.__new__(rtl.RtldavisDriver)
    drv.last_rain_count = None
    drv.rain_per_tip = 0.01
    drv.sensor_map = dict(rtl.RtldavisDriver.DEFAULT_SENSOR_MAP)
    return drv


def test_last_seen_merges_across_packets_and_excludes_rain():
    drv = _make_driver()

    # First packet carries only outTemp.
    p1 = drv._data_to_packet({"temperature": 20.0})
    assert p1["outTemp"] == 20.0
    assert "outHumidity" not in p1

    # Second packet carries only outHumidity (no temperature key) but the
    # merge step must surface the cached outTemp into this packet.
    p2 = drv._data_to_packet({"humidity": 60.0})
    assert p2["outHumidity"] == 60.0
    assert p2["outTemp"] == 20.0, (
        "patched _data_to_packet must merge last-seen non-rain fields into "
        "every LOOP packet so StdWXCalculate sees both outTemp and "
        "outHumidity together"
    )

    # Rain delta must NOT carry across — re-emitting double-counts tips.
    p3 = drv._data_to_packet({"rain_count": 5})
    assert "rain" in p3
    p4 = drv._data_to_packet({"temperature": 21.0})
    assert "rain" not in p4, (
        "rain is an incremental delta; the merge step must skip it so a "
        "subsequent packet without rain_count does not double-count tips"
    )
