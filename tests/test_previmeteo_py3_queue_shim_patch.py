# Copyright (c) 2026 Kenneth Baker <bakerkj@umich.edu>
# All rights reserved.

"""Regression tests for patches/extensions/0001-previmeteo-py3-queue-shim.patch.

previmeteo (previmeteo/weewx-previmeteo v0.1) imports ``Queue``
unconditionally, which only exists on Python 2. The addon runs Python 3,
so without this shim weewxd dies at import time with ``ModuleNotFoundError:
No module named 'Queue'``. Pin both halves of the try/except so a future
revert tripping the import is caught here, not in production.
"""

import pathlib

PATCH = (
    pathlib.Path(__file__).resolve().parent.parent
    / "patches/extensions/0001-previmeteo-py3-queue-shim.patch"
)


def test_queue_import_is_py3_shimmed():
    """The bare ``import Queue`` must be wrapped in a try/except that falls
    back to the Python 3 ``queue`` module under the ``Queue`` alias. Without
    the fallback, weewxd crashes at import time with ``ModuleNotFoundError``
    on every start (we ship Python 3.13).
    """
    src = PATCH.read_text()
    assert (
        "try:\n+    import Queue\n+except ImportError:\n+    import queue as Queue"
        in src
    ), (
        "previmeteo must guard `import Queue` with a Py3 fallback to "
        "`import queue as Queue`; bare Py2 import crashes weewxd"
    )
    assert "-import Queue" in src, (
        "patch must remove the unconditional Py2 `import Queue` line"
    )
