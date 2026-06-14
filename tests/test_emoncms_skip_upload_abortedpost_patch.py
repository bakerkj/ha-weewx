# Copyright (c) 2026 Kenneth Baker <bakerkj@umich.edu>
# All rights reserved.

"""Regression tests for patches/extensions/0006-emoncms-skip-upload-abortedpost.patch.

emoncms (matthewwall/weewx-emoncms 7c04113) ``process_record`` returns
silently when ``skip_upload`` is set, so the base RESTThread loop logs a
FALSE "Published record" though nothing was sent. Raise
``weewx.restx.AbortedPost`` like every other uploader so skip_upload logs
"Skipped record" and never reports a phantom success.
"""

import pathlib

PATCH = (
    pathlib.Path(__file__).resolve().parent.parent
    / "patches/extensions/0006-emoncms-skip-upload-abortedpost.patch"
)


def test_skip_upload_raises_aborted_post():
    """``skip_upload`` must raise ``weewx.restx.AbortedPost`` so the
    RESTThread loop logs "Skipped record" instead of a phantom
    "Published record". Returning silently lies to the operator about
    successful uploads they never made.
    """
    src = PATCH.read_text()
    assert 'raise weewx.restx.AbortedPost("skip_upload")' in src, (
        "skip_upload branch must raise weewx.restx.AbortedPost so the "
        "base RESTThread loop logs `Skipped record` instead of a phantom success"
    )
    assert '-            loginf("skipping upload")\n-            return' in src, (
        "patch must remove the bare loginf/return pair that produces the "
        "phantom-success log line"
    )
