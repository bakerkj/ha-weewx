# Copyright (c) 2026 Kenneth Baker <bakerkj@umich.edu>
# All rights reserved.

"""Behavioural regression test for
patches/extensions/0001-previmeteo-py3-queue-shim.patch.

The upstream previmeteo module does a bare ``import Queue`` (Python 2 only).
Our patch wraps it in a ``try/except ImportError`` falling back to
``import queue as Queue``. Without the shim, importing previmeteo crashes
weewxd at startup with ``ModuleNotFoundError: No module named 'Queue'``.
"""

import importlib
import sys


def test_previmeteo_imports_under_py3_and_queue_resolves_to_stdlib():
    sys.modules.pop("previmeteo", None)
    previmeteo = importlib.import_module("previmeteo")
    # The patched module exposes ``Queue`` as an alias for the stdlib
    # ``queue`` module on Python 3.
    import queue as stdlib_queue

    assert previmeteo.Queue is stdlib_queue, (
        "patched previmeteo must alias the stdlib `queue` module under "
        "the `Queue` name; bare Py2 `import Queue` crashes Py3 weewxd"
    )
    # And the constructor we depend on must be reachable.
    q = previmeteo.Queue.Queue()
    q.put("x")
    assert q.get() == "x"
