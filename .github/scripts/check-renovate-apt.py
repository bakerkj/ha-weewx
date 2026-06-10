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

    # Renovate's debug-level dry-run dumps each flattened-update record as a
    # JSON object inline with the log. Slice the log at every "depName" so a
    # per-record regex can't accidentally pick up fields from the next record
    # (e.g. matching depName=libnginx-mod-http-js then greedily scanning to
    # the newVersion of the following nginx-light record).
    depname_re = re.compile(r'"depName":\s*"([^"]+)"')
    record_starts = [m.start() for m in depname_re.finditer(log)]
    record_starts.append(len(log))

    fields_re = re.compile(
        r'"packageName":\s*"([^"]+)"',
    )
    cur_re = re.compile(r'"currentValue":\s*"([^"]+)"')
    ds_re = re.compile(r'"datasource":\s*"([^"]+)"')
    # Non-empty updates: "updates": [ {  ... }
    upd_re = re.compile(r'"updates":\s*\[\s*\{')
    nv_re = re.compile(r'"newVersion":\s*"([^"]+)"')

    failures: list[str] = []
    seen: set[tuple[str, str, str]] = set()
    for i in range(len(record_starts) - 1):
        record = log[record_starts[i] : record_starts[i + 1]]
        dep_match = depname_re.search(record)
        if not dep_match:
            continue
        dep = dep_match.group(1)

        pkg_match = fields_re.search(record)
        ds_match = ds_re.search(record)
        cur_match = cur_re.search(record)
        if not (pkg_match and ds_match and cur_match):
            continue
        pkg = pkg_match.group(1)
        ds = ds_match.group(1)
        cur = cur_match.group(1)

        if ds != "repology" or not pkg.startswith("debian_13/"):
            continue

        # Only check records that actually have a proposed update. An empty
        # "updates": [] array means Renovate is keeping the current pin.
        if not upd_re.search(record):
            continue
        nv_match = nv_re.search(record)
        if not nv_match:
            continue
        new = nv_match.group(1)

        key = (dep, cur, new)
        if key in seen:
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
