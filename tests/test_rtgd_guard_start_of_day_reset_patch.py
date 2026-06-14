# Copyright (c) 2026 Kenneth Baker <bakerkj@umich.edu>
# All rights reserved.

"""Behavioural regression test for
patches/extensions/0007-rtgd-guard-start-of-day-reset.patch.

rtgd's ``Buffer.start_of_day_reset()`` iterates the static manifest and
resets every obs. The buffer only contains obs the station actually reports,
so a missing manifest entry (e.g. ``humidex`` without StdWXCalculate)
raises ``KeyError`` at the first midnight rollover and the rtgd worker
thread exits, freezing ``gauge-data.txt`` until restart.

The patched code guards with ``if obs in self``.
"""

import importlib
import sys
from unittest.mock import Mock


def test_start_of_day_reset_skips_missing_obs():
    sys.modules.pop("rtgd", None)
    rtgd = importlib.import_module("rtgd")

    buf = dict.__new__(rtgd.Buffer)
    # Hand-build the dict; bypass __init__ which wants real day_stats.
    dict.__init__(buf)
    # Manifest references one obs we provide and one we don't, mimicking
    # the production "humidex declared but never observed" scenario.
    buf.manifest = ["outTemp", "humidex"]
    buf["outTemp"] = Mock()

    # Must not raise even though 'humidex' is in the manifest but not the dict.
    buf.start_of_day_reset()
    assert buf["outTemp"].day_reset.call_count == 1
