#!/usr/bin/env python3
# Copyright (c) 2026 Kenneth Baker <bakerkj@umich.edu>
# All rights reserved.

# Cross-check Renovate's proposed apt-package updates against Debian's actual
# archives. Reads Renovate's JSON-format dry-run log from argv[1] (each line a
# JSON event, produced by LOG_FORMAT=json LOG_LEVEL=debug), locates the
# "packageFiles with updates" event, walks its config tree to find every
# dependency, and for each one whose datasource is "repology" and
# packageName starts with "debian_13/" verifies:
#
#   (a) `dpkg --compare-versions <newVersion> ge <currentValue>` -- no
#       downgrades;
#   (b) <newVersion> appears in `apt-cache madison <depName>` -- whatever
#       Renovate concluded, apt knows of the same version for that exact
#       binary in trixie / -updates / -security. This catches the failure
#       mode where Repology resolves a binary to a wrong-upstream source
#       and Renovate happily lifts a "newer" version that doesn't exist
#       for the binary in the actual archive.

import json
import subprocess
import sys
from typing import Any, Generator


def iter_deps(obj: Any) -> Generator[dict, None, None]:
    """Yield every dep dict reachable from obj by walking the config tree."""
    if isinstance(obj, dict):
        if isinstance(obj.get("deps"), list):
            for dep in obj["deps"]:
                if isinstance(dep, dict):
                    yield dep
        for v in obj.values():
            yield from iter_deps(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from iter_deps(v)


def find_package_files_event(log_path: str) -> dict:
    """Return the first `packageFiles with updates` event from the JSON log."""
    with open(log_path, encoding="utf-8") as f:
        for line in f:
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event.get("msg") == "packageFiles with updates":
                return event
    raise SystemExit(
        "::error::no 'packageFiles with updates' event in dry-run log; "
        "did the dry-run run to completion with LOG_FORMAT=json?"
    )


def main() -> int:
    event = find_package_files_event(sys.argv[1])

    failures: list[str] = []
    checked = 0
    for dep in iter_deps(event.get("config", event)):
        if dep.get("datasource") != "repology":
            continue
        pkg = dep.get("packageName", "")
        if not pkg.startswith("debian_13/"):
            continue
        updates = dep.get("updates") or []
        if not updates:
            # Renovate is keeping the current pin -- nothing to validate.
            continue

        name = dep["depName"]
        cur = dep["currentValue"]
        for upd in updates:
            new = upd.get("newVersion") or upd.get("newValue")
            if not new:
                continue
            checked += 1

            # (a) no downgrade per dpkg's version comparator
            cmp_result = subprocess.run(
                ["dpkg", "--compare-versions", new, "ge", cur],
                capture_output=True,
            )
            if cmp_result.returncode != 0:
                failures.append(
                    f"{name}: proposed {new} is < currently pinned {cur} (downgrade)"
                )
                continue

            # (b) proposed version exists in apt-cache for this exact binary.
            # apt-cache madison output is "pkg | version | source" per line
            # with column-aligned whitespace. Parse the pipe-separated
            # fields rather than substring-matching the raw text (which
            # would false-positive "1.2" against a line containing "1.2.3").
            madison = subprocess.run(
                ["apt-cache", "madison", name],
                capture_output=True,
                text=True,
            )
            versions = {
                parts[1].strip()
                for line in madison.stdout.splitlines()
                if len(parts := line.split("|")) >= 2
            }
            if madison.returncode != 0 or new not in versions:
                madison_lines = madison.stdout.strip() or "(empty)"
                failures.append(
                    f"{name}: proposed {new} not in `apt-cache madison {name}` "
                    f"(currently pinned: {cur}). apt knows of:\n{madison_lines}"
                )

    if failures:
        print(
            "::error::Renovate proposed apt updates that disagree with apt's view of trixie:"
        )
        for f in failures:
            for line in f.splitlines():
                print(f"  {line}")
        return 1

    print(
        f"OK: cross-checked {checked} Renovate apt update(s) against "
        f"Debian trixie/-updates/-security archives."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
