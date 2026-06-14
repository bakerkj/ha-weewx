# Copyright (c) 2026 Kenneth Baker <bakerkj@umich.edu>
# All rights reserved.

"""Regression tests for patches/extensions/0005-previmeteo-qualify-get-site-dict.patch.

previmeteo (previmeteo/weewx-previmeteo v0.1) calls bare ``get_site_dict(...)``,
which is undefined on WeeWX 5 (it lives in ``weewx.restx``). Without
qualification the service crashes weewxd with ``NameError`` at import time.
Qualify the call so the service loads.
"""

import pathlib

PATCH = (
    pathlib.Path(__file__).resolve().parent.parent
    / "patches/extensions/0005-previmeteo-qualify-get-site-dict.patch"
)


def test_get_site_dict_is_qualified():
    """``get_site_dict`` must be called as ``weewx.restx.get_site_dict``
    because the unqualified name is not exported in WeeWX 5; leaving it
    bare raises ``NameError`` at service init and crashes weewxd.
    """
    src = PATCH.read_text()
    assert "weewx.restx.get_site_dict(" in src, (
        "previmeteo must call weewx.restx.get_site_dict(...) explicitly; "
        "bare get_site_dict is undefined on WeeWX 5"
    )
    assert "-        _ambient_dict = get_site_dict(" in src, (
        "patch must remove the unqualified call site"
    )
