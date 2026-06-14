# Copyright (c) 2026 Kenneth Baker <bakerkj@umich.edu>
# All rights reserved.

"""Behavioural regression test for
patches/extensions/0011-rtgd-history-max-none-guard.patch.

When no wind packets have landed in the last 10 minutes (intermittent SDR
reception, offline driver, startup race), ``Buffer['windGust'].history_max(ts,
age=600)`` returns ``None``. Upstream calls ``.value`` on the result
unconditionally and crashes with::

    AttributeError: 'NoneType' object has no attribute 'value'

The patch guards with ``_h.value if _h is not None else 0.0``.

Driving the full ``calculate()`` requires deep setup, so we exec the
patched wgust slice from the live ``calculate`` source against a
controlled ``self`` and ``packet`` --- exercising the *actual* patched
lines, not a re-typed copy.
"""

import importlib
import inspect
import sys
import textwrap
from unittest.mock import Mock


def _wgust_slice():
    sys.modules.pop("rtgd", None)
    rtgd = importlib.import_module("rtgd")
    src = inspect.getsource(rtgd.RealtimeGaugeDataThread.calculate)
    body_start = src.index("# wgust - 10 minute high gust")
    line_start = src.rfind("\n", 0, body_start) + 1
    end = src.index("#        # avgbearing", line_start)
    return rtgd, textwrap.dedent(src[line_start:end])


def test_history_max_none_does_not_crash_wgust():
    rtgd, body = _wgust_slice()
    self_mock = Mock()
    # buffer must contain 'windGust' to hit the patched branch.
    self_mock.buffer = {"windGust": Mock()}
    self_mock.buffer["windGust"].history_max = Mock(return_value=None)
    self_mock.packet_unit_dict = {
        "windSpeed": {"units": "km_per_hour", "group": "group_speed"}
    }
    self_mock.wind_group = "km_per_hour"
    self_mock.wind_format = "%.1f"
    data = {}
    ts = 1_700_000_000
    g = dict(vars(rtgd))
    g.update({"self": self_mock, "data": data, "ts": ts})
    exec(body, g)
    # No AttributeError --- and we get the 0.0 fallback formatted.
    assert data["wgust"] == "0.0", (
        "patched wgust branch must fall back to 0.0 when history_max returns "
        "None; unpatched code raises AttributeError on .value and kills the "
        "rtgd thread on every LOOP packet"
    )


def test_history_max_none_does_not_crash_windspeed_fallback():
    rtgd, body = _wgust_slice()
    self_mock = Mock()
    # No windGust in buffer; falls through to windSpeed.
    self_mock.buffer = {"windSpeed": Mock()}
    self_mock.buffer["windSpeed"].history_max = Mock(return_value=None)
    self_mock.packet_unit_dict = {
        "windSpeed": {"units": "km_per_hour", "group": "group_speed"}
    }
    self_mock.wind_group = "km_per_hour"
    self_mock.wind_format = "%.1f"
    data = {}
    ts = 1_700_000_000
    g = dict(vars(rtgd))
    g.update({"self": self_mock, "data": data, "ts": ts})
    exec(body, g)
    assert data["wgust"] == "0.0"
