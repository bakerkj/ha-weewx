# Copyright (c) 2026 Kenneth Baker <bakerkj@umich.edu>
# All rights reserved.

"""Manual install of the inguy24/weewx-noaa_marine_API extension.

Its ``install.py`` runs a curses-based interactive setup during
``weectl extension install``. ``--yes`` doesn't dismiss curses, so
we can't ship this through ``build/install_extensions.sh``. Unpack
manually:

  - ``bin/user/marine_data.py``           - the service module
  - ``bin/user/marine_data_fields.yaml``  - field & table definitions
  - ``scripts/marine_data_installer.py``  - retained for its SHA pin
                                            (its five hardcoded tide
                                            operational fields are
                                            mirrored into the addon
                                            shim; drift there needs a
                                            re-audit). Not imported at
                                            runtime.

Per-site NOAA station IDs go into ``[MarineDataService]`` on the
target box after deploy - that's the interactive setup's job.
"""

import hashlib
import io
import os
import sys
import time
import urllib.error
import urllib.request
import zipfile

# SHA-pinned to main HEAD (no post-v1.0.1b tag; that tag alone fails the
# schema check). Renovate tracks this via a main-branch SHA regex.
URL = "https://github.com/inguy24/weewx-noaa_marine_API/archive/51db84c9b93116c52f009c0aad70dfb634abb8de.zip"
DEST_ROOT = "/opt/weewx-data"

# GitHub 5xx hiccups on the archive URL burn CI on unrelated PRs otherwise.
MAX_ATTEMPTS = 4
INITIAL_SLEEP = 2

# SHA256 of each extracted file after normalization (CRLF and bare CR
# both -> LF). The shim owns the marine DDL directly; its column list
# plus the tide_table operational fields are derived from these two
# files. If a Renovate bump changes either, the corresponding hash
# mismatches and the build fails: signal to re-audit the shim against
# the new upstream, then update the hash. Update by pasting the value
# printed in the build's "expected/got" report.
EXPECTED_SHA256 = {
    "bin/user/marine_data_fields.yaml": "28e3700ed28abf0eb5a21ffd473bebf7474c61026949e391a27aabef5f97435f",
    "scripts/marine_data_installer.py": "2d05aadee3c2e5be1ff8c1b5dae1c3f22397cc9a7a5582353727a7dfc7a7315f",
}


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
            prefix + "install.py": os.path.join(
                DEST_ROOT, "scripts/marine_data_installer.py"
            ),
        }

        # Verify all SHAs BEFORE writing any file to disk. A drift outside
        # Docker (dev workstation, cache-populate step) would otherwise
        # silently overwrite prior known-good copies.
        payloads: list[tuple[str, str, bytes]] = []
        drift: list[tuple[str, str, str]] = []
        for member, dest in expected.items():
            if member not in names:
                sys.exit(f"marine_data install: expected member {member!r} not in zip")
            payload = z.read(member).replace(b"\r\n", b"\n").replace(b"\r", b"\n")
            rel = os.path.relpath(dest, DEST_ROOT)
            payloads.append((member, dest, payload))
            want = EXPECTED_SHA256.get(rel)
            if want is not None:
                got = hashlib.sha256(payload).hexdigest()
                if got != want:
                    drift.append((rel, want, got))

    # Guard against a rename to `dest` that silently disables the pin.
    dest_rels = {os.path.relpath(d, DEST_ROOT) for _, d, _ in payloads}
    orphaned_pins = set(EXPECTED_SHA256) - dest_rels
    if orphaned_pins:
        sys.exit(
            f"marine_data install: EXPECTED_SHA256 has keys with no matching dest: {sorted(orphaned_pins)}"
        )

    if drift:
        print(
            "marine_data install: upstream drift; audit the shim and update EXPECTED_SHA256.",
            file=sys.stderr,
        )
        for rel, want, got in drift:
            print(
                f"  {rel}\n    expected: {want}\n    got:      {got}", file=sys.stderr
            )
        sys.exit(1)

    for dest_dir in {os.path.dirname(dest) for _, dest, _ in payloads}:
        os.makedirs(dest_dir, exist_ok=True)
    # Atomic: write each to <dest>.tmp first, then os.replace to promote.
    # Partial state (SIGTERM/OOM/ENOSPC) leaves stale originals untouched
    # instead of a mismatched half-updated set.
    for member, dest, payload in payloads:
        tmp = dest + ".tmp"
        with open(tmp, "wb") as f:
            f.write(payload)
        os.replace(tmp, dest)
        print(f"  Copied {member} -> {dest}")


if __name__ == "__main__":
    main()
