# Copyright (c) 2026 Kenneth Baker <bakerkj@umich.edu>
# All rights reserved.

"""Manual install of the inguy24/weewx-noaa_marine_API extension.

Its ``install.py`` runs a curses-based interactive setup during
``weectl extension install`` (it asks for CO-OPS tide station IDs,
NDBC buoy IDs, field selection). ``--yes`` doesn't dismiss curses, so
we can't ship this through ``build/install_extensions.sh``. Unpack
manually:

  - ``bin/user/marine_data.py``           — the service module
  - ``bin/user/marine_data_fields.yaml``  — field & table definitions
  - ``bin/user/xtypes/*``                 — search-list extensions (if any)
  - ``scripts/marine_data_installer.py``  — the installer, preserved so
                                            /etc/scripts/init_marine_schema.py
                                            can call its private
                                            ``_create_marine_tables_weewx_compliant``
                                            at addon startup to create
                                            the three marine tables from
                                            the YAML field definitions.

Per-site NOAA station IDs go into ``[MarineDataService]`` in
``weewx.conf`` on the target box after deploy — that's the interactive
setup's job, which we can't run here.
"""

import io
import os
import sys
import time
import urllib.error
import urllib.request
import zipfile

# SHA pin at v1.0.1b's commit; upstream only ships beta-suffixed tags
# which the tag regex rejects, so this is tracked via renovate.json's
# main-branch SHA-regex manager.
URL = "https://github.com/inguy24/weewx-noaa_marine_API/archive/c689a7e4cba3f8fbff6c2d9d675a342f30558f77.zip"
DEST_ROOT = "/opt/weewx-data"

# Retry shape: same as install_extensions.sh + install_rtgd.py — GitHub 5xx
# hiccups on the archive URL burn CI on unrelated PRs otherwise.
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
    print(f"Manually installing weewx-noaa_marine_API from {URL}")
    data = _fetch_with_retry(URL)

    with zipfile.ZipFile(io.BytesIO(data)) as z:
        names = z.namelist()
        top_levels = {n.split("/", 1)[0] for n in names if "/" in n}
        if len(top_levels) != 1:
            sys.exit(
                f"marine_data zip has unexpected layout: top-level dirs = {top_levels}"
            )
        prefix = next(iter(top_levels)) + "/"

        # Files we require. Add here rather than special-casing below so a
        # future rename or missing file fails loudly.
        expected = {
            prefix + "bin/user/marine_data.py": os.path.join(
                DEST_ROOT, "bin/user/marine_data.py"
            ),
            prefix + "bin/user/marine_data_fields.yaml": os.path.join(
                DEST_ROOT, "bin/user/marine_data_fields.yaml"
            ),
            # The installer's own module is preserved so the addon startup
            # shim can invoke _create_marine_tables_weewx_compliant. Kept
            # OUT of bin/user/ so weewx doesn't try to import it as a
            # user.* module.
            prefix + "install.py": os.path.join(
                DEST_ROOT, "scripts/marine_data_installer.py"
            ),
        }

        for dest_dir in {os.path.dirname(dest) for dest in expected.values()}:
            os.makedirs(dest_dir, exist_ok=True)

        copied = 0
        for member, dest in expected.items():
            if member not in names:
                sys.exit(f"marine_data install: expected member {member!r} not in zip")
            with open(dest, "wb") as f:
                f.write(z.read(member))
            print(f"  Copied {member} -> {dest}")
            copied += 1

    if copied != len(expected):
        sys.exit(
            f"marine_data install: copied {copied} of {len(expected)} expected files"
        )


if __name__ == "__main__":
    main()
