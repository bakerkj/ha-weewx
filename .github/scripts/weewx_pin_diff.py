#!/usr/bin/env python3
# Copyright (c) 2026 Kenneth Baker <bakerkj@umich.edu>
# All rights reserved.

# Copyright (c) 2026 Kenneth J Baker <bakerkj@umich.edu>
#
# Render the UPSTREAM source diff for a Renovate bump on ha-weewx.
#
# Renovate cannot do this itself. A ha-weewx bump PR carries only opaque
# pin lines: a docker digest change, a version=/==, a `github.com/.../archive/
# <ref>.zip` swap, or an `ARG *_REF=<sha>` update. Renovate never resolves
# any of that to the upstream commit range it represents -- its PR shows
# `f986374 -> 54531eb`, `v5.4.0 -> v5.5.0`, or nothing at all, and nothing
# else.
#
# This script parses the PR diff for the FOUR files Renovate is allowed to
# touch in ha-weewx (Dockerfile, pyproject.toml, build/extensions.txt,
# build/install_rtgd.py), classifies each changed pin by its shape, and
# resolves each shape to a real `compare/<old>...<new>` link + commit list.
#
# Shapes handled (see PIN_SHAPES table in the code):
#   1. pypi `weewx==X.Y.Z`                       -> weewx/weewx  vX.Y.Z compare
#   2. `github.com/.../archive/<tag>.zip`        -> owner/repo   tag compare
#   3. `github.com/.../archive/<sha>.zip`        -> owner/repo   sha compare
#   4. `raw.githubusercontent.com/.../<ref>/...` -> owner/repo   ref compare
#   5. `ARG <NAME>_REF=<sha>`                    -> mapping table -> sha compare
#   6. docker digest FROM <image>:<tag>@sha256   -> OCI labels   compare, or
#                                                    note-only (plain debian)
#   7. `ghcr.io/astral-sh/uv:<ver>` bind-mount   -> note-only (no source repo)
#   +  pyproject `[tool.uv] required-version`    -> sister of #7, note-only
#
# Usage:  weewx_pin_diff.py <base-ref> <head-ref>
# Writes markdown to stdout (empty if no tracked pin changed).
# Dumps the resolved payload to $RESOLVED_JSON when set (consumed by
# weewx_pin_briefing.py so the briefing step never re-runs the resolution).

import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

# The four files Renovate is allowed to touch in ha-weewx. Anything outside this
# set is not classified: if a real pin ever appears elsewhere, add it here (and
# to the workflow's `paths:` filter) rather than silently ignoring it.
TRACKED_FILES = [
    "Dockerfile",
    "pyproject.toml",
    "build/extensions.txt",
    "build/install_rtgd.py",
]

# ---- pin-shape regexes ----------------------------------------------------
#
# Each regex matches ONE pin shape. All are anchored to shapes Renovate's
# customManagers in renovate.json actually emit. Adding a new managed shape
# to renovate.json REQUIRES a matching addition here -- otherwise a resolver
# gap silently degrades to "no upstream analysis" for that class of PR.

# 1. pypi `weewx==X.Y.Z` in pyproject.toml.
PYPI_WEEWX_RE = re.compile(r'"weewx==(?P<ver>[\w.]+)"')

# 2/3. `github.com/<owner>/<repo>/archive/<ref>.zip` in Dockerfile, pyproject.toml,
#      build/extensions.txt and build/install_rtgd.py. `ref` is either a tag
#      (typically [vV]?N.N.N...) or a 7-40 hex SHA -- classified downstream.
GITHUB_ARCHIVE_RE = re.compile(
    r"github\.com/(?P<owner>[\w.-]+)/(?P<repo>[\w.-]+)/archive/"
    r"(?P<ref>[^/\"'\s]+?)\.zip"
)

# 4. `raw.githubusercontent.com/<owner>/<repo>/<ref>/<path>` in Dockerfile
#    (xstats.py ADD). Same-shape compare on refs.
RAW_GITHUB_RE = re.compile(
    r"raw\.githubusercontent\.com/(?P<owner>[\w.-]+)/(?P<repo>[\w.-]+)/"
    r"(?P<ref>[^/\s]+)/(?P<path>[^\s\"']+)"
)

# 5. `ARG <NAME>_REF=<sha>` in Dockerfile. The mapping from ARG name to source
#    repo is EXPLICIT (ARG_REF_MAP below) -- an unknown name resolves to
#    "unknown source" rather than a guess, which is the correct failure mode
#    for a shape whose meaning is not in the line itself.
ARG_REF_RE = re.compile(
    r"^\s*ARG\s+(?P<name>[A-Z][A-Z0-9_]*_REF)=(?P<sha>[0-9a-f]{7,40})\s*$",
    re.MULTILINE,
)
ARG_REF_MAP = {
    # ARG RTLDAVIS_REF=<sha> -> the Go binary we compile in the rtldavis-builder
    # stage. Upstream has no release tags; Renovate tracks git-refs/master.
    "RTLDAVIS_REF": "lheijst/rtldavis",
}

# 6. `<image>:<tag>@sha256:<64 hex>` in Dockerfile FROM lines (and in a plain
#    BUILD_FROM ARG). Same shape as aviation-feeder.
IMAGE_RE = re.compile(
    r"(?P<image>[a-z0-9.-]+\.[a-z]{2,}/[a-z0-9._/-]+|debian)"
    r":(?P<tag>[\w][\w.-]*)"
    r"@(?P<digest>sha256:[0-9a-f]{64})"
)

# 7. `--mount=from=ghcr.io/astral-sh/uv:<ver>` bind-mount in Dockerfile. This
#    line has NO digest -- it's a plain tag pin. uv is a Rust binary shipped
#    via docker + PyPI; we deliberately do not resolve it to a commit range
#    (the release notes are what the reviewer wants for a uv bump).
UV_DOCKER_RE = re.compile(r"astral-sh/uv:(?P<ver>[\d.][\w.]*)")

# 8. pyproject [tool.uv] `required-version = "==X.Y.Z"` -- sister pin of #7,
#    grouped by Renovate. Note-only, no source range to resolve.
UV_PYPROJECT_RE = re.compile(
    r'required-version\s*=\s*"(?P<op>==|>=|<=|~=)?(?P<ver>[^"]+)"'
)

# Known pypi-name -> github source-repo mappings. Kept small and explicit: the
# only pypi package Renovate is allowed to bump in a way that reaches the image
# is `weewx` itself (see the [project].dependencies MANUAL REVIEW rule in
# renovate.json), so a mapping table is enough and beats a network lookup.
PYPI_TO_GITHUB = {
    "weewx": "weewx/weewx",
}


def run(*args, fatal=False):
    """Run a command. Returns stdout, or None on failure.

    A silently-swallowed failure here is the worst outcome: a broken `git diff`
    or `imagetools inspect` would render as "no upstream changes" / "no
    revision label" and quietly lie in the review comment. So a failure is
    always surfaced -- fatally for the diff (without it we know nothing),
    loudly for an inspect (that image is reported as un-inspectable).
    """
    proc = subprocess.run(args, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        err = (proc.stderr or "").strip().splitlines()
        detail = err[-1] if err else "(no stderr)"
        msg = f"`{' '.join(args[:4])} …` exited {proc.returncode}: {detail}"
        if fatal:
            sys.exit(f"error: {msg}")
        print(f"warning: {msg}", file=sys.stderr)
        return None
    return proc.stdout


def diff_of(base, head, path):
    """Unified diff of a single file between BASE and HEAD, or '' if absent.

    Absent (never in either rev) is normal -- pyproject.toml has no weewx pin
    on a PR that only bumps an extension SHA. `git diff` on a path that
    doesn't exist in EITHER rev exits 0 with empty output, and that is what
    we want; we do not want to fail fatally there.
    """
    out = run("git", "diff", f"{base}...{head}", "--", path)
    return out or ""


# ---- pin extraction ------------------------------------------------------


def _lines(diff_text, sign):
    """Return lines of a git diff prefixed with `sign` ('-' or '+'), WITH THE
    SIGN STRIPPED, skipping the diff-header lines (`---`, `+++`).

    Stripping the sign matters for any pin regex that anchors to line start
    (`^\\s*ARG ...`, for one) -- if we left the sign on, `^\\s*` would need to
    match zero characters and then the next char is `-` or `+`, and the anchor
    fails. Regexes using `.search()` / `.finditer()` do not care either way,
    but consistency across shapes is safer than remembering which regex
    happens to be line-anchored.
    """
    out = []
    for line in diff_text.splitlines():
        if not line.startswith(sign) or line.startswith(sign * 3):
            continue
        out.append(line[1:])
    return out


def _classify_archive_ref(ref):
    """Return 'sha' for a 7-40 hex commit, else 'tag'.

    The tag test intentionally MATCHES first only when the ref is NOT purely
    hex, because some upstream tags happen to be all-hex (unlikely for weewx
    extensions, but possible in principle). Real observed tags in extensions.txt
    include v5.0.1, 4.4, V0.3 -- all contain non-hex characters or dots that a
    pure hex test rejects.
    """
    if re.fullmatch(r"[0-9a-f]{7,40}", ref):
        return "sha"
    return "tag"


def _pins_in_side(diff_text, path, sign):
    """Extract every pin present on `sign` ('-' or '+') lines for one file.

    Returns a list of (kind, key, value_dict). `key` is what pairs the '-'
    and '+' occurrences of the SAME pin -- e.g. depName='owner/repo' for a
    github archive URL, or 'weewx' for the pypi pin. The value_dict holds
    everything the resolver needs downstream.
    """
    lines = _lines(diff_text, sign)
    text = "\n".join(lines)
    pins = []

    if path == "pyproject.toml":
        for m in PYPI_WEEWX_RE.finditer(text):
            pins.append(("pypi", "weewx", {"ver": m.group("ver")}))
        for m in UV_PYPROJECT_RE.finditer(text):
            pins.append(
                ("uv_pyproject", "uv", {"ver": m.group("ver"), "op": m.group("op")})
            )

    if path == "Dockerfile":
        for m in ARG_REF_RE.finditer(text):
            name = m.group("name")
            pins.append(
                ("arg_ref", name, {"sha": m.group("sha"), "arg_name": name}),
            )
        for m in UV_DOCKER_RE.finditer(text):
            pins.append(("uv_docker", "ghcr.io/astral-sh/uv", {"ver": m.group("ver")}))
        for m in IMAGE_RE.finditer(text):
            image = m.group("image")
            pins.append(
                (
                    "docker_digest",
                    image,
                    {
                        "image": image,
                        "tag": m.group("tag"),
                        "digest": m.group("digest"),
                    },
                ),
            )
        for m in RAW_GITHUB_RE.finditer(text):
            depname = f"{m.group('owner')}/{m.group('repo')}"
            pins.append(
                (
                    "raw_github",
                    depname,
                    {
                        "owner": m.group("owner"),
                        "repo": m.group("repo"),
                        "ref": m.group("ref"),
                        "path": m.group("path"),
                    },
                ),
            )

    # github archive URLs can appear in ALL four files -- extensions.txt,
    # install_rtgd.py, pyproject.toml (felddy weewx-home-assistant) and
    # Dockerfile.
    for m in GITHUB_ARCHIVE_RE.finditer(text):
        depname = f"{m.group('owner')}/{m.group('repo')}"
        ref = m.group("ref")
        pins.append(
            (
                "github_archive",
                depname,
                {
                    "owner": m.group("owner"),
                    "repo": m.group("repo"),
                    "ref": ref,
                    "ref_kind": _classify_archive_ref(ref),
                },
            ),
        )
    return pins


def _pair_up(old_pins, new_pins):
    """Pair '-' side pins with their '+' side counterparts by (kind, key).

    A pin present on both sides with the SAME value is a no-op (context
    line dedup); drop it. A pin present on only one side is add/remove --
    return the missing side as None so the caller can format that.
    """
    old_by_key = {}
    new_by_key = {}
    for kind, key, val in old_pins:
        old_by_key[(kind, key)] = val
    for kind, key, val in new_pins:
        new_by_key[(kind, key)] = val

    pairs = []
    for k in sorted(set(old_by_key) | set(new_by_key)):
        old = old_by_key.get(k)
        new = new_by_key.get(k)
        if old == new:
            continue
        pairs.append((k[0], k[1], old, new))
    return pairs


# ---- resolvers per shape --------------------------------------------------


def labels_for(image, digest):
    """OCI labels for a digest, or None if the image could not be inspected.

    Cribbed from renovate_image_diff.py in hass-aviation-feeder. None is
    deliberately DIFFERENT from {} (inspected fine, but no labels) so a
    toolchain failure is never reported as "this image has no revision label".
    """
    raw = run(
        "docker",
        "buildx",
        "imagetools",
        "inspect",
        f"{image}@{digest}",
        "--format",
        "{{json .Image}}",
    )
    if raw is None:
        return None
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        print(
            f"warning: {image}@{digest[:19]} inspect returned non-JSON",
            file=sys.stderr,
        )
        return None
    if isinstance(data, dict) and "config" in data:
        return (data.get("config") or {}).get("Labels") or {}
    # multi-arch: {"linux/amd64": {...}, ...} -- any platform's labels will do.
    if isinstance(data, dict):
        for entry in data.values():
            lab = (entry or {}).get("config", {}).get("Labels") or {}
            if lab:
                return lab
    return {}


def gh_compare(repo_path, old, new, token):
    """GitHub compare API -> (commit_count, [subjects], {file: {patch,status}}).

    (None, [], {}) on failure. Keeps STATUS so a DELETED upstream file is not
    misreported as an added one -- important for the patch-intersection story
    (an upstream removal of a file we patch is different news from a modification).
    """
    url = f"https://api.github.com/repos/{repo_path}/compare/{old}...{new}"
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json"})
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.load(r)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        print(
            f"warning: compare {repo_path} {old[:7]}...{new[:7]} failed: {exc}",
            file=sys.stderr,
        )
        return None, [], {}
    subjects = [c["commit"]["message"].splitlines()[0] for c in data.get("commits", [])]
    files = {
        f["filename"]: {
            "patch": f.get("patch") or "",
            "status": f.get("status") or "modified",
        }
        for f in data.get("files", [])
    }
    return data.get("total_commits"), subjects, files


def _weewx_tag(ver):
    """weewx repo tags are `vX.Y.Z`; the pypi pin is bare (`X.Y.Z`)."""
    return f"v{ver}"


def resolve(kind, key, old, new, token):
    """Return a resolved dict for one pin bump.

    Every branch returns the same keys so the JSON dumped to $RESOLVED_JSON is
    uniform (the briefing consumes it without switching on kind). Fields:
        depName, kind, source_repo (or None), old_ref, new_ref, compare_url,
        old_display, new_display, note (a short human note when we deliberately
        did not resolve), commit_count, subjects, files
    """
    r = {
        "depName": key,
        "kind": kind,
        "source_repo": None,
        "old_ref": None,
        "new_ref": None,
        "compare_url": None,
        "old_display": None,
        "new_display": None,
        "note": None,
        "commit_count": None,
        "subjects": [],
        "files": {},
    }
    # Add / remove -- the pin appeared or disappeared. We can't compare a
    # single side, so report it plainly rather than fabricate a range.
    if old is None or new is None:
        r["old_display"] = _display(kind, old) if old else "(added)"
        r["new_display"] = _display(kind, new) if new else "(removed)"
        r["note"] = (
            "pin was added" if old is None else "pin was removed"
        ) + " -- no old-vs-new range to compute."
        return r

    if kind == "pypi":
        if key not in PYPI_TO_GITHUB:
            r["note"] = f"no known GitHub source repo for pypi package `{key}`."
            r["old_display"] = old["ver"]
            r["new_display"] = new["ver"]
            return r
        repo = PYPI_TO_GITHUB[key]
        old_ref, new_ref = _weewx_tag(old["ver"]), _weewx_tag(new["ver"])
        r.update(
            source_repo=repo,
            old_ref=old_ref,
            new_ref=new_ref,
            compare_url=f"https://github.com/{repo}/compare/{old_ref}...{new_ref}",
            old_display=old["ver"],
            new_display=new["ver"],
        )

    elif kind == "github_archive":
        repo = key  # owner/repo
        old_ref, new_ref = old["ref"], new["ref"]
        r.update(
            source_repo=repo,
            old_ref=old_ref,
            new_ref=new_ref,
            compare_url=f"https://github.com/{repo}/compare/{old_ref}...{new_ref}",
            old_display=_short(old_ref, old["ref_kind"]),
            new_display=_short(new_ref, new["ref_kind"]),
        )

    elif kind == "raw_github":
        repo = key
        old_ref, new_ref = old["ref"], new["ref"]
        r.update(
            source_repo=repo,
            old_ref=old_ref,
            new_ref=new_ref,
            compare_url=f"https://github.com/{repo}/compare/{old_ref}...{new_ref}",
            old_display=old_ref,
            new_display=new_ref,
        )

    elif kind == "arg_ref":
        repo = ARG_REF_MAP.get(key)
        if not repo:
            r["note"] = f"no source-repo mapping for ARG `{key}`."
            r["old_display"] = old["sha"][:7]
            r["new_display"] = new["sha"][:7]
            return r
        old_ref, new_ref = old["sha"], new["sha"]
        r.update(
            source_repo=repo,
            old_ref=old_ref,
            new_ref=new_ref,
            compare_url=f"https://github.com/{repo}/compare/{old_ref}...{new_ref}",
            old_display=old_ref[:7],
            new_display=new_ref[:7],
        )

    elif kind == "docker_digest":
        image = key
        # Two different treatments -- see the module-level PIN_SHAPES notes.
        # `debian` (from Docker Hub) has no git provenance labels; we do not
        # try to invent one. The base-debian image DOES carry OCI labels
        # (org.opencontainers.image.source) we can read via `imagetools inspect`.
        r["old_display"] = f"{old['tag']}@{old['digest'][7:19]}"
        r["new_display"] = f"{new['tag']}@{new['digest'][7:19]}"
        if image == "debian":
            r["note"] = (
                "plain `debian` image (Docker Hub); no git provenance labels. "
                "Read the Debian security tracker for CVE context."
            )
            return r
        old_lab = labels_for(image, old["digest"])
        new_lab = labels_for(image, new["digest"])
        if old_lab is None or new_lab is None:
            r["note"] = (
                "could not inspect image (docker buildx imagetools inspect failed) "
                "-- upstream range unresolved."
            )
            return r
        source = new_lab.get("org.opencontainers.image.source") or ""
        old_rev = old_lab.get("org.opencontainers.image.revision")
        new_rev = new_lab.get("org.opencontainers.image.revision")
        if not (source.startswith("https://github.com/") and old_rev and new_rev):
            r["note"] = (
                "image has no `org.opencontainers.image.source` + `.revision` "
                "OCI labels; upstream range unresolved."
            )
            return r
        repo = source[len("https://github.com/") :].rstrip("/")
        r.update(
            source_repo=repo,
            old_ref=old_rev,
            new_ref=new_rev,
            compare_url=f"https://github.com/{repo}/compare/{old_rev}...{new_rev}",
        )

    elif kind == "uv_docker":
        r["old_display"] = old["ver"]
        r["new_display"] = new["ver"]
        r["note"] = (
            "uv is a Rust binary distributed via docker + PyPI; no upstream "
            "git range is resolved for its bumps -- read the release notes at "
            "https://github.com/astral-sh/uv/releases."
        )

    elif kind == "uv_pyproject":
        r["old_display"] = old["ver"]
        r["new_display"] = new["ver"]
        r["note"] = (
            "sister pin of the Dockerfile ghcr.io/astral-sh/uv:<ver> bind-mount; "
            "the two must move together (`uv sync --frozen` refuses on mismatch)."
        )

    else:
        r["note"] = f"unknown pin kind `{kind}`; nothing resolved."
        return r

    # Compare API -- the SAME response gives us subjects AND the diff of every
    # changed file, so the briefing step does not need to re-call it.
    if r["source_repo"] and r["old_ref"] and r["new_ref"]:
        count, subjects, files = gh_compare(
            r["source_repo"], r["old_ref"], r["new_ref"], token
        )
        r["commit_count"] = count
        r["subjects"] = subjects
        r["files"] = files
        # gh_compare returns (None, [], {}) on failure. Left unmarked, that is
        # indistinguishable downstream from a genuinely empty range, and the
        # briefing's install-manifest section would print a false "mechanically
        # verified: no change" claim for an extension bump whose fetch never
        # actually ran. Mark the failure explicitly so the briefing can see it.
        if count is None:
            r["note"] = (
                "GitHub compare API call failed -- commit/file list "
                "unavailable (see workflow log). This is NOT evidence of "
                'an empty range; do not treat it as "no upstream changes".'
            )
    return r


def _short(ref, kind):
    return ref[:7] if kind == "sha" else ref


def _display(kind, val):
    if val is None:
        return None
    if kind == "pypi":
        return val["ver"]
    if kind == "github_archive":
        return _short(val["ref"], val["ref_kind"])
    if kind == "raw_github":
        return val["ref"]
    if kind == "arg_ref":
        return val["sha"][:7]
    if kind == "docker_digest":
        return f"{val['tag']}@{val['digest'][7:19]}"
    if kind in ("uv_docker", "uv_pyproject"):
        return val["ver"]
    return "?"


# ---- markdown emission ----------------------------------------------------


KIND_LABELS = {
    "pypi": "pypi",
    "github_archive": "github archive",
    "raw_github": "raw github file",
    "arg_ref": "Dockerfile ARG",
    "docker_digest": "docker digest",
    "uv_docker": "docker (uv build tool)",
    "uv_pyproject": "pyproject (uv)",
}


def markdown(resolved):
    """Render one row per resolved pin, plus a per-pin commit-subject block."""
    if not resolved:
        return ""
    rows, details = [], []
    for r in resolved:
        change = f"`{r['old_display']}` → `{r['new_display']}`"
        if r.get("compare_url") and r.get("commit_count") is not None:
            link = f"[{r['old_display']}…{r['new_display']}]({r['compare_url']})"
            rows.append(
                f"| `{r['depName']}` | {KIND_LABELS.get(r['kind'], r['kind'])} "
                f"| {change} | {r['commit_count']} | {link} |"
            )
            if r["subjects"]:
                body = "\n".join(f"- {s}" for s in r["subjects"][:20])
                more = "\n- …" if len(r["subjects"]) > 20 else ""
                details.append(
                    f"<details><summary><code>{r['depName']}</code> — "
                    f"{r['commit_count']} commit(s)</summary>\n\n{body}{more}\n\n"
                    "</details>"
                )
        else:
            note = r.get("note") or "no upstream range resolved."
            rows.append(
                f"| `{r['depName']}` | {KIND_LABELS.get(r['kind'], r['kind'])} "
                f"| {change} | — | :grey_question: {note} |"
            )
    out = [
        "### Upstream changes in this bump",
        "",
        "| dep | kind | version | commits | diff |",
        "|---|---|---|---|---|",
        *rows,
    ]
    if details:
        out.append("")
        out.append("\n\n".join(details))
    out.append("")
    out.append(
        "<sub>Resolved from each pin's shape (tag, SHA, docker digest, "
        "raw file ref) — Renovate can't produce this on its own.</sub>"
    )
    return "\n".join(out) + "\n"


def main():
    if len(sys.argv) < 3:
        sys.exit(f"usage: {sys.argv[0]} <base-ref> <head-ref>")
    base, head = sys.argv[1], sys.argv[2]
    token = os.environ.get("GITHUB_TOKEN", "")

    all_resolved = []
    for path in TRACKED_FILES:
        diff_text = diff_of(base, head, path)
        if not diff_text.strip():
            continue
        old_pins = _pins_in_side(diff_text, path, "-")
        new_pins = _pins_in_side(diff_text, path, "+")
        for kind, key, old, new in _pair_up(old_pins, new_pins):
            r = resolve(kind, key, old, new, token)
            r["source_file"] = path
            all_resolved.append(r)

    # Deduplicate: the SAME pin can legally show up in two files (e.g. weewx
    # in pyproject.toml + xstats.py's ref in the Dockerfile). Renovate groups
    # them into one PR but the resolver visits them per-file. Collapse by
    # (kind, depName, source_file) to keep one row per touched file so the
    # reader still sees which files bumped.
    seen = set()
    unique = []
    for r in all_resolved:
        key = (r["kind"], r["depName"], r.get("source_file"))
        if key in seen:
            continue
        seen.add(key)
        unique.append(r)

    dump = os.environ.get("RESOLVED_JSON")
    if dump:
        with open(dump, "w", encoding="utf-8") as fh:
            json.dump(unique, fh)

    md = markdown(unique)
    if md:
        sys.stdout.write(md)


if __name__ == "__main__":
    main()
