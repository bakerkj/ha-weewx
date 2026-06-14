# Copyright (c) 2026 Kenneth Baker <bakerkj@umich.edu>
# All rights reserved.

"""Regression tests for patches/extensions/0010-rtldavis-transmitters-override.patch.

Allow ``[Rtldavis] transmitters_override`` in weewx.conf to set the raw
``-tr`` bitmask directly. The driver builds ``-tr`` from 5 named slots
(iss/anemometer/leaf_soil/temp_hum_1/temp_hum_2), capping coverage at 5
of 8 transmitter IDs; diagnostic scans want the full 0xFF. Bad config
must be logged and ignored, leaving the computed value in place.
"""

import pathlib

PATCH = (
    pathlib.Path(__file__).resolve().parent.parent
    / "patches/extensions/0010-rtldavis-transmitters-override.patch"
)


def test_override_read_from_stn_dict():
    """The driver must pull ``transmitters_override`` from ``stn_dict`` so
    a [Rtldavis] config knob can replace the slot-derived bitmask without
    editing code. Falsy/empty values must fall through to the computed value.
    """
    src = PATCH.read_text()
    assert "stn_dict.get('transmitters_override')" in src, (
        "driver must read transmitters_override from stn_dict so a "
        "weewx.conf override actually reaches the bitmask"
    )
    assert "if _ov is not None and str(_ov).strip():" in src, (
        "override must be skipped when missing/blank so the slot-derived "
        "default still applies"
    )


def test_override_logs_and_skips_bad_int():
    """A non-integer override must be logged via ``logerr`` and skipped,
    *not* propagated as a ValueError that crashes the driver init. The
    successful path also recomputes ``tr_count`` via ``bin(...).count('1')``
    so downstream logging stays consistent.
    """
    src = PATCH.read_text()
    assert "except ValueError:" in src, (
        "bad-int override must hit a ValueError branch, not crash driver init"
    )
    assert "transmitters_override=%r is not a " in src, (
        "bad-int branch must log via logerr with the offending value"
    )
    assert "self.tr_count = bin(self.transmitters).count('1')" in src, (
        "successful override must recompute tr_count from the new bitmask"
    )
