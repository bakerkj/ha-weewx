#!/opt/weewx/bin/python3
# Copyright (c) 2026 Kenneth Baker <bakerkj@umich.edu>
# All rights reserved.

"""
Addon hang-detection watchdog.

Reads its options from /data/options.json (HA Supervisor mounts this for the
addon at runtime). Periodically GETs `http://localhost:8099${watchdog_path}`
through the addon's own nginx and verifies the response's Last-Modified is
within `watchdog_max_age_seconds` of now. After
`watchdog_consecutive_failures` consecutive failures, sends SIGTERM to PID 1
(s6-overlay's init), which tears down the supervisor cleanly and exits the
container -- HA Supervisor's "Watchdog" toggle will then restart the addon.

Disabled when `watchdog_path` is empty (the default), in which case the
service sits idle and never fires.

Reading the URL through nginx is intentional: a single probe verifies both
that nginx is serving and that whatever writes the file (weewxd / rtgd /
the report engine) is doing so on cadence. Pick a URL the user knows is
rewritten regularly: index.html (every archive cycle) is a safe default;
/gauge-data.txt (every LOOP packet, ~2s) is much sharper if rtgd is enabled.
"""

from __future__ import annotations

import email.utils
import http.client
import json
import os
import signal
import sys
import time


OPTIONS_PATH = "/data/options.json"


def load_options() -> dict:
    try:
        with open(OPTIONS_PATH) as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except Exception as exc:
        print(f"watchdog: cannot parse {OPTIONS_PATH}: {exc}", file=sys.stderr)
        return {}


def probe(path: str, max_age: int) -> tuple[bool, str]:
    """Return (ok, reason)."""
    conn = http.client.HTTPConnection("localhost", 8099, timeout=10)
    try:
        conn.request("HEAD", path)
        resp = conn.getresponse()
    except Exception as exc:
        return False, f"nginx unreachable: {exc!r}"
    finally:
        try:
            conn.close()
        except Exception:
            pass
    if resp.status >= 400:
        return False, f"HTTP {resp.status} {resp.reason}"
    lm = resp.getheader("Last-Modified")
    if not lm:
        # Without Last-Modified there's no way to verify freshness, which is
        # the whole job of this watchdog. Treat it as a failure so the
        # operator notices and either picks a path that nginx serves with
        # Last-Modified (any on-disk file under /config/www does) or
        # disables the watchdog by clearing watchdog_path.
        return (
            False,
            f"HTTP {resp.status} but no Last-Modified header (cannot verify freshness)",
        )
    try:
        lm_ts = email.utils.parsedate_to_datetime(lm).timestamp()
    except Exception as exc:
        return False, f"unparsable Last-Modified={lm!r}: {exc!r}"
    age = time.time() - lm_ts
    if age > max_age:
        return False, f"stale: age={age:.0f}s > max_age={max_age}s (Last-Modified={lm})"
    return True, f"fresh: age={age:.0f}s <= max_age={max_age}s"


def halt(reason: str) -> None:
    # Send SIGTERM to PID 1 (s6-overlay's init) -- the documented way to
    # tear down the whole supervisor and exit the container cleanly. See
    # rootfs/etc/s6-overlay/s6-rc.d/{weewxd,nginx}/finish for the matching
    # rationale (and why we no longer use s6-svscanctl -t /run/service).
    print(
        f"watchdog: {reason}; bringing addon down (SIGTERM -> PID 1)",
        file=sys.stderr,
    )
    try:
        os.kill(1, signal.SIGTERM)
    except Exception as exc:
        print(f"watchdog: kill -TERM 1 failed: {exc!r}", file=sys.stderr)


def main() -> int:
    opts = load_options()
    path = (opts.get("watchdog_path") or "").strip()
    max_age = int(opts.get("watchdog_max_age_seconds") or 600)
    threshold = int(opts.get("watchdog_consecutive_failures") or 3)
    interval = int(opts.get("watchdog_interval_seconds") or 30)
    grace = int(opts.get("watchdog_startup_grace_seconds") or 0)

    if not path:
        print(
            "watchdog: watchdog_path is empty; watchdog disabled. Sleeping.",
            file=sys.stderr,
            flush=True,
        )
        # Sit idle rather than exiting; s6 would restart us in a tight loop.
        while True:
            time.sleep(3600)

    if not path.startswith("/"):
        path = "/" + path

    print(
        f"watchdog: enabled  path={path}  max_age={max_age}s  "
        f"threshold={threshold}  interval={interval}s  grace={grace}s",
        file=sys.stderr,
        flush=True,
    )

    if grace > 0:
        # Don't probe at all until the addon has had time to come up. Without
        # this, a fresh restart can find watchdog_path stale (mtime from before
        # the restart) and trip the threshold before the first archive cycle
        # has had a chance to refresh it -- a bootstrap deadlock where the
        # watchdog kills the very process that would have refreshed its
        # target. Pick grace > one full report-engine cycle of the target
        # file's source (archive_interval for HTML/PNG, much smaller for
        # /gauge-data.txt under rtgd).
        print(
            f"watchdog: sleeping {grace}s startup grace before first probe",
            file=sys.stderr,
            flush=True,
        )
        time.sleep(grace)

    failures = 0
    while True:
        ok, reason = probe(path, max_age)
        if ok:
            if failures:
                print(
                    f"watchdog: recovered after {failures} failure(s): {reason}",
                    file=sys.stderr,
                    flush=True,
                )
            failures = 0
        else:
            failures += 1
            print(
                f"watchdog: failure {failures}/{threshold}: {reason}",
                file=sys.stderr,
                flush=True,
            )
            if failures >= threshold:
                halt(f"{failures} consecutive watchdog failures on {path}")
                # PID 1 will tear down the tree shortly; sleep briefly
                # so we don't busy-loop while it does so.
                time.sleep(30)
                return 0
        time.sleep(interval)


if __name__ == "__main__":
    sys.exit(main())
