# Copyright (c) 2026 Kenneth Baker <bakerkj@umich.edu>
# All rights reserved.

"""Regression tests for patches/extensions/0009-rtldavis-python313-rstrings.patch.

The remaining ``re.compile()`` arguments in rtldavis.py contain unrecognised
escape sequences inside non-raw strings; Python 3.12+ emits a SyntaxWarning
for each on import, and we run Python 3.13. Convert to raw strings so the
warnings disappear at weewxd start. (DATAPacket.IDENTIFIER's r-prefix
lands in 0008-rtldavis-low-battery-regex.patch.)
"""

import pathlib

PATCH = (
    pathlib.Path(__file__).resolve().parent.parent
    / "patches/extensions/0009-rtldavis-python313-rstrings.patch"
)


def test_datapacket_pattern_uses_raw_string():
    """``DATAPacket.PATTERN`` must be a raw string so Python 3.13 does not
    SyntaxWarning on the ``\\d`` escapes at every weewxd start.
    """
    src = PATCH.read_text()
    assert "+    PATTERN = re.compile(r'([0-9A-F]{2})" in src, (
        "DATAPacket.PATTERN must use the r-prefix; non-raw form triggers "
        "SyntaxWarning on Python 3.13 for every \\d escape"
    )


def test_channelpacket_regexes_use_raw_string():
    """All three ``CHANNELPacket`` regexes (``IDENTIFIER``, ``PATTERNv13``,
    ``PATTERNv12``) must be raw strings — same Python 3.13 SyntaxWarning
    rationale as ``DATAPacket.PATTERN``.
    """
    src = PATCH.read_text()
    assert '+    IDENTIFIER = re.compile(r"ChannelIdx:")' in src, (
        "CHANNELPacket.IDENTIFIER must use the r-prefix"
    )
    assert "+    PATTERNv13 = re.compile(r'ChannelIdx:" in src, (
        "CHANNELPacket.PATTERNv13 must use the r-prefix"
    )
    assert "+    PATTERNv12 = re.compile(r'ChannelIdx:" in src, (
        "CHANNELPacket.PATTERNv12 must use the r-prefix"
    )
