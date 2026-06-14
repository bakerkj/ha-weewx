# Copyright (c) 2026 Kenneth Baker <bakerkj@umich.edu>
# All rights reserved.

"""Behavioural regression test for
patches/extensions/0008-rtldavis-low-battery-regex.patch.

``DATAPacket.IDENTIFIER`` upstream restricts the second hex nibble to 0-7
(normal-battery encoding). When the battery goes low the high bit is set
and the nibble lands in 8-F, so the regex stops matching and the driver
silently drops every packet. The patched regex accepts any 16-hex-char
payload (and adds proper escaping for the decimal point).
"""

import importlib
import sys


def test_identifier_matches_normal_and_low_battery_payloads():
    sys.modules.pop("rtldavis", None)
    rtl = importlib.import_module("rtldavis")
    rx = rtl.DATAPacket.IDENTIFIER

    # Normal-battery payload (second hex char 0-7) — must still match.
    assert rx.match("12:34:56.789012 50FF11223344556677") is not None, (
        "patched regex must still accept normal-battery payloads (2nd nibble 0-7)"
    )
    # Low-battery payload (second hex char 8-F) — bug fix: must NOW match.
    # The upstream regex restricts position 1 to ``[0-7]`` and silently
    # drops everything from that transmitter once the battery goes low.
    assert rx.match("12:34:56.789012 58FF11223344556677") is not None, (
        "patched regex must accept low-battery payloads (2nd nibble 8-F); "
        "the unpatched regex restricts position 1 to [0-7] and drops every "
        "packet once the battery goes low, taking the driver silently dark"
    )
    # Length mismatch should still fail — guards against an over-broad relax.
    assert rx.match("12:34:56.789012 58FF1122334455") is None, (
        "regex must still reject short payloads (length check intact)"
    )
