#!/usr/bin/env python3
# Copyright (c) 2026 Kenneth Baker <bakerkj@umich.edu>
# All rights reserved.

"""Detect newer commits for SHA-pinned weewx extensions and rewrite the
Dockerfile + scripts/check-updates.sh in place.

Renovate's ``custom.regex`` manager in ``renovate.json`` already covers
*tag-pinned* GitHub archive URLs
(``github.com/<owner>/<repo>/archive/v?N.N.N.zip``). It does NOT cover
commit-SHA pins (the matthewwall extensions, plus the two added by
PR #57: chaunceygardiner/weewx-rain24h, tkeffer/weewx-xaggs), because
there's no Renovate datasource that semver-orders raw commit SHAs.
``.github/workflows/check-updates.yml`` invokes this script weekly to
fill the gap and produces a single bundled bump PR.

Output: a JSON array of ``{owner, repo, from, to}`` objects to stdout,
ready for the workflow to render into a PR body. The Dockerfile (and
``scripts/check-updates.sh`` ``check_commit`` lines, if present) are
edited in place; the workflow then commits and opens / updates the PR.

Standard library only — runs in any GitHub-Actions ubuntu image with no
``pip install`` step.
"""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCKERFILE = ROOT / "Dockerfile"
CHECK_UPDATES = ROOT / "scripts" / "check-updates.sh"

# https://github.com/<owner>/<repo>/archive/<7-hex-sha>.zip
# Anchored to .zip so it can't false-match a longer hex string elsewhere.
SHA_URL_RE = re.compile(
    r"https://github\.com/"
    r"(?P<owner>[\w.-]+)/(?P<repo>[\w.-]+)/archive/"
    r"(?P<sha>[0-9a-f]{7})\.zip"
)


def latest_commit_sha(owner: str, repo: str) -> str:
    """Return the 7-char SHA of the latest commit on the repo's default
    branch via the GitHub commits API.
    """
    url = f"https://api.github.com/repos/{owner}/{repo}/commits?per_page=1"
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json"})
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        # Authenticated requests get 5000/hr instead of 60/hr; matters when the
        # workflow re-runs frequently or against many extensions.
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.load(resp)
    if not data:
        raise RuntimeError(f"no commits returned for {owner}/{repo}")
    return data[0]["sha"][:7]


def main() -> int:
    df_text = DOCKERFILE.read_text()

    # Find every SHA-pinned URL and dedupe by (owner, repo). One repo can
    # legitimately appear multiple times in the Dockerfile (e.g. the install
    # URL plus a commit reference in a comment); we want one query per repo
    # and a replace that hits all sites.
    pinned: dict[tuple[str, str], str] = {}
    for m in SHA_URL_RE.finditer(df_text):
        pinned[(m.group("owner"), m.group("repo"))] = m.group("sha")

    bumps: list[dict[str, str]] = []
    df_new = df_text
    for (owner, repo), current in sorted(pinned.items()):
        try:
            latest = latest_commit_sha(owner, repo)
        except (urllib.error.URLError, urllib.error.HTTPError, RuntimeError) as e:
            # Log to stderr but keep going on other repos. The workflow
            # surfaces stderr in the run log; failures don't block other bumps.
            print(f"WARN: {owner}/{repo}: {e}", file=sys.stderr)
            continue
        if latest == current:
            continue
        bumps.append({"owner": owner, "repo": repo, "from": current, "to": latest})
        df_new = df_new.replace(
            f"github.com/{owner}/{repo}/archive/{current}.zip",
            f"github.com/{owner}/{repo}/archive/{latest}.zip",
        )

    if bumps:
        DOCKERFILE.write_text(df_new)
        # Also keep scripts/check-updates.sh in sync. Each tracked dep has a
        # `check_commit "label" "owner/repo" "<sha>"` line. We rewrite the
        # SHA in place when one matches a bump.
        if CHECK_UPDATES.exists():
            cu_text = CHECK_UPDATES.read_text()
            for bump in bumps:
                cu_text = re.sub(
                    r'(check_commit\s+"[^"]+"\s+"'
                    + re.escape(f"{bump['owner']}/{bump['repo']}")
                    + r'"\s+")[0-9a-f]{7}(")',
                    rf"\g<1>{bump['to']}\g<2>",
                    cu_text,
                )
            CHECK_UPDATES.write_text(cu_text)

    # Machine-readable output for the workflow.
    json.dump(bumps, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
