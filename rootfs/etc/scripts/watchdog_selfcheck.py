#!/opt/weewx/bin/python3
# Copyright (c) 2026 Kenneth Baker <bakerkj@umich.edu>
# All rights reserved.

"""
Build-time unit checks for /etc/scripts/watchdog.py. Validates the freshness
policy directly against the `probe` function with a stubbed nginx, so the
behavior is locked in by the Dockerfile `test` stage without needing the
e2e to manufacture each case.
"""

from __future__ import annotations

import importlib.util
import sys
import time
from email.utils import formatdate

spec = importlib.util.spec_from_file_location("watchdog", "/etc/scripts/watchdog.py")
wd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wd)


class FakeResp:
    def __init__(self, status: int, last_modified: str | None) -> None:
        self.status = status
        self.reason = "OK" if status < 400 else "Not Found"
        self._lm = last_modified

    def getheader(self, name: str):
        if name.lower() == "last-modified":
            return self._lm
        return None


class FakeConn:
    def __init__(self, resp: FakeResp) -> None:
        self._resp = resp

    def request(self, method, path) -> None:  # noqa: ARG002 - signature parity
        pass

    def getresponse(self) -> FakeResp:
        return self._resp

    def close(self) -> None:
        pass


def stub_with(resp: FakeResp):
    """Patch HTTPConnection so probe() sees the given response."""
    wd.http.client.HTTPConnection = lambda *_args, **_kw: FakeConn(resp)


cases = [
    # (label, status, last_modified, max_age, expect_ok)
    ("fresh-200", 200, formatdate(time.time(), usegmt=True), 60, True),
    ("stale-200", 200, formatdate(time.time() - 3600, usegmt=True), 60, False),
    ("404", 404, None, 60, False),
    ("500", 500, None, 60, False),
    ("200-without-last-modified", 200, None, 60, False),
    ("200-with-bogus-last-modified", 200, "not a real date", 60, False),
]

failures: list[str] = []
for label, status, lm, max_age, expect_ok in cases:
    stub_with(FakeResp(status, lm))
    ok, reason = wd.probe("/x", max_age)
    if ok is not expect_ok:
        failures.append(
            f"  {label}: expected ok={expect_ok}, got ok={ok}, reason={reason}"
        )
    else:
        print(f"  ok {label}: {reason}", file=sys.stderr)

if failures:
    print("watchdog_selfcheck: FAILED", file=sys.stderr)
    for f in failures:
        print(f, file=sys.stderr)
    sys.exit(1)
print("watchdog_selfcheck: passed", file=sys.stderr)
