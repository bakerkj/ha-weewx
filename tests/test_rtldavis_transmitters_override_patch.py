# Copyright (c) 2026 Kenneth Baker <bakerkj@umich.edu>
# All rights reserved.

"""Behavioural regression test for
patches/extensions/0010-rtldavis-transmitters-override.patch.

The patched driver lets ``[Rtldavis] transmitters_override`` set the raw
``-tr`` bitmask directly, bypassing the slot-derived value built from 5
named channels. Bad integer values are logged and skipped, leaving the
computed default in place.
"""

import importlib
import sys
from unittest.mock import Mock, patch


def _build_stn_dict(override):
    d = {
        "iss_channel": 1,
        "anemometer_channel": 0,
        "leaf_soil_channel": 0,
        "temp_hum_1_channel": 0,
        "temp_hum_2_channel": 0,
    }
    if override is not None:
        d["transmitters_override"] = override
    return d


def _build_driver(stn_dict_override):
    sys.modules.pop("rtldavis", None)
    rtl = importlib.import_module("rtldavis")
    cfg = {"Rtldavis": _build_stn_dict(stn_dict_override)}
    # Block the real ProcManager (would fork rtldavis), and skip the
    # NEW_ARCHIVE_RECORD bind (we pass engine=None anyway).
    with patch.object(rtl, "ProcManager", lambda *a, **kw: Mock()):
        drv = rtl.RtldavisDriver(engine=None, config_dict=cfg)
    return drv


def test_transmitters_override_sets_raw_bitmask():
    drv = _build_driver("255")
    assert drv.transmitters == 255, (
        "transmitters_override='255' must set the bitmask directly, "
        "bypassing the 5-slot channel computation"
    )
    assert drv.tr_count == 8, (
        "successful override must recompute tr_count from the new bitmask"
    )


def test_transmitters_override_invalid_is_ignored():
    # iss_channel=1 → computed bitmask = 1<<0 = 1.
    drv = _build_driver("not-an-int")
    assert drv.transmitters == 1, (
        "invalid transmitters_override must be logged and skipped, leaving "
        "the slot-derived bitmask intact (not crash driver init)"
    )


def test_transmitters_override_absent_uses_computed():
    drv = _build_driver(None)
    assert drv.transmitters == 1, (
        "absent transmitters_override must leave the slot-derived bitmask"
    )
