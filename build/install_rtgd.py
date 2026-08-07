# Copyright (c) 2026 Kenneth Baker <bakerkj@umich.edu>
# All rights reserved.

"""Manual install of the realtime-gauge-data extension.

Its ``install.py`` uses ``distutils`` (removed in Python 3.12) and the old
WeeWX 3/4 ``ExtensionInstaller`` API, so ``weectl extension install``
chokes on it. We just unpack the two pieces directly:

  - ``bin/user/rtgd.py``
  - ``skins/RealtimeGauges/`` (whole directory tree)

The top-level directory inside a GitHub archive zip varies with the ref
(tag vs SHA), so we discover it from the zip itself rather than coupling
the unpack to a specific version string. A post-unpack sanity check
fails the build if no expected files were copied.
"""

import io
import os
import sys
import time
import urllib.error
import urllib.request
import zipfile

URL = "https://github.com/hoetzgit/weewx-realtime_gauge-data/archive/v0.6.0.zip"
DEST_ROOT = "/opt/weewx-data"

# urllib has no built-in retry. GitHub 5xx hiccups on the archive URL surface
# as fatal errors and burn CI builds on unrelated PRs. Retry with exponential
# backoff — same shape as build/install_extensions.sh.
MAX_ATTEMPTS = 4
INITIAL_SLEEP = 2


def _fetch_with_retry(url: str) -> bytes:
    sleep_s = INITIAL_SLEEP
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            with urllib.request.urlopen(url) as r:
                return r.read()
        except (urllib.error.HTTPError, urllib.error.URLError) as exc:
            if attempt >= MAX_ATTEMPTS:
                raise
            print(
                f"  attempt {attempt} failed ({exc}); retrying in {sleep_s}s...",
                file=sys.stderr,
            )
            time.sleep(sleep_s)
            sleep_s *= 2
    raise RuntimeError("unreachable")  # for type-checkers


def main() -> None:
    print(f"Manually installing realtime-gauge-data from {URL}")

    data = _fetch_with_retry(URL)

    with zipfile.ZipFile(io.BytesIO(data)) as z:
        names = z.namelist()
        top_levels = {n.split("/", 1)[0] for n in names if "/" in n}
        if len(top_levels) != 1:
            sys.exit(f"rtgd zip has unexpected layout: top-level dirs = {top_levels}")
        prefix = next(iter(top_levels)) + "/"

        copied_module = False
        copied_skin_files = 0
        for name in names:
            if name == prefix + "bin/user/rtgd.py":
                dest = os.path.join(DEST_ROOT, "bin/user/rtgd.py")
                with open(dest, "wb") as f:
                    f.write(z.read(name))
                print(f"  Copied {name} -> {dest}")
                copied_module = True
            elif name.startswith(
                prefix + "skins/RealtimeGauges/"
            ) and not name.endswith("/"):
                rel = name[len(prefix + "skins/RealtimeGauges/") :]
                dest = os.path.join(DEST_ROOT, "skins/RealtimeGauges", rel)
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                with open(dest, "wb") as f:
                    f.write(z.read(name))
                print(f"  Copied {name} -> {dest}")
                copied_skin_files += 1

    if not copied_module:
        sys.exit(f"rtgd install: bin/user/rtgd.py not found under prefix {prefix!r}")
    if copied_skin_files == 0:
        sys.exit(
            f"rtgd install: no skin files copied from {prefix}skins/RealtimeGauges/"
        )


if __name__ == "__main__":
    main()
