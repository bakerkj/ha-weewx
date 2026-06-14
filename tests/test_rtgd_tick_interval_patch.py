# Copyright (c) 2026 Kenneth Baker <bakerkj@umich.edu>
# All rights reserved.

"""Behavioural regression test for
patches/extensions/0014-rtgd-tick-interval.patch.

``_emit_tick`` is the synthetic-write path that advances ``dateTime`` in
gauge-data.txt when no LOOP packet has landed. The patch:

1. Rounds the dateTime sent to ``calculate()`` with ``int(now + 0.5)`` so
   it matches the LOOP-packet rounding (Vantage uses ``int(time.time() +
   0.5)``). Without this, the strftime("%S") in calculate() truncates the
   fractional second and the displayed clock ticks 2 s at a time.
2. Stores ``self.last_write = now`` (un-rounded), NOT ``= ts``. If
   ``last_write`` is rounded up by 0.5 s, the next
   ``(time.time() - self.last_write) >= tick_interval`` check underflows
   and skips a tick --- same 2 s symptom one layer up.
"""

import importlib
import sys
from unittest.mock import Mock


def test_emit_tick_rounds_datetime_and_stores_unrounded_last_write(monkeypatch):
    sys.modules.pop("rtgd", None)
    rtgd = importlib.import_module("rtgd")

    thr = object.__new__(rtgd.RealtimeGaugeDataThread)
    cached_packet = {"dateTime": 0}  # placeholder; overwritten on write_data side
    calculate = Mock(return_value={"some": "data"})
    write_data = Mock()
    get_lost_contact = Mock(return_value=False)
    thr.packet_cache = Mock()
    thr.packet_cache.get_packet = Mock(return_value=cached_packet)
    thr.max_cache_age = 600
    thr.calculate = calculate
    thr.write_data = write_data
    thr.get_lost_contact = get_lost_contact
    thr.exporter = None
    thr.last_write = 0

    # frac > 0.5 so int(now+0.5) rounds *up* — the asymmetry the patch addresses.
    now = 1234567890.7
    monkeypatch.setattr(rtgd.time, "time", lambda: now)

    thr._emit_tick()

    # 1. calculate received a packet whose dateTime is the rounded second.
    assert calculate.call_count == 1
    arg_packet = calculate.call_args[0][0]
    assert arg_packet is cached_packet
    # _emit_tick is responsible for setting dateTime via get_packet — verify
    # it asked for the *rounded* ts.
    get_packet_args = thr.packet_cache.get_packet.call_args[0]
    assert get_packet_args[0] == int(now + 0.5), (
        "ts passed to get_packet must round to the nearest integer second so "
        'calculate()\'s strftime("%%S") matches LOOP-packet rounding'
    )

    # 2. last_write stays on the un-rounded wall clock; otherwise the next
    # tick scheduler under-counts the elapsed interval and skips a tick.
    assert thr.last_write == now, (
        "self.last_write must be the un-rounded float time.time(); using the "
        "rounded ts schedules the next tick from a future timestamp and "
        "re-introduces the 2 s-clock bug at the scheduler layer"
    )

    write_data.assert_called_once_with({"some": "data"})
