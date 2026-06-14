# Copyright (c) 2026 Kenneth Baker <bakerkj@umich.edu>
# All rights reserved.

"""Behavioural regression test for
patches/extensions/0006-emoncms-skip-upload-abortedpost.patch.

Without the patch, ``EmonCMSThread.process_record`` returns silently when
``skip_upload`` is set and the base RESTThread loop falsely logs
"Published record". The patch raises ``weewx.restx.AbortedPost`` instead,
so the loop logs "Skipped record" and the operator never sees a phantom
success.
"""

import importlib
import queue
import sys

import pytest
import weewx.restx


def test_skip_upload_raises_abortedpost():
    sys.modules.pop("emoncms", None)
    emoncms = importlib.import_module("emoncms")

    t = emoncms.EmonCMSThread(
        queue=queue.Queue(),
        token="x",
        skip_upload=True,
        manager_dict=None,
    )
    with pytest.raises(weewx.restx.AbortedPost):
        t.process_record({"dateTime": 1000, "usUnits": 1}, dbm=None)
