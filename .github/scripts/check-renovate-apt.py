#!/usr/bin/env python3
# Copyright (c) 2026 Kenneth Baker <bakerkj@umich.edu>
# All rights reserved.

# Cross-check Renovate's proposed apt-package updates against Debian's actual
# archives. Reads Renovate's debug-level dry-run log from argv[1], extracts
# every proposed update whose datasource is "repology" and packageName starts
# with "debian_13/", and for each one verifies:
#
#   (a) newVersion compares >= currentValue per `dpkg --compare-versions ge`;
#   (b) newVersion appears in `apt-cache madison <depName>` for the binary
#       (so wherever Renovate resolved the version, apt agrees it exists for
#       this exact binary in trixie / -updates / -security).
#
# Both checks combined are what catches an overridePackageName rule that
# mistakenly points a binary at a wrong-upstream Repology source: the wrong
# version Renovate would emit doesn't exist for the binary in apt, so (b)
# fails. (a) catches downgrades.

import re
import subprocess
import sys


def main() -> int:
    log_path = sys.argv[1]
    with open(log_path, encoding="utf-8") as f:
        log = f.read()

    # Renovate's debug-level dry-run dumps each flattened update as a JSON
    # object inline. Extract (depName, packageName, currentValue, datasource,
    # newVersion) tuples by anchored regex -- structured parsing of the full
    # config dump is fragile because the JSON is interleaved with INFO/TRACE
    # log lines.
    pat = re.compile(
        r'"depName":\s*"([^"]+)".{1,500}?'
        r'"packageName":\s*"([^"]+)".{1,200}?'
        r'"currentValue":\s*"([^"]+)".{1,200}?'
        r'"datasource":\s*"([^"]+)".{1,1500}?'
        r'"newVersion":\s*"([^"]+)"',
        re.S,
    )

    failures: list[str] = []
    seen: set[tuple[str, str, str]] = set()
    for m in pat.finditer(log):
        dep, pkg, cur, ds, new = m.groups()
        key = (dep, cur, new)
        if key in seen:
            continue
        if ds != "repology" or not pkg.startswith("debian_13/"):
            continue
        seen.add(key)

        # (a) no downgrade per dpkg's version comparator
        cmp_result = subprocess.run(
            ["dpkg", "--compare-versions", new, "ge", cur],
            capture_output=True,
        )
        if cmp_result.returncode != 0:
            failures.append(
                f"{dep}: proposed {new} is < currently pinned {cur} (downgrade)"
            )
            continue

        # (b) proposed version exists in apt-cache for this exact binary
        madison = subprocess.run(
            ["apt-cache", "madison", dep],
            capture_output=True,
            text=True,
        )
        if madison.returncode != 0 or new not in madison.stdout:
            failures.append(
                f"{dep}: proposed {new} not in `apt-cache madison {dep}` "
                f"(currently pinned: {cur}). apt knows of:\n"
                f"{madison.stdout.strip() or '(empty)'}"
            )
            continue

    if failures:
        print(
            "::error::Renovate proposed apt updates that disagree with apt's view of trixie:"
        )
        for f in failures:
            for line in f.splitlines():
                print(f"  {line}")
        return 1

    print(
        f"OK: cross-checked {len(seen)} Renovate apt update(s) against "
        f"Debian trixie/-updates/-security archives."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
