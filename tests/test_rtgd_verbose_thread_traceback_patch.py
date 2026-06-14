# Copyright (c) 2026 Kenneth Baker <bakerkj@umich.edu>
# All rights reserved.

"""Regression tests for patches/extensions/0002-rtgd-verbose-thread-traceback.patch.

rtgd's worker-thread top-level except clause logs the exception *type* at
CRITICAL but sends the traceback to ``log.debug``, hiding the actual KeyError
key (or other failure detail) unless the whole addon logger is bumped to
debug. Promote that one ``log_traceback`` call to ``log.critical`` so the
stack shows up in the addon log without raising global verbosity.
"""

import pathlib

PATCH = (
    pathlib.Path(__file__).resolve().parent.parent
    / "patches/extensions/0002-rtgd-verbose-thread-traceback.patch"
)


def test_thread_traceback_logged_at_critical():
    """The rtgd worker-thread crash traceback must be emitted via
    ``log.critical`` so the offending key/value shows up in production logs.
    Sending it to ``log.debug`` (the upstream default) hides the trace
    behind a logger level we don't run in production.
    """
    src = PATCH.read_text()
    assert "log_traceback(log.critical, 'rtgdthread: **** ')" in src, (
        "thread-exit traceback must go to log.critical so the failing key "
        "surfaces in the addon log without bumping global log level"
    )
    assert (
        "-                                weeutil.logger.log_traceback(log.debug" in src
    ), (
        "patch must remove the upstream log.debug call for the thread-exit "
        "traceback; otherwise the stack is invisible at production log levels"
    )
