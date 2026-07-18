# Copyright (c) 2026 Kenneth Baker <bakerkj@umich.edu>
# All rights reserved.
"""ReportHook: run a subprocess when a skin's report cycle finishes.

Slots into a skin's ``[Generators] generator_list`` after the generators
whose output the command depends on (usually CheetahGenerator + any
Copy/ImageGenerator). WeeWX runs generators in list order within a single
report thread, so the command fires exactly when everything before it has
completed for that skin — no polling, no cross-thread coordination.

The command is executed as an **argv list** (``subprocess.run(argv,
shell=False)``) — no shell, no injection surface, no accidental glob
expansion. Each argv element is passed through ``os.path.expandvars`` so
``$TOKEN`` / ``${TOKEN}`` still substitute from the subprocess env, which
is preloaded with the process's own env plus every ``env_*`` config entry.

Configuration lives under the skin's ``[ReportHook]`` block. WeeWX's configobj
parses a comma-separated ``command = a, b, c`` line as a Python list, which
is exactly the argv shape this module wants:

    [StdReport]
        [[MySkin]]
            [[[ReportHook]]]
                command = curl, -fsS, -X, POST,
                          -H, "Authorization: Bearer $TOKEN",
                          https://example.com/hook
                env_TOKEN = xyz-secret

    [Generators]
        generator_list = weewx.cheetahgenerator.CheetahGenerator, \\
                         user.report_hook.ReportHook

Options (all optional except ``command``; empty/missing ``command`` is a
disabled no-op so the module is safe to leave in the generator_list):

    command      argv list, first element is the executable (looked up on
                 PATH). Empty or missing = disabled. Each element runs
                 through ``expandvars`` at runtime.
    frequency    ``once`` (fire once per addon boot, tracked by a marker
                 file in /tmp) or ``every`` (default: every report cycle).
    timeout      Command timeout in seconds. Default: 10.
    verify_file  Optional path; if set, the command runs only when this
                 file exists and is non-empty. Cheetah catches per-template
                 exceptions, so "our generator ran" alone doesn't prove a
                 successful publish — this closes the gap.
    env_<NAME>   Any option whose key starts with ``env_`` becomes an env
                 var passed to the command with the prefix stripped, e.g.
                 ``env_TOKEN = xyz`` makes ``$TOKEN`` available for
                 expandvars substitution into argv elements. Keeps secrets
                 in their own config line for rotation / grep.

HA add-on integration: at run time the module also reads
``/data/options.json`` (Home Assistant Supervisor writes this file inside
the addon container). Any ``report_hook_*`` key found there overlays the
corresponding ``[ReportHook]`` value from the skin dict — so an operator can
configure everything from the addon's Configuration tab and leave the skin
config empty. In vanilla WeeWX ``/data/options.json`` doesn't exist and
the module behaves exactly as if it weren't there.

Failures (non-zero exit, timeout, spawn error) are logged at WARNING and
never propagate — this is a fire-and-forget hook and must not break the
report cycle.
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
from typing import Any

from weeutil.weeutil import to_int
from weewx.reportengine import ReportGenerator

log = logging.getLogger(__name__)

# Marker files for ``frequency = once`` live in /tmp so container restart
# resets the "already fired" state — which matches the intended semantic
# ("run once per addon boot").
MARKER_DIR = "/tmp"

# HA Supervisor writes the addon's options here inside the container.
# The path is a class-level constant so tests can point it at tmp_path.
HA_OPTIONS_PATH = "/data/options.json"

# Restrict marker-file basenames to safe filesystem characters. WeeWX skin
# names are conventionally CamelCase / snake_case, so a permissive [\w.-]
# filter is more than enough; anything else collapses to underscore.
_SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]")

# ``os.path.expandvars`` grammar, replicated so we can substitute against a
# caller-supplied env dict instead of touching ``os.environ`` — mutating
# ``os.environ`` would race with the main WeeWX engine thread that runs
# concurrently to the report thread. ``re.ASCII`` matches stdlib exactly:
# posixpath compiles its own ``_varprog`` with the same flag, so a non-ASCII
# name character (e.g. an accented letter) terminates the match at that
# byte here the same way stdlib does. POSIX env-var names are ASCII.
_VAR_RE = re.compile(r"\$(\w+|\{[^}]*\})", re.ASCII)


def _extract_env(hook_cfg: dict[str, Any]) -> dict[str, str]:
    """Return only the ``env_*`` keys as a ``{NAME: value}`` dict."""
    return {
        k[len("env_") :]: str(v) for k, v in hook_cfg.items() if k.startswith("env_")
    }


def _normalize_argv(raw: Any) -> list[str]:
    """Coerce configobj's ``command`` value into a clean argv list.

    - ``None`` / missing            → ``[]``
    - ``"curl -fsS ..."`` (str)     → single-element list
      (configobj gives a bare string when the user writes no commas)
    - ``["curl", "-fsS", ...]``     → passed through, stringified
    Empty strings and empty list entries are dropped so a trailing comma
    in the config doesn't smuggle in a ``""`` argument.
    """
    if raw is None:
        return []
    if isinstance(raw, str):
        return [raw] if raw.strip() else []
    if isinstance(raw, (list, tuple)):
        return [str(x) for x in raw if str(x).strip() != ""]
    # Anything else (int, dict, ...) is a config error — treat as disabled.
    return []


def _expand_one(s: str, env: dict[str, str]) -> str:
    """Substitute ``$VAR`` and ``${VAR}`` in ``s`` against ``env``.

    Mirrors ``os.path.expandvars`` semantics but reads names from a
    caller-supplied env dict — critical because ``os.environ`` is shared
    with the main WeeWX engine thread, and swapping it out even briefly
    would leak env_* values (typically secrets) into every other running
    subprocess or ``os.environ`` reader for the swap window.

    An unknown name expands to the literal ``$VAR`` / ``${VAR}`` string —
    matching ``os.path.expandvars`` behaviour so an unset variable fails
    loud at the destination (e.g. a webhook 401) rather than silently
    dropping to empty.
    """

    def _sub(m: re.Match[str]) -> str:
        name = m.group(1)
        if name.startswith("{") and name.endswith("}"):
            name = name[1:-1]
        return env.get(name, m.group(0))

    return _VAR_RE.sub(_sub, s)


def _expand_argv(argv: list[str], extra_env: dict[str, str]) -> list[str]:
    """Expand ``$VAR`` / ``${VAR}`` in each argv element against the merged
    env (process env + ``env_*`` entries). Never touches ``os.environ`` —
    all substitutions run against a local dict. See ``_expand_one``.
    """
    merged = {**os.environ, **extra_env}
    return [_expand_one(a, merged) for a in argv]


def _verify_ok(verify_file: str) -> bool:
    """True if the gate path exists and is a non-empty regular file."""
    try:
        return os.path.isfile(verify_file) and os.path.getsize(verify_file) > 0
    except OSError:
        return False


def _run_command(
    argv: list[str],
    timeout: int,
    extra_env: dict[str, str],
) -> tuple[bool, str]:
    """Execute the argv list; return ``(ok, error_summary)``.

    Never raises. On timeout or spawn error, returns ``(False, <reason>)``
    so the caller can log without needing its own try/except.
    """
    env = os.environ.copy()
    env.update(extra_env)
    try:
        r = subprocess.run(
            argv,
            timeout=timeout,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return False, f"timed out after {timeout}s"
    except (OSError, FileNotFoundError) as e:
        # FileNotFoundError is a subclass of OSError; catching both keeps
        # the intent explicit — spawning a nonexistent binary is the same
        # failure class as any other spawn error.
        return False, f"spawn failed: {e}"

    if r.returncode == 0:
        return True, ""
    stderr_snippet = (r.stderr or "").strip().replace("\n", " ")[:500]
    return False, f"exit {r.returncode}: {stderr_snippet}"


def _load_ha_overrides() -> dict[str, Any]:
    """Read ``HA_OPTIONS_PATH`` and return an override dict shaped like
    the ``[ReportHook]`` skin dict.

    - Missing file, unreadable file, or invalid JSON → ``{}`` (silent).
    - Only ``report_hook_*`` keys are considered; the prefix is stripped.
    - ``report_hook_env`` is expected to be a list of ``{"name": ..., "value": ...}``
      dicts (matches the HA options-schema convention for repeated fields)
      and is unrolled into ``env_NAME`` entries so it merges naturally
      with skin-dict env_* keys.
    - Empty / falsy override values are dropped so a blank field in the HA
      UI doesn't clobber a real value in the skin's ``[ReportHook]`` block.
    """
    try:
        with open(HA_OPTIONS_PATH) as f:
            opts = json.load(f)
    except (OSError, ValueError):
        return {}
    if not isinstance(opts, dict):
        return {}

    override: dict[str, Any] = {}
    for k, v in opts.items():
        if not k.startswith("report_hook_"):
            continue
        if v in (None, "", [], {}):
            continue
        override[k[len("report_hook_") :]] = v

    # env is a list of {name, value} in the HA schema — unroll it.
    env_list = override.pop("env", None) or []
    if isinstance(env_list, list):
        for item in env_list:
            if not isinstance(item, dict):
                continue
            name = item.get("name")
            if not name:
                continue
            value = item.get("value")
            override[f"env_{name}"] = "" if value is None else str(value)

    return override


def run_hook(
    hook_cfg: dict[str, Any],
    report_name: str,
) -> str:
    """Core hook logic — pure function around ``hook_cfg``, testable.

    Returns a short string describing what happened (``"disabled"``,
    ``"skipped: <why>"``, ``"ok"``, or ``"failed: <why>"``). Never raises.
    """
    argv = _normalize_argv(hook_cfg.get("command"))
    if not argv:
        return "disabled"

    frequency = str(hook_cfg.get("frequency", "every")).strip().lower()
    timeout = to_int(hook_cfg.get("timeout", 10))
    verify_file = (hook_cfg.get("verify_file") or "").strip()

    # Order matters: check the once-marker BEFORE the verify_file gate. A
    # transiently missing/empty verify_file after we've already fired
    # should stay reported as "once-per-boot already fired", not confuse
    # the user with a stale verify_file warning.
    marker: str | None = None
    if frequency == "once":
        safe = _SAFE_NAME.sub("_", report_name) or "unknown"
        marker = os.path.join(MARKER_DIR, f".weewx-report-hook-{safe}")
        if os.path.exists(marker):
            return "skipped: once-per-boot already fired"

    if verify_file and not _verify_ok(verify_file):
        return f"skipped: verify_file '{verify_file}' missing or empty"

    extra_env = _extract_env(hook_cfg)
    expanded = _expand_argv(argv, extra_env)
    ok, err = _run_command(expanded, timeout, extra_env)

    if not ok:
        return f"failed: {err}"

    if marker:
        try:
            open(marker, "w").close()
        except OSError as e:
            # Best-effort: log but treat the actual command run as success.
            # A missing marker just means "will fire again on next report
            # cycle" — annoying but not broken.
            log.warning(
                "ReportHook[%s]: could not create marker %s: %s", report_name, marker, e
            )

    return "ok"


class ReportHook(ReportGenerator):
    """WeeWX ``ReportGenerator`` that runs a subprocess on each cycle.

    Reads ``[ReportHook]`` from the skin dict, merges any ``report_hook_*`` overrides
    from the addon options file (see ``_load_ha_overrides``), and hands
    off to ``run_hook``. ``run()`` returns nothing and never raises — the
    report thread continues regardless of the outcome.
    """

    def run(self) -> None:
        skin_cfg = dict(self.skin_dict.get("ReportHook", {}) or {})
        ha_cfg = _load_ha_overrides()
        # HA options WIN over skin dict — the addon UI is the intended
        # single source of truth once the operator starts using it.
        hook_cfg = {**skin_cfg, **ha_cfg}

        # skin_dict includes REPORT_NAME (set by StdReportEngine when it
        # walks each skin). Fall back to a stable literal so marker-file
        # collision on the "unknown" bucket is at least deterministic.
        report_name = str(self.skin_dict.get("REPORT_NAME") or "unknown")

        # Belt-and-suspenders: run_hook is designed never to raise, but a
        # future refactor that changes that contract must never take down
        # a report thread. The report engine catches per-generator
        # exceptions and logs them as errors, and the goal here is "zero
        # such logs from this hook".
        try:
            outcome = run_hook(hook_cfg, report_name)
        except Exception as e:
            log.warning("ReportHook[%s]: unexpected error: %s", report_name, e)
            return

        if outcome == "disabled":
            log.debug("ReportHook[%s]: no command configured, skipping", report_name)
        elif outcome.startswith("skipped:"):
            log.debug("ReportHook[%s]: %s", report_name, outcome)
        elif outcome == "ok":
            log.info("ReportHook[%s]: command succeeded", report_name)
        else:  # failed
            log.warning("ReportHook[%s]: %s", report_name, outcome)
