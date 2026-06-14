# Copyright (c) 2026 Kenneth Baker <bakerkj@umich.edu>
# All rights reserved.

"""Behavioural regression test for
patches/extensions/0002-rtgd-verbose-thread-traceback.patch.

The loop-packet ``except`` inside ``RealtimeGaugeDataThread.run`` upstream
ships the traceback to ``log.debug`` — under the addon's default logger
level it never appears, so an offending KeyError key stays hidden until
you bump global verbosity. The patch promotes that one call to
``log.critical``.

We assert on the patched method's *runtime source* (so a future revert is
caught here, not in production), then exercise the patched line by
executing it in the module's globals with a stubbed ``log_traceback``.
"""

import importlib
import inspect
import sys


def test_loop_packet_traceback_logs_at_critical(monkeypatch):
    sys.modules.pop("rtgd", None)
    rtgd = importlib.import_module("rtgd")

    run_src = inspect.getsource(rtgd.RealtimeGaugeDataThread.run)
    # Isolate the loop-packet except block so we don't accidentally
    # match the outer except (which intentionally still uses log.debug).
    loop_start = run_src.index("elif _package['type'] == 'loop':")
    loop_end = run_src.index("# if packets have backed up", loop_start)
    loop_block = run_src[loop_start:loop_end]

    assert (
        "weeutil.logger.log_traceback(log.critical, 'rtgdthread: **** ')" in loop_block
    ), (
        "loop-packet except block must call log_traceback with log.critical "
        "so a KeyError stack reaches production logs without a global "
        "logger-level bump"
    )
    assert (
        "weeutil.logger.log_traceback(log.debug, 'rtgdthread: **** ')" not in loop_block
    ), (
        "loop-packet except block must NOT log the traceback at debug; "
        "that was the bug — the stack stays hidden at production log levels"
    )

    # Actually run the patched call (in module globals) to prove the line
    # is wired to the expected logger method, not just visually correct.
    captured = {}

    def fake_log_traceback(level_func, prefix):
        captured["level"] = level_func
        captured["prefix"] = prefix

    monkeypatch.setattr(rtgd.weeutil.logger, "log_traceback", fake_log_traceback)
    exec_globals = dict(vars(rtgd))
    exec(
        "weeutil.logger.log_traceback(log.critical, 'rtgdthread: **** ')",
        exec_globals,
    )
    assert captured["level"] == rtgd.log.critical
    assert captured["prefix"] == "rtgdthread: **** "
