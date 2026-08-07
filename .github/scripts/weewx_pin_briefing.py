#!/usr/bin/env python3
# Copyright (c) 2026 Kenneth Baker <bakerkj@umich.edu>
# All rights reserved.

# Copyright (c) 2026 Kenneth J Baker <bakerkj@umich.edu>
#
# Mechanize the evidence-gathering for a Renovate PR review on ha-weewx.
#
# weewx_pin_diff.py answers "what changed upstream". This answers the
# questions that actually decide whether it MATTERS to us -- and every one
# of them is pure set arithmetic, so none should be an LLM's job:
#
#   1. WHICH FILES WE PATCH WERE ALSO CHANGED UPSTREAM.
#      ha-weewx applies unified-diff patches to weewx core (weedb, weeutil),
#      to bundled extensions (`bin/user/*.py`) and to the felddy MQTT
#      publisher (`weewx_ha/*`). If the upstream commit range in a bump
#      touches a file we patch, one of two things is true:
#        - the patch will fail to apply on the next build (a break), OR
#        - the fix was upstreamed and our patch is now redundant.
#      Both are load-bearing news. We compute the intersection by parsing
#      our own `.patch` files' `--- a/PATH` headers and suffix-matching
#      against the compare API's changed-files list.
#
#   2. WHAT EACH EXTENSION IS EXPECTED TO PRODUCE.
#      `build/extensions.txt` prefixes each URL with `# install: <path>`
#      lines that build/check_image.sh asserts against the built image.
#      If an extension bump renames or removes one of those files upstream,
#      the in-image assertion fails at build time -- but a REVIEWER can spot
#      it here, before merge, by cross-referencing the upstream changed-file
#      list against the extension's `# install:` paths.
#
#   3. FOR WEEWX ITSELF, WHETHER `src/weewx_data/` OR `src/schemas/` MOVED.
#      Those trees ship in our container (`skins/`, the archive schema),
#      so they cannot be treated as pure library churn.
#
# It does NOT inline the bulk. Everything heavy is PRE-FETCHED into a
# directory that is handed to the agent, and the briefing is just the
# index into it:
#
#   upstream/
#     briefing.md                    <- small, high-signal: ranges, hits table
#     <slug>/
#       range.txt                    depName, kind, source_repo, old/new, compare
#       commits.md                   every commit subject in the range
#       changed-files.txt            every file the range touched (with status)
#       patches/<flat-path>.diff     the FULL upstream patch per changed file
#       intersect/<flat-path>.before whole upstream file at OLD ref  } only for files
#       intersect/<flat-path>.after  whole upstream file at NEW ref  } we patch
#       our-side-context.md          which of our patches touch the same paths,
#                                    and (for extensions) which `# install:`
#                                    paths this pin is expected to produce
#
# Why a directory rather than one big briefing:
#   * the briefing stays small -- the bulk never has to fit in the context
#     window, and nothing needs clipping to protect it. The agent reads
#     only what it needs.
#   * the agent then needs NO NETWORK: with the data on disk it holds no
#     gh/api tool at all -- so an instruction injected into an upstream
#     commit message has no egress and no write path.
#   * the tree uploads as a CI artifact, so when a verdict looks wrong you
#     can read exactly what the agent was handed.
#
# Writes the tree; prints nothing. Exits 0 having written nothing when
# no pin changed.
#
# Usage: weewx_pin_briefing.py <base-ref> <head-ref> <out-dir>

import base64
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

# Reuses the resolver's logic for parsing the PR diff so a shape it can
# resolve is a shape we can brief on (and vice versa). Importing here rather
# than duplicating keeps the two scripts in sync -- adding a new pin shape
# means editing weewx_pin_diff.py, not this file.
from weewx_pin_diff import (
    TRACKED_FILES,
    _pair_up,
    _pins_in_side,
    diff_of,
    resolve,
)

# ---- our-side inventory (patches + extension install manifest) ------------

# Every file whose upstream tree the reviewer might need to cross-reference
# against a bump. Keep the same shape a patch's `--- a/PATH` line uses.
PATCH_DIRS = ("patches/weewx", "patches/extensions", "patches/venv")


def patch_targets(patch_path):
    """Return every file path a `.patch` modifies (parsed from `--- a/PATH`).

    We take the a/ (pre-image) side because that is the path in the tree the
    patch is applied AGAINST, which is exactly what we suffix-compare with the
    upstream changed-file list. `/dev/null` on the a/ side (a new-file patch)
    is dropped -- upstream cannot have modified a file that did not exist
    before our patch introduced it.
    """
    targets = []
    try:
        text = patch_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return targets
    for line in text.splitlines():
        if not line.startswith("--- "):
            continue
        rest = line[4:].strip()
        # Common forms: `a/path/to/file`, `path/to/file`, `/dev/null`,
        # `a/path\tYYYY-MM-DD ...` (git-style with trailing timestamp).
        rest = rest.split("\t", 1)[0].strip()
        if rest == "/dev/null":
            continue
        rest = rest.removeprefix("a/")
        if rest:
            targets.append(rest)
    return targets


def scan_our_patches(repo_root):
    """{patch_relpath: [target_paths]} for every .patch in PATCH_DIRS.

    Repo-relative paths so we can print them straight into the briefing.
    """
    out = {}
    for d in PATCH_DIRS:
        base = repo_root / d
        if not base.is_dir():
            continue
        for p in sorted(base.glob("*.patch")):
            rel = str(p.relative_to(repo_root))
            out[rel] = patch_targets(p)
    return out


# Parse build/extensions.txt into {url: [install_paths]}. The lines above each
# URL are the `# install: <path>` markers; a URL with NO install lines simply
# has an empty list (that is a documentation gap in extensions.txt, not this
# script's problem).
INSTALL_RE = re.compile(r"^#\s*install:\s*(?P<path>\S+)\s*$")
URL_RE = re.compile(r"^\s*(?P<url>https?://\S+)\s*$")


def parse_extensions_manifest(repo_root):
    """{url: [install_paths]} from build/extensions.txt.

    URL comes bare (no `.zip` split), so the caller can key on the same string
    it pulled out of the PR diff. If extensions.txt is missing, return {} --
    a PR that only touches Dockerfile or pyproject.toml won't need it.
    """
    manifest = {}
    p = repo_root / "build" / "extensions.txt"
    if not p.is_file():
        return manifest
    pending = []
    for line in p.read_text(encoding="utf-8").splitlines():
        m = INSTALL_RE.match(line)
        if m:
            pending.append(m.group("path"))
            continue
        u = URL_RE.match(line)
        if u:
            manifest[u.group("url")] = list(pending)
            pending = []
            continue
        # A blank line or an unrelated `#` comment resets the pending buffer
        # so `# install:` lines don't drift over intervening prose.
        if not line.strip() or line.lstrip().startswith("#"):
            if not line.strip():
                pending = []
            continue
    return manifest


# ---- upstream helpers (network) -------------------------------------------


def gh_json(url, token):
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json"})
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        print(f"warning: GET {url} failed: {exc}", file=sys.stderr)
        return None


def file_at(repo_path, path, rev, token):
    """Whole file content at a revision, or None.

    Used to stage the BEFORE/AFTER of files we patch: a hunk carries 3 lines
    of context, which is often too little to judge a scriptlet inside the
    file. Returns None on any lookup / decode failure; a missing before/after
    is expected for adds/removes and is not an error.
    """
    data = gh_json(
        f"https://api.github.com/repos/{repo_path}/contents/{path}?ref={rev}", token
    )
    if not data or "content" not in data:
        return None
    try:
        return base64.b64decode(data["content"]).decode("utf-8", "replace")
    except (ValueError, TypeError):
        return None


# ---- intersection ----------------------------------------------------------


def suffix_hit(upstream_path, our_target):
    """True if `upstream_path` is the same file as `our_target` by suffix.

    Suffix match handles the two common repo layouts our patches straddle:

      * weewx: our patch says `weedb/mysql.py` (venv site-packages layout);
        upstream repo says `src/weedb/mysql.py`. Match on the tail.
      * felddy: our patch says `config_publisher.py` (bare, relative to the
        package dir); upstream repo says `weewx_ha/config_publisher.py`.
      * extensions: our patch says `bin/user/rtldavis.py`; upstream extension
        repo also says `bin/user/rtldavis.py`. Same path, match wins on
        equality (`endswith` on `"/" + x` won't match a top-level file, but
        the equality branch will).
    """
    return upstream_path == our_target or upstream_path.endswith("/" + our_target)


def find_patch_hits(our_patches, upstream_files):
    """List of (patch_relpath, patch_target, upstream_file, status).

    Every hit -- one row per (our patch target, upstream file) pair. The same
    upstream file can match more than one patch (e.g. three rtldavis patches
    all touch bin/user/rtldavis.py, and an upstream change to that file hits
    all three -- and we want to see all three flagged).
    """
    hits = []
    for patch_rel, targets in our_patches.items():
        for target in targets:
            for f, meta in upstream_files.items():
                if suffix_hit(f, target):
                    hits.append((patch_rel, target, f, meta["status"]))
    return hits


# Statuses that mean the install manifest could BREAK -- i.e. the path we
# assert in build/check_image.sh may no longer be produced. A plain "modified"
# is normal churn (the file still exists at the same path) and is treated as
# informational, not an alarm.
STRUCTURAL_STATUSES = {"removed", "renamed", "added"}


def find_install_hits(install_paths, upstream_files):
    """Whether each of the extension's `# install:` paths still exists / moved
    in the new range. Returns [(install_path, [(upstream_file, status), ...])].

    An `install:` path prefix that the upstream range removed or renamed is
    the exact signal build/check_image.sh will flag at build time -- we surface
    it here for the reviewer, before the CI build wastes cycles. Modifications
    to files under an install: skin directory are also included (as
    informational context), but the alarm is reserved for structural changes.
    """
    hits = []
    for ip in install_paths:
        matches = []
        for f, meta in upstream_files.items():
            # An install: path can be either a file (bin/user/emoncms.py) or a
            # directory (skins/exfoliation). For directories we match any
            # upstream file whose path starts with that prefix.
            if suffix_hit(f, ip) or f.startswith(ip + "/") or f.endswith("/" + ip):
                matches.append((f, meta["status"]))
        if matches:
            hits.append((ip, matches))
    return hits


def install_hits_structural(install_hits):
    """Subset of install_hits with only add/remove/rename statuses.

    These are the real break signals -- what would make `check_image.sh` fail.
    Used to decide whether to fire the :rotating_light: alarm.
    """
    out = []
    for ip, matches in install_hits:
        real = [(f, s) for f, s in matches if s in STRUCTURAL_STATUSES]
        if real:
            out.append((ip, real))
    return out


# ---- staging ---------------------------------------------------------------


def flat(path):
    """A filesystem-safe leaf name for an upstream path."""
    return path.strip("/").replace("/", "__")


def write_file(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def slug_for(r):
    """Directory name under upstream/ for one pin.

    depName can carry a `/` (owner/repo); we flatten it to `owner__repo` so
    the directory is safe on every filesystem. Kind is prefixed so pyproject
    and Dockerfile `uv` pins live side by side without clashing.
    """
    return f"{r['kind']}__{r['depName'].replace('/', '__')}"


def stage_upstream(out_dir, r, token, our_patches, ext_manifest, src_file_diff):
    """Stage one resolved pin's upstream range on disk. Returns the briefing
    section (markdown text) for this pin.

    src_file_diff: the git diff text of the file the pin came from (Dockerfile,
    pyproject.toml, ...). Included in our-side-context.md so the reviewer sees
    the pin line that changed, without having to re-run git diff themselves.
    """
    slug = slug_for(r)
    d = out_dir / slug

    lines = [
        f"### `{r['depName']}` — {r['old_display']} → {r['new_display']}",
        "",
        f"- kind: `{r['kind']}` (from `{r['source_file']}`)",
    ]

    # If we resolved a real range, dump range/commits/files/patches. Otherwise
    # write only range.txt with the note (so the tree is uniform).
    if r["compare_url"]:
        lines += [
            (
                f"- range: [`{r['old_display']}…{r['new_display']}`]"
                f"({r['compare_url']}) in `{r['source_repo']}`"
            ),
            (
                f"- {len(r['files'])} upstream file(s) changed; "
                f"{r['commit_count']} commit(s)"
            ),
        ]
        write_file(
            d / "range.txt",
            f"depName:     {r['depName']}\n"
            f"kind:        {r['kind']}\n"
            f"source_file: {r['source_file']}\n"
            f"source_repo: {r['source_repo']}\n"
            f"old_ref:     {r['old_ref']}\n"
            f"new_ref:     {r['new_ref']}\n"
            f"compare:     {r['compare_url']}\n",
        )
        write_file(
            d / "commits.md",
            "\n".join(f"- {s}" for s in r["subjects"]) or "(none)",
        )
        cf_lines = []
        for f, meta in r["files"].items():
            cf_lines.append(f"{meta['status']:<10}\t{f}")
        write_file(d / "changed-files.txt", "\n".join(cf_lines) or "(none)")
        for f, meta in r["files"].items():
            if meta["patch"]:
                write_file(
                    d / "patches" / f"{flat(f)}.diff",
                    f"# status: {meta['status']}\n{meta['patch']}",
                )
    else:
        lines += [
            f"- :grey_question: {r['note']}",
        ]
        write_file(
            d / "range.txt",
            f"depName:     {r['depName']}\n"
            f"kind:        {r['kind']}\n"
            f"source_file: {r['source_file']}\n"
            f"note:        {r['note']}\n",
        )

    lines.append(f"- prefetched: `{d}/`")

    # ---- our-side context (patches + install manifest) -------------------
    ctx_lines = [
        f"# our-side context for `{r['depName']}` ({r['kind']})",
        "",
        "## PR-diff hunk (the line that changed in this PR)",
        "",
        "```diff",
        (src_file_diff.strip() or "(empty)"),
        "```",
        "",
    ]

    # Every hit is a signal; the *table* of hits is the briefing's key claim.
    patch_hits = []
    install_hits = []
    weewx_data_hits = []

    if r["files"]:
        patch_hits = find_patch_hits(our_patches, r["files"])
        # Extension install-manifest cross-check. Only meaningful for github
        # archive pins from build/extensions.txt whose URL keys the manifest.
        # We reconstruct the URL from the resolved pin's shape.
        if r["source_file"] == "build/extensions.txt" and r["kind"] == "github_archive":
            new_url = (
                f"https://github.com/{r['source_repo']}/archive/{r['new_ref']}.zip"
            )
            # The manifest is built from the HEAD extensions.txt, so the new_ref
            # URL is the one that keys it.
            install_hits = find_install_hits(ext_manifest.get(new_url, []), r["files"])
        # weewx core -- flag skins / schema / weewx_data changes since those
        # ship in our container. Tests deliberately excluded: src/weewx/tests/
        # does not ship in the image, and flagging it as "runs in our
        # container" would be a false alarm.
        if r["source_repo"] == "weewx/weewx":
            for f, meta in r["files"].items():
                if f.startswith(("src/weewx_data/", "src/schemas/")):
                    weewx_data_hits.append((f, meta["status"]))

    # PATCH INTERSECTION -- the sharpest signal. Emit both in the briefing
    # index AND in our-side-context.md.
    if patch_hits:
        lines += [
            "",
            (
                ":rotating_light: **Patch intersection: upstream touched files "
                "we patch.** Either the patch will fail to apply, or the fix was "
                "upstreamed. Read the patch AND the upstream diff of the same file."
            ),
            "",
            "| our patch | our target | upstream file | upstream change |",
            "|---|---|---|---|",
        ]
        for patch_rel, target, upstream_file, status in patch_hits:
            lines.append(
                f"| `{patch_rel}` | `{target}` | "
                f"[`{upstream_file}`]"
                f"(https://github.com/{r['source_repo']}/blob/{r['new_ref']}/"
                f"{upstream_file}) | `{status}` |"
            )
        ctx_lines += [
            "## Patches that touch files upstream changed",
            "",
            (
                "For each row: the patch, the target it modifies, the upstream "
                "file the range changed, the change status. Read both the "
                "`patches/<file>.diff` (the upstream change) and our `.patch` "
                "(what we edit on top)."
            ),
            "",
        ]
        for patch_rel, target, upstream_file, status in patch_hits:
            ctx_lines.append(
                f"- `{patch_rel}` -> `{target}` <=> `{upstream_file}` ({status})"
            )
        ctx_lines.append("")

        # Stage before/after of each upstream file we patch. A hunk's 3 lines
        # of context are often too little to judge a bugfix that lives inside
        # a longer function.
        staged = set()
        for _patch_rel, _target, upstream_file, status in patch_hits:
            if upstream_file in staged:
                continue
            staged.add(upstream_file)
            before = file_at(r["source_repo"], upstream_file, r["old_ref"], token)
            after = (
                None
                if status == "removed"
                else file_at(r["source_repo"], upstream_file, r["new_ref"], token)
            )
            if before is not None:
                write_file(d / "intersect" / f"{flat(upstream_file)}.before", before)
            if after is not None:
                write_file(d / "intersect" / f"{flat(upstream_file)}.after", after)
    else:
        # State the *negative* explicitly so "no patch intersection" is a
        # positive claim rather than an absence to interpret. Only meaningful
        # when we actually resolved a range -- we don't want to say "no
        # intersection" about a pin whose range we could not compute.
        if r["files"]:
            ctx_lines += [
                "## Patches that touch files upstream changed",
                "",
                (
                    "None. No file in this upstream range is a suffix match "
                    "for any target of our `patches/{weewx,extensions,venv}/"
                    "*.patch` files."
                ),
                "",
            ]

    # Install-manifest cross-check (extension bumps only).
    if r["source_file"] == "build/extensions.txt" and r["kind"] == "github_archive":
        new_url = f"https://github.com/{r['source_repo']}/archive/{r['new_ref']}.zip"
        install_paths = ext_manifest.get(new_url, [])
        ctx_lines += [
            "## Extension install manifest (from `build/extensions.txt`)",
            "",
            (
                "These are the paths the extension is expected to produce -- "
                "asserted at build time by `build/check_image.sh`. If the "
                "upstream range renamed or removed any of them, the build "
                "will fail."
            ),
            "",
        ]
        for ip in install_paths:
            ctx_lines.append(f"- `# install: {ip}`")
        if install_hits:
            structural = install_hits_structural(install_hits)
            if structural:
                ctx_lines += [
                    "",
                    (
                        ":rotating_light: **install-path STRUCTURAL changes "
                        "(added / removed / renamed) upstream:**"
                    ),
                    "",
                ]
                for ip, matches in structural:
                    for f, status in matches:
                        ctx_lines.append(f"- `{ip}` <=> `{f}` ({status})")
            ctx_lines += [
                "",
                "Files under an install: path that were modified (normal churn):",
                "",
            ]
            for ip, matches in install_hits:
                for f, status in matches:
                    if status in STRUCTURAL_STATUSES:
                        continue
                    ctx_lines.append(f"- `{ip}` <=> `{f}` ({status})")
        else:
            ctx_lines += [
                "",
                (
                    "No install-path change detected in this upstream range "
                    "(mechanically verified: no changed file suffix-matches "
                    "any `# install:` path)."
                ),
            ]
        ctx_lines.append("")

        # Only fire the alarm on structural changes (add/remove/rename).
        # A plain "modified" is normal churn; the patch intersection already
        # surfaces any modification we care about.
        structural = install_hits_structural(install_hits)
        if structural:
            lines += [
                "",
                (
                    ":rotating_light: **Install-manifest STRUCTURAL change: "
                    "extension's `# install:` paths were added / removed / "
                    "renamed upstream.** `build/check_image.sh` will fail the "
                    "build if the expected path is gone. See "
                    "`our-side-context.md`."
                ),
            ]

    if weewx_data_hits:
        lines += [
            "",
            (
                ":rotating_light: **weewx core: `src/weewx_data/` / `src/schemas/` "
                "changed.** These ship in our container (skins, archive schema)."
            ),
            "",
            "| upstream file | status |",
            "|---|---|",
        ]
        for f, status in weewx_data_hits:
            lines.append(
                f"| [`{f}`](https://github.com/{r['source_repo']}/blob/"
                f"{r['new_ref']}/{f}) | `{status}` |"
            )
        ctx_lines += [
            "## `src/weewx_data/` and `src/schemas/` changes",
            "",
            (
                "These trees ship in the container's `/opt/weewx-data/skins/` "
                "and the archive schema. Not pure library churn."
            ),
            "",
        ]
        for f, status in weewx_data_hits:
            ctx_lines.append(f"- `{f}` ({status})")
        ctx_lines.append("")

    write_file(d / "our-side-context.md", "\n".join(ctx_lines))
    lines.append("")
    return "\n".join(lines)


# ---- main -----------------------------------------------------------------


def summarize_our_patches(our_patches):
    """A compact table for the briefing top-matter."""
    rows = ["| patch | targets |", "|---|---|"]
    for patch_rel, targets in our_patches.items():
        rows.append(
            f"| `{patch_rel}` | {', '.join(f'`{t}`' for t in targets) or '(none)'} |"
        )
    return "\n".join(rows)


def build_hits_summary(sections_data):
    """Cross-pin hits table for the briefing top-matter.

    Each row: which pin bump hit which of our patches. Empty = no intersection
    across the whole PR.
    """
    rows = []
    for r, patch_hits, install_hits, weewx_data_hits in sections_data:
        if patch_hits:
            for patch_rel, target, upstream_file, status in patch_hits:
                rows.append(
                    f"| `{r['depName']}` | `{patch_rel}` | `{target}` | "
                    f"`{upstream_file}` | `{status}` | patch intersection |"
                )
        # Only include STRUCTURAL install-manifest hits in the summary table;
        # a plain "modified" is normal churn and would drown the useful signal.
        for ip, matches in install_hits_structural(install_hits):
            for f, status in matches:
                rows.append(
                    f"| `{r['depName']}` | (extensions.txt) | "
                    f"`# install: {ip}` | `{f}` | `{status}` | "
                    "install manifest (structural) |"
                )
        if weewx_data_hits:
            for f, status in weewx_data_hits:
                rows.append(
                    f"| `{r['depName']}` | (weewx core) | `src/weewx_data/` or "
                    f"`src/schemas/` | `{f}` | `{status}` | ships in our container |"
                )
    if not rows:
        return (
            "No mechanical hit across this PR (no patch intersection, no "
            "install-manifest change, no `src/weewx_data/` movement).\n\n"
            "That is strong evidence of low impact -- still skim commit "
            "subjects for behaviours the mechanical analysis cannot see "
            "(config-schema changes, new required options, s6 service "
            "interactions, telemetry-name changes)."
        )
    return "\n".join(
        [
            "| pin | our patch / manifest | our target | upstream file | status | class |",
            "|---|---|---|---|---|---|",
            *rows,
        ]
    )


def main():
    if len(sys.argv) < 4:
        sys.exit(f"usage: {sys.argv[0]} <base-ref> <head-ref> <out-dir>")
    base, head = sys.argv[1], sys.argv[2]
    out = Path(sys.argv[3])
    token = os.environ.get("GITHUB_TOKEN", "")

    # Repo root (script lives at .github/scripts/): needed to find patches/
    # and build/extensions.txt from the workspace regardless of CWD.
    repo_root = Path(__file__).resolve().parents[2]

    # Consume what the resolve step ALREADY worked out (kind, source_repo,
    # compare payload). Re-deriving it here would mean a second compare API
    # call per pin, in the same job. Falls back to a fresh resolve if we're
    # running standalone (local replay).
    resolved = []
    rj = os.environ.get("RESOLVED_JSON")
    if rj and Path(rj).exists():
        resolved = json.loads(Path(rj).read_text())
    else:
        for path in TRACKED_FILES:
            diff_text = diff_of(base, head, path)
            if not diff_text.strip():
                continue
            old_pins = _pins_in_side(diff_text, path, "-")
            new_pins = _pins_in_side(diff_text, path, "+")
            for kind, key, old, new in _pair_up(old_pins, new_pins):
                r = resolve(kind, key, old, new, token)
                r["source_file"] = path
                resolved.append(r)

    if not resolved:
        return

    our_patches = scan_our_patches(repo_root)
    ext_manifest = parse_extensions_manifest(repo_root)

    sections = []
    sections_data = []
    for r in resolved:
        # A resolved.json produced by an OLDER resolver might not carry the
        # source_file field. Fall back to "(unknown)" rather than KeyError'ing.
        r.setdefault("source_file", "(unknown)")
        src_diff = diff_of(base, head, r["source_file"])
        section_md = stage_upstream(out, r, token, our_patches, ext_manifest, src_diff)
        sections.append(section_md)

        patch_hits = find_patch_hits(our_patches, r["files"]) if r["files"] else []
        install_hits = []
        weewx_data_hits = []
        if (
            r["source_file"] == "build/extensions.txt"
            and r["kind"] == "github_archive"
            and r["files"]
        ):
            new_url = (
                f"https://github.com/{r['source_repo']}/archive/{r['new_ref']}.zip"
            )
            install_hits = find_install_hits(ext_manifest.get(new_url, []), r["files"])
        if r["source_repo"] == "weewx/weewx" and r["files"]:
            for f, meta in r["files"].items():
                if f.startswith(("src/weewx_data/", "src/schemas/")):
                    weewx_data_hits.append((f, meta["status"]))
        sections_data.append((r, patch_hits, install_hits, weewx_data_hits))

    index = [
        "## Mechanical briefing",
        "",
        (
            "_Computed, not inferred. The patch-target intersection, the "
            "extension install-manifest cross-check, and the weewx `src/weewx_data/` "
            "flagging are set arithmetic over our patches/manifest and the "
            "upstream compare API. The bulk (full patches, whole before/after "
            "files, commit lists) is PREFETCHED to disk — read only what you "
            "need with Read/Grep. You need no network._"
        ),
        "",
        "### Pins in this PR",
        "",
        "| dep | old → new | source file |",
        "|---|---|---|",
    ]
    for r in resolved:
        index.append(
            f"| `{r['depName']}` ({r['kind']}) | "
            f"`{r['old_display']}` → `{r['new_display']}` | "
            f"`{r['source_file']}` |"
        )
    index += [
        "",
        "### Hits (this PR × our patches / manifest)",
        "",
        build_hits_summary(sections_data),
        "",
        "### Our patches (inventory)",
        "",
        summarize_our_patches(our_patches),
        "",
        "### Per-pin sections",
        "",
    ]
    index.extend(sections)
    write_file(out / "briefing.md", "\n".join(index))
    print(f"wrote {out}/briefing.md and prefetched upstream data", file=sys.stderr)


if __name__ == "__main__":
    main()
