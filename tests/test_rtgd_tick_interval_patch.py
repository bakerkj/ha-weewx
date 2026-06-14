# Copyright (c) 2026 Kenneth Baker <bakerkj@umich.edu>
# All rights reserved.

"""Regression tests for patches/extensions/0014-rtgd-tick-interval.patch.

A behavioural test that imports the patched rtgd module belongs in the
broader patch-test framework; here we pin the specific change that
shipped in v0.1.17 wrong and was corrected by this PR, so a future
revert (or a stray review-bot suggestion like the one that mangled the
patch in #150) trips the test instead of the production clock.
"""

import pathlib

PATCH = (
    pathlib.Path(__file__).resolve().parent.parent
    / "patches/extensions/0014-rtgd-tick-interval.patch"
)


def test_emit_tick_rounds_ts_to_nearest_second():
    """`_emit_tick` must round `ts` the same way weewx's Vantage driver
    rounds LOOP packets (`int(time.time() + 0.5)`). The original patch
    used `ts = time.time()` and `strftime("%S")` truncated the fractional
    second, colliding with the LOOP write's *rounded* second — the
    resulting `gauge-data.txt` file ticked every 1s on the filesystem
    but its `timeUTC` field only advanced every 2s.
    """
    src = PATCH.read_text()
    assert "ts = int(now + 0.5)" in src, (
        "tick patch must round ts to match LOOP-packet rounding; "
        "raw float time.time() collides with LOOP timeUTC every other write"
    )
    assert "+        ts = time.time()" not in src, (
        "raw float ts assignment was the v0.1.17 bug; do not reintroduce it"
    )


def test_emit_tick_schedules_against_unrounded_wall_clock():
    """`self.last_write` must be set to the *un-rounded* wall clock, not
    to the rounded `ts`. If `last_write = ts` and `ts` rounded *up* (i.e.
    frac(time.time()) >= 0.5), `last_write` is up to 0.5 s in the future.
    The next queue.Empty branch's `(time.time() - self.last_write) >=
    tick_interval` check then underflows and skips, so the *next* tick
    fires 2 s after this one — the same 2 s-clock symptom one layer up
    from the ts-rounding bug fixed by this patch.
    """
    src = PATCH.read_text()
    assert "+        self.last_write = now" in src, (
        "last_write must capture the un-rounded wall clock so the "
        "tick-interval scheduler doesn't underflow when ts rounds up"
    )
    assert "+        self.last_write = ts" not in src, (
        "setting last_write to the rounded ts schedules the next tick "
        "from a future timestamp and reintroduces the 2 s-clock bug"
    )
