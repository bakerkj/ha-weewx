# Copyright (c) 2026 Kenneth Baker <bakerkj@umich.edu>
# All rights reserved.
"""Behavioural tests for extensions/report_hook.py.

Drives ``run_hook`` directly with fixture-controlled marker + HA-options
directories; ``subprocess`` is real, but every command is an argv list
touching only files under ``tmp_path``, so the tests never hit the network
and never depend on WeeWX's report engine being importable.
"""

from __future__ import annotations

import json
import os

import pytest

import report_hook as hook_module


@pytest.fixture(autouse=True)
def _isolated_paths(tmp_path, monkeypatch):
    """Point every ``.weewx-report-hook-*`` marker at ``tmp_path`` AND redirect
    the HA options-file lookup to a per-test path.

    The module's defaults (``/tmp``, ``/data/options.json``) are the
    production locations; tests substitute per-test paths so parallel
    runs don't clobber each other and no test needs to write to root
    dirs it doesn't own.
    """
    monkeypatch.setattr(hook_module, "MARKER_DIR", str(tmp_path))
    monkeypatch.setattr(hook_module, "HA_OPTIONS_PATH", str(tmp_path / "options.json"))
    return tmp_path


def _write_ha_options(tmp_path, opts):
    (tmp_path / "options.json").write_text(json.dumps(opts))


# --------------------------------------------------------------------------
# _normalize_argv — accept str, list, None; drop empty entries
# --------------------------------------------------------------------------


def test_normalize_argv_none_or_missing_returns_empty():
    assert hook_module._normalize_argv(None) == []
    assert hook_module._normalize_argv("") == []
    assert hook_module._normalize_argv("   ") == []
    assert hook_module._normalize_argv([]) == []


def test_normalize_argv_bare_string_becomes_single_element():
    # configobj gives a bare string when the user writes `command = curl`
    # with no commas — we treat it as a one-element argv rather than
    # word-splitting on spaces (that would resurrect a hidden shell path).
    assert hook_module._normalize_argv("true") == ["true"]


def test_normalize_argv_list_passed_through_and_stringified():
    assert hook_module._normalize_argv(["curl", "-fsS"]) == ["curl", "-fsS"]
    assert hook_module._normalize_argv(["echo", 42]) == ["echo", "42"]


def test_normalize_argv_drops_empty_entries():
    # A trailing comma in the config leaves an empty string — silently
    # dropping it is safer than passing "" as an argv element (which
    # some binaries interpret as an empty positional argument).
    assert hook_module._normalize_argv(["curl", "", "-fsS", "   "]) == ["curl", "-fsS"]


def test_normalize_argv_non_string_container_disables():
    # Anything other than str/list/None is a config error; treat as
    # disabled rather than a runtime crash inside the report thread.
    assert hook_module._normalize_argv({"nope": 1}) == []
    assert hook_module._normalize_argv(42) == []


# --------------------------------------------------------------------------
# disabled / gate paths — never invoke the command
# --------------------------------------------------------------------------


def test_empty_command_is_a_noop():
    assert hook_module.run_hook({}, "MySkin") == "disabled"
    assert hook_module.run_hook({"command": ""}, "MySkin") == "disabled"
    assert hook_module.run_hook({"command": []}, "MySkin") == "disabled"


def test_verify_file_missing_skips(tmp_path):
    missing = tmp_path / "does-not-exist"
    result = hook_module.run_hook(
        {"command": ["true"], "verify_file": str(missing)}, "MySkin"
    )
    assert result.startswith("skipped: verify_file")


def test_verify_file_empty_skips(tmp_path):
    empty = tmp_path / "empty.html"
    empty.write_text("")
    result = hook_module.run_hook(
        {"command": ["true"], "verify_file": str(empty)}, "MySkin"
    )
    assert result.startswith("skipped: verify_file")


def test_verify_file_non_empty_allows(tmp_path):
    ok = tmp_path / "index.html"
    ok.write_text("<html></html>")
    result = hook_module.run_hook(
        {"command": ["true"], "verify_file": str(ok)}, "MySkin"
    )
    assert result == "ok"


# --------------------------------------------------------------------------
# frequency — once vs. every
# --------------------------------------------------------------------------


def test_every_runs_repeatedly(tmp_path):
    sentinel = tmp_path / "hit.txt"
    cmd = ["sh", "-c", f"echo x >> {sentinel}"]
    for _ in range(3):
        assert hook_module.run_hook({"command": cmd}, "MySkin") == "ok"
    assert len(sentinel.read_text().splitlines()) == 3


def test_once_fires_exactly_once(tmp_path):
    sentinel = tmp_path / "hit.txt"
    cmd = ["sh", "-c", f"echo x >> {sentinel}"]
    cfg = {"command": cmd, "frequency": "once"}
    assert hook_module.run_hook(cfg, "MySkin") == "ok"
    assert hook_module.run_hook(cfg, "MySkin") == "skipped: once-per-boot already fired"
    assert hook_module.run_hook(cfg, "MySkin") == "skipped: once-per-boot already fired"
    assert len(sentinel.read_text().splitlines()) == 1


def test_once_marker_is_per_report_name(tmp_path):
    """Attaching the extension to two skins gives each its own marker.

    Prevents a "skin A fires, skin B silently suppressed on the same boot"
    footgun that a shared marker would introduce.
    """
    sentinel = tmp_path / "hit.txt"
    cmd = ["sh", "-c", f"echo x >> {sentinel}"]
    cfg = {"command": cmd, "frequency": "once"}
    assert hook_module.run_hook(cfg, "SkinA") == "ok"
    assert hook_module.run_hook(cfg, "SkinB") == "ok"
    assert len(sentinel.read_text().splitlines()) == 2


def test_once_report_name_with_unsafe_chars_sanitised(tmp_path):
    """A report_name containing path separators must NOT create the marker
    outside the intended MARKER_DIR — i.e., no path traversal via skin
    name. The sanitiser replaces every non-``[A-Za-z0-9._-]`` char with
    ``_``, so the marker lands in tmp_path exactly."""
    cfg = {"command": ["true"], "frequency": "once"}
    assert hook_module.run_hook(cfg, "../evil/name") == "ok"
    markers = [
        p.name for p in tmp_path.iterdir() if p.name.startswith(".weewx-report-hook-")
    ]
    assert markers == [".weewx-report-hook-.._evil_name"]


# --------------------------------------------------------------------------
# env_* / $VAR expansion
# --------------------------------------------------------------------------


def test_env_prefix_exported_to_command(tmp_path):
    """env_TOKEN=xyz in config → $TOKEN available to the child.

    Uses ``sh -c`` INSIDE the argv (the module itself invokes without a
    shell) to demonstrate that the child process sees the env var. The
    expansion path (``$TOKEN`` in an argv element) is tested separately
    below.
    """
    sentinel = tmp_path / "token.txt"
    cfg = {
        "command": ["sh", "-c", f'printf %s "$TOKEN" > {sentinel}'],
        "env_TOKEN": "s3cr3t",
    }
    assert hook_module.run_hook(cfg, "MySkin") == "ok"
    assert sentinel.read_text() == "s3cr3t"


def test_env_prefix_does_not_leak_into_calling_process(monkeypatch):
    """Setting env_FOO must NOT permanently mutate os.environ.

    Guards against a naive ``os.environ[...] = ...`` implementation
    that would poison subsequent tests / other WeeWX code.
    """
    monkeypatch.delenv("HOOK_TEST_TOKEN", raising=False)
    cfg = {"command": ["true"], "env_HOOK_TEST_TOKEN": "leak-check"}
    hook_module.run_hook(cfg, "MySkin")
    assert "HOOK_TEST_TOKEN" not in os.environ


def test_expandvars_substitutes_in_argv_elements(tmp_path):
    """$VAR in an argv element gets substituted from env_* before exec.

    Without this the shell-free argv would leave literal ``$TOKEN`` in the
    Authorization header, sending the string ``$TOKEN`` over the wire.
    """
    sentinel = tmp_path / "auth.txt"
    cfg = {
        "command": [
            "sh",
            "-c",
            # $1 = expanded auth header value, written verbatim
            f'printf %s "$1" > {sentinel}',
            "shell-name",  # $0 for sh -c
            "Bearer $TOKEN",  # argv element that must be expanded
        ],
        "env_TOKEN": "abc123",
    }
    assert hook_module.run_hook(cfg, "MySkin") == "ok"
    assert sentinel.read_text() == "Bearer abc123"


def test_expand_argv_never_mutates_os_environ(monkeypatch):
    """Regression pin: an earlier implementation swapped ``os.environ`` in
    a try/finally window to reuse ``os.path.expandvars``. That leaks env_*
    values (usually secrets) into any concurrent ``os.environ`` reader in
    the same interpreter — which very much includes the main WeeWX engine
    thread. The current impl must substitute against a local dict only.

    A before/after snapshot alone is NOT strong enough: the original bug
    restored ``os.environ`` at the end of its try/finally, so end-state
    matches start-state and the snapshot check would pass. Instead spy on
    every mutating method and fail if any of them fire during the call.
    """
    monkeypatch.delenv("HOOK_SPY_TOKEN", raising=False)

    def _fail(*_a, **_kw):
        pytest.fail("_expand_argv must not mutate os.environ")

    for name in ("clear", "update", "__setitem__", "__delitem__", "pop", "popitem"):
        monkeypatch.setattr(os.environ, name, _fail)

    argv = ["echo", "$HOOK_SPY_TOKEN", "$PATH"]
    extra_env = {"HOOK_SPY_TOKEN": "should-not-leak"}
    hook_module._expand_argv(argv, extra_env)
    # The end-state check is a second sentinel; the spies above are the
    # primary defence.
    assert "HOOK_SPY_TOKEN" not in os.environ


def test_expandvars_leaves_unknown_var_literal(tmp_path):
    """os.path.expandvars leaves ``$MISSING`` as literal if no env entry.

    Not a great UX but at least it fails observably at the destination
    (a webhook returning 401) rather than mutating to some other value.
    """
    sentinel = tmp_path / "out.txt"
    cfg = {
        "command": [
            "sh",
            "-c",
            f'printf %s "$1" > {sentinel}',
            "shell-name",
            "$NOT_A_REAL_VAR",
        ],
    }
    assert hook_module.run_hook(cfg, "MySkin") == "ok"
    assert sentinel.read_text() == "$NOT_A_REAL_VAR"


# --------------------------------------------------------------------------
# failure paths — non-fatal, informative return string
# --------------------------------------------------------------------------


def test_non_zero_exit_returns_failed_with_stderr_snippet():
    cfg = {"command": ["sh", "-c", ">&2 echo boom; exit 7"]}
    result = hook_module.run_hook(cfg, "MySkin")
    assert result.startswith("failed: exit 7")
    assert "boom" in result


def test_failed_command_does_not_write_marker(tmp_path):
    """A failed 'once' run leaves the marker UNwritten so a retry can
    succeed on the next report cycle — otherwise a single early failure
    would permanently disable the hook for the boot."""
    cfg = {"command": ["false"], "frequency": "once"}
    assert hook_module.run_hook(cfg, "MySkin").startswith("failed:")
    markers = [
        p.name for p in tmp_path.iterdir() if p.name.startswith(".weewx-report-hook-")
    ]
    assert markers == []


def test_timeout_returns_failed():
    cfg = {"command": ["sleep", "5"], "timeout": 1}
    result = hook_module.run_hook(cfg, "MySkin")
    assert result == "failed: timed out after 1s"


def test_missing_executable_returns_failed():
    cfg = {"command": ["/definitely/not/a/binary"]}
    result = hook_module.run_hook(cfg, "MySkin")
    assert result.startswith("failed: spawn failed")


def test_marker_write_failure_still_returns_ok(monkeypatch):
    """If the marker file can't be written (e.g. /tmp mounted read-only),
    the command *did* succeed and the caller should still see ``ok``. The
    downside is only that the hook may fire again next report cycle —
    annoying but not incorrect."""
    real_open = open

    def _fail_marker_open(path, *args, **kwargs):
        if isinstance(path, str) and path.startswith(str(hook_module.MARKER_DIR)):
            raise OSError("simulated: read-only marker dir")
        return real_open(path, *args, **kwargs)

    monkeypatch.setattr("builtins.open", _fail_marker_open)
    cfg = {"command": ["true"], "frequency": "once"}
    assert hook_module.run_hook(cfg, "MySkin") == "ok"


def test_once_marker_gate_wins_over_verify_file(tmp_path):
    """A once-hook that has already fired must return 'once-per-boot
    already fired' even if verify_file is transiently missing/empty —
    otherwise a stale verify_file would rename the outcome and mislead
    an operator reading the log."""
    empty = tmp_path / "empty.html"
    empty.write_text("")
    cfg = {"command": ["true"], "frequency": "once", "verify_file": str(empty)}
    # First call: verify_file gate fires (marker not yet created).
    assert hook_module.run_hook(cfg, "MySkin").startswith("skipped: verify_file")
    # Create marker as if a prior successful run had left it.
    (tmp_path / ".weewx-report-hook-MySkin").write_text("")
    # Marker gate now precedes the verify_file gate.
    assert hook_module.run_hook(cfg, "MySkin") == "skipped: once-per-boot already fired"


# --------------------------------------------------------------------------
# HA overrides (/data/options.json)
# --------------------------------------------------------------------------


def test_ha_overrides_absent_file_returns_empty():
    # tmp_path/options.json doesn't exist yet — must NOT raise.
    assert hook_module._load_ha_overrides() == {}


def test_ha_overrides_bad_json_returns_empty(tmp_path):
    (tmp_path / "options.json").write_text("this is not json {")
    assert hook_module._load_ha_overrides() == {}


def test_ha_overrides_non_dict_json_returns_empty(tmp_path):
    (tmp_path / "options.json").write_text('["a", "list"]')
    assert hook_module._load_ha_overrides() == {}


def test_ha_overrides_extracts_report_hook_prefixed_only(tmp_path):
    _write_ha_options(
        tmp_path,
        {
            "watchdog_path": "/index.html",  # non-report_hook, ignored
            "report_hook_command": ["curl", "-fsS"],
            "report_hook_frequency": "once",
            "report_hook_timeout": 42,
            "report_hook_verify_file": "/config/www/index.html",
        },
    )
    o = hook_module._load_ha_overrides()
    assert o == {
        "command": ["curl", "-fsS"],
        "frequency": "once",
        "timeout": 42,
        "verify_file": "/config/www/index.html",
    }


def test_ha_overrides_drops_empty_values(tmp_path):
    """A blank field in the HA UI must NOT clobber a real value in
    the skin dict — otherwise the operator "unsetting" a value silently
    reverts to disabled."""
    _write_ha_options(
        tmp_path,
        {
            "report_hook_command": [],
            "report_hook_frequency": "",
            "report_hook_timeout": None,
            "report_hook_verify_file": "",
            "report_hook_env": [],
        },
    )
    assert hook_module._load_ha_overrides() == {}


def test_ha_overrides_env_list_unrolled_to_env_prefix(tmp_path):
    """The HA schema stores env vars as a list of ``{name, value}``.
    Overrides must be reshaped into the same ``env_NAME`` keys the skin
    dict already uses, so downstream code doesn't need two code paths."""
    _write_ha_options(
        tmp_path,
        {
            "report_hook_command": ["true"],
            "report_hook_env": [
                {"name": "TOKEN", "value": "abc"},
                {"name": "OTHER", "value": "xyz"},
                # malformed entries silently dropped
                {"name": "", "value": "no-name"},
                {"value": "only-value"},
                "not-a-dict",
            ],
        },
    )
    o = hook_module._load_ha_overrides()
    assert o == {"command": ["true"], "env_TOKEN": "abc", "env_OTHER": "xyz"}


def test_ha_overrides_win_over_skin_dict(tmp_path):
    """Full-stack integration through ReportHook.run — the skin dict
    says one thing, HA options say another; HA wins."""
    _write_ha_options(
        tmp_path,
        {"report_hook_command": ["true"], "report_hook_frequency": "once"},
    )

    class _StubGen(hook_module.ReportHook):
        def __init__(self):  # noqa: D401
            self.skin_dict = {
                "REPORT_NAME": "SkinFromWeewxConf",
                "ReportHook": {
                    "command": ["false"],  # would fail
                    "frequency": "every",
                },
            }

    # If HA didn't win we'd get "failed:" (from `false`); we should get "ok".
    _StubGen().run()
    # Marker present with the skin name → confirms HA's frequency=once
    # took effect on the skin from the weewx.conf side.
    marker = tmp_path / ".weewx-report-hook-SkinFromWeewxConf"
    assert marker.exists()


def test_ha_env_var_merges_with_skin_env_and_wins(tmp_path):
    """If both HA and skin dict set env_TOKEN, HA's value wins — same
    override semantics as the other config keys."""
    _write_ha_options(
        tmp_path,
        {
            "report_hook_command": ["true"],
            "report_hook_env": [{"name": "TOKEN", "value": "ha-side"}],
        },
    )
    skin = {"command": ["true"], "env_TOKEN": "skin-side", "env_KEEP": "skin-only"}
    ha = hook_module._load_ha_overrides()
    merged = {**skin, **ha}
    assert merged["env_TOKEN"] == "ha-side"
    assert merged["env_KEEP"] == "skin-only"


# --------------------------------------------------------------------------
# integration: the class glue
# --------------------------------------------------------------------------


def test_generator_run_never_raises(monkeypatch):
    """ReportHook.run() is called inside a WeeWX report thread which
    catches exceptions but logs them as generator errors — we want zero
    such logs from this hook. Force run_hook to raise and confirm the
    class wrapper swallows it."""

    def _boom(*_a, **_kw):
        raise RuntimeError("simulated crash")

    monkeypatch.setattr(hook_module, "run_hook", _boom)

    class _FakeGen(hook_module.ReportHook):
        # Skip ReportGenerator.__init__ (would need a full weewx config
        # and a DBBinder); we're only testing that run() handles a bad
        # run_hook gracefully.
        def __init__(self):  # noqa: D401
            self.skin_dict = {
                "REPORT_NAME": "MySkin",
                "ReportHook": {"command": ["true"]},
            }

    try:
        _FakeGen().run()
    except Exception as e:  # pragma: no cover — the assertion is the point
        pytest.fail(f"ReportHook.run() must not propagate: {e!r}")


class _StubGen(hook_module.ReportHook):
    """Bypass ReportGenerator.__init__ (which requires a real DBBinder)."""

    def __init__(self, report_name="MySkin"):  # noqa: D401
        self.skin_dict = {
            "REPORT_NAME": report_name,
            "ReportHook": {"command": ["true"]},
        }


@pytest.mark.parametrize(
    "outcome,expected_level",
    [
        ("disabled", "DEBUG"),
        ("skipped: verify_file 'x' missing or empty", "DEBUG"),
        ("ok", "INFO"),
        ("failed: exit 7: some stderr", "WARNING"),
    ],
)
def test_generator_dispatch_uses_correct_log_level(
    monkeypatch, caplog, outcome, expected_level
):
    """Each outcome from run_hook routes to a specific log level; a
    ``failed:`` outcome at DEBUG (or ``ok`` at WARNING) would silently
    misreport hook health in production."""
    monkeypatch.setattr(hook_module, "run_hook", lambda cfg, name: outcome)
    caplog.set_level("DEBUG", logger=hook_module.log.name)
    _StubGen().run()
    matching = [r for r in caplog.records if r.levelname == expected_level]
    assert matching, (
        f"expected a {expected_level} log record for outcome {outcome!r}, "
        f"got {[r.levelname for r in caplog.records]}"
    )
