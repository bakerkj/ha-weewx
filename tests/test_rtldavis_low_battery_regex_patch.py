# Copyright (c) 2026 Kenneth Baker <bakerkj@umich.edu>
# All rights reserved.

"""Regression tests for patches/extensions/0008-rtldavis-low-battery-regex.patch.

``DATAPacket.IDENTIFIER`` restricted the second hex nibble to ``[0-7]``,
which is the encoding for a normal-battery ISS transmitter. When the
battery goes low the high bit is set and the nibble lands in ``8-F``; the
regex then stops matching and the driver silently drops every packet
after the battery starts to die. Upstream issue
lheijst/weewx-rtldavis#20.
"""

import pathlib

PATCH = (
    pathlib.Path(__file__).resolve().parent.parent
    / "patches/extensions/0008-rtldavis-low-battery-regex.patch"
)


def test_identifier_accepts_all_hex_nibbles():
    """The DATA packet identifier regex must accept every hex nibble in the
    16-character payload (``[0-9A-F]{16}``). Restricting the second nibble
    to ``[0-7]`` (the upstream form) silently drops every packet from a
    transmitter once its battery starts to die.
    """
    src = PATCH.read_text()
    assert (
        r'+    IDENTIFIER = re.compile(r"^\d\d:\d\d:\d\d\.[\d]{6} [0-9A-F]{16}")' in src
    ), (
        "DATAPacket.IDENTIFIER must accept the full hex range so low-battery "
        "packets (high bit set in the second nibble) still match"
    )
    assert (
        r'-    IDENTIFIER = re.compile("^\d\d:\d\d:\d\d.[\d]{6} [0-9A-F][0-7][0-9A-F]{14}")'
        in src
    ), (
        "patch must explicitly delete the upstream [0-7]-restricted regex; "
        "leaving it in place silently drops every packet once the battery goes low"
    )
