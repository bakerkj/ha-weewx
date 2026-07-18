# Copyright (c) 2026 Kenneth Baker <bakerkj@umich.edu>
# All rights reserved.
"""Behavioural tests for extensions/refresh_stale_outputs.py.

Drives the pure helpers (``_cheetah_stale_outputs``, ``_image_stale_outputs``,
``_resolve_html_root``, ``_stale_outputs``, ``_age_out``) directly, and
exercises the full ``_age_out_all`` walk against fixture skin.conf files
under ``tmp_path``. WeeWX's engine/service machinery is stubbed out — only
the parts the walk actually reads (``self.config_dict``) are provided —
so the tests never require an importable ``weewx.engine.StdService``.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

import configobj
import pytest

import refresh_stale_outputs as mod


# --------------------------------------------------------------------------
# _cheetah_stale_outputs — template with stale_age → output path
# --------------------------------------------------------------------------


def test_cheetah_yields_only_entries_with_both_template_and_stale_age():
    cfg = {
        "ToDate": {
            "view_live": {"template": "views/live.html.tmpl"},  # no stale_age → skip
            "view_forecast": {
                "template": "views/forecast.html.tmpl",
                "stale_age": "3570",
            },
            "no_template": {"stale_age": "3570"},  # no template → skip
        }
    }
    assert list(mod._cheetah_stale_outputs(cfg)) == ["views/forecast.html"]


def test_cheetah_recurses_arbitrarily_deep():
    cfg = {
        "Level1": {
            "Level2": {
                "Level3": {
                    "template": "deeply/nested.html.tmpl",
                    "stale_age": "60",
                }
            }
        }
    }
    assert list(mod._cheetah_stale_outputs(cfg)) == ["deeply/nested.html"]


def test_cheetah_ignores_scalar_leaves():
    """String / int values (e.g. ``encoding = utf8``) must not raise on
    the .items() traversal."""
    cfg = {
        "encoding": "utf8",
        "search_list": ["foo", "bar"],
        "view_forecast": {
            "template": "views/forecast.html.tmpl",
            "stale_age": "3570",
        },
    }
    assert list(mod._cheetah_stale_outputs(cfg)) == ["views/forecast.html"]


def test_cheetah_ignores_template_without_tmpl_suffix():
    """A template value that doesn't end in .tmpl is a config bug; skip
    it rather than yielding an unpredictable output name."""
    cfg = {
        "weird": {"template": "views/forecast.html", "stale_age": "3570"},
    }
    assert list(mod._cheetah_stale_outputs(cfg)) == []


def test_cheetah_container_stale_age_propagates_to_children():
    """weewx applies accumulateLeaves so a stale_age set on a container
    section (e.g. SummaryByMonth) gates every template underneath it —
    the walker must yield those child outputs too."""
    cfg = {
        "SummaryByMonth": {
            "stale_age": "3600",
            "NOAA_Monthly": {"template": "NOAA/NOAA-%Y-%m.txt.tmpl"},
            "Yearly_Summary": {"template": "views/yearly.html.tmpl"},
        }
    }
    # Fix the "now" so the strftime expansion is stable.
    fixed_now = time.mktime(time.strptime("2026-07-18", "%Y-%m-%d"))
    got = sorted(mod._cheetah_stale_outputs(cfg, now=fixed_now))
    assert got == ["NOAA/NOAA-2026-07.txt", "views/yearly.html"]


def test_cheetah_expands_literal_yyyymm_placeholders_shipped_by_weewx():
    """weewx's shipped Seasons/Standard skins use literal ``YYYY``/``MM``
    (see weeutil.getFileName) — NOT ``%Y-%m``. If the walker only handles
    the strftime form, aging the canonical monthly NOAA report (the exact
    use case this service exists for) is a silent no-op."""
    fixed_now = time.mktime(time.strptime("2026-07-18", "%Y-%m-%d"))
    cfg = {
        "NOAA": {
            "template": "NOAA/NOAA-YYYY-MM.txt.tmpl",
            "stale_age": "3570",
        }
    }
    assert list(mod._cheetah_stale_outputs(cfg, now=fixed_now)) == [
        "NOAA/NOAA-2026-07.txt"
    ]


def test_cheetah_expands_strftime_placeholders_in_template_name():
    """SummaryByMonth NOAA reports use ``%Y-%m`` in the template path
    (`NOAA-%Y-%m.txt.tmpl` → `NOAA-2026-07.txt` on disk). Aging out the
    literal 'NOAA-%Y-%m.txt' would never find a real file. Expand via
    time.strftime so the current period is aged correctly; past periods
    are immutable so they don't need aging."""
    fixed_now = time.mktime(time.strptime("2026-07-18", "%Y-%m-%d"))
    cfg = {
        "NOAA": {
            "template": "NOAA/NOAA-%Y-%m.txt.tmpl",
            "stale_age": "3600",
        }
    }
    assert list(mod._cheetah_stale_outputs(cfg, now=fixed_now)) == [
        "NOAA/NOAA-2026-07.txt"
    ]


# --------------------------------------------------------------------------
# _image_stale_outputs — section name → <name>.png
# --------------------------------------------------------------------------


def test_image_yields_section_name_plus_png_for_stale_age_entries():
    cfg = {
        "week_images": {
            "weekcloudbase": {"stale_age": "3600"},
            "weekbarometer": {},  # no stale_age → skip
        },
        "year_images": {
            "yearpurpleair": {"stale_age": "3600"},
        },
    }
    got = sorted(mod._image_stale_outputs(cfg))
    assert got == ["weekcloudbase.png", "yearpurpleair.png"]


def test_image_container_stale_age_propagates_to_every_child_plot():
    """weewx uses accumulateLeaves so a ``stale_age`` at the container
    level (e.g. ``[[year_images]]``) gates every plot under it, NOT the
    nonexistent ``year_images.png``. Walker must yield each child plot."""
    cfg = {
        "year_images": {
            "stale_age": "3600",
            "yearbarometer": {},
            "yearcloudbase": {},
        }
    }
    assert sorted(mod._image_stale_outputs(cfg)) == [
        "yearbarometer.png",
        "yearcloudbase.png",
    ]


def test_image_only_yields_at_plot_depth_not_container_depth():
    """A container section itself must never yield a bogus
    ``<container>.png`` — plots live one level deeper. This is what
    prevented the container-inheritance fix from double-firing on the
    parent."""
    cfg = {
        "year_images": {
            "yearbarometer": {"stale_age": "3600"},
        }
    }
    assert list(mod._image_stale_outputs(cfg)) == ["yearbarometer.png"]


# --------------------------------------------------------------------------
# _stale_outputs — combined walk
# --------------------------------------------------------------------------


def test_stale_outputs_combines_cheetah_and_image():
    skin = {
        "CheetahGenerator": {
            "view_forecast": {
                "template": "views/forecast.html.tmpl",
                "stale_age": "3570",
            }
        },
        "ImageGenerator": {
            "week_images": {"weekcloudbase": {"stale_age": "3600"}},
        },
    }
    got = sorted(mod._stale_outputs(skin))
    assert got == ["views/forecast.html", "weekcloudbase.png"]


def test_stale_outputs_missing_generator_sections_ok():
    """A skin with only CheetahGenerator, or only ImageGenerator, or
    neither must not raise."""
    assert list(mod._stale_outputs({})) == []
    assert list(
        mod._stale_outputs(
            {"CheetahGenerator": {"x": {"template": "x.tmpl", "stale_age": "1"}}}
        )
    ) == ["x"]


# --------------------------------------------------------------------------
# _age_out — the actual utime touch
# --------------------------------------------------------------------------


def test_age_out_touches_existing_file_to_epoch(tmp_path):
    p = tmp_path / "forecast.html"
    p.write_text("hi")
    assert mod._age_out(str(p)) is True
    st = os.stat(p)
    assert int(st.st_mtime) == 0


def test_age_out_returns_false_for_missing_file(tmp_path):
    p = tmp_path / "nope.html"
    assert mod._age_out(str(p)) is False


def test_age_out_returns_false_and_logs_on_oserror(monkeypatch, tmp_path, caplog):
    p = tmp_path / "forecast.html"
    p.write_text("hi")

    def _boom(*_a, **_kw):
        raise OSError("simulated: read-only fs")

    monkeypatch.setattr(mod.os, "utime", _boom)
    caplog.set_level("WARNING", logger=mod.log.name)
    assert mod._age_out(str(p)) is False
    assert any("could not age" in r.message for r in caplog.records)


# --------------------------------------------------------------------------
# _resolve_html_root — mirrors weewx's own resolution
# --------------------------------------------------------------------------


def test_resolve_html_root_uses_explicit_absolute_path_from_per_report():
    got = mod._resolve_html_root(
        "/opt/weewx", "MySkin", {"HTML_ROOT": "/var/www"}, {}, {}
    )
    assert got == "/var/www"


def test_resolve_html_root_resolves_relative_against_weewx_root():
    got = mod._resolve_html_root(
        "/opt/weewx", "MySkin", {"HTML_ROOT": "public_html"}, {}, {}
    )
    assert got == "/opt/weewx/public_html"


def test_resolve_html_root_per_report_beats_all_others():
    """Per-report [StdReport][<name>] HTML_ROOT wins over every other
    source (highest precedence in build_skin_dict)."""
    got = mod._resolve_html_root(
        "/opt/weewx",
        "MySkin",
        {"HTML_ROOT": "/per-report"},
        {"HTML_ROOT": "/skin-conf"},
        {
            "HTML_ROOT": "/stdreport-scalar",
            "Defaults": {"HTML_ROOT": "/defaults"},
        },
    )
    assert got == "/per-report"


def test_resolve_html_root_stdreport_scalar_beats_defaults_and_skin_conf():
    """weewx's build_skin_dict merges [StdReport] scalars AFTER [[Defaults]],
    so the scalar wins if both are set. Beats skin.conf too."""
    got = mod._resolve_html_root(
        "/opt/weewx",
        "MySkin",
        {},
        {"HTML_ROOT": "/skin-conf"},
        {
            "HTML_ROOT": "/stdreport-scalar",
            "Defaults": {"HTML_ROOT": "/defaults"},
        },
    )
    assert got == "/stdreport-scalar"


def test_resolve_html_root_defaults_beats_skin_conf():
    """[StdReport][[Defaults]] HTML_ROOT overrides skin.conf's default."""
    got = mod._resolve_html_root(
        "/opt/weewx",
        "MySkin",
        {},
        {"HTML_ROOT": "/skin-conf"},
        {"Defaults": {"HTML_ROOT": "/defaults"}},
    )
    assert got == "/defaults"


def test_resolve_html_root_falls_back_to_skin_conf_when_nothing_overrides():
    """If neither weewx.conf's scalar nor [[Defaults]] nor per-report sets
    HTML_ROOT, the skin.conf value wins over the built-in default."""
    got = mod._resolve_html_root(
        "/opt/weewx",
        "MySkin",
        {},
        {"HTML_ROOT": "/skin-conf"},
        {},
    )
    assert got == "/skin-conf"


def test_resolve_html_root_default_is_bare_public_html():
    """weewx's built-in default (per weewx/defaults.py) is a bare
    'public_html' directory shared across reports — NOT 'public_html/
    <report_name>'. Report-name subdirectory disambiguation happens at
    the template level, not HTML_ROOT."""
    got = mod._resolve_html_root("/opt/weewx", "MySkin", {}, {}, {})
    assert got == "/opt/weewx/public_html"


# --------------------------------------------------------------------------
# _resolve_skin_conf — resolution table
# --------------------------------------------------------------------------


def test_resolve_skin_conf_absolute_skin_path():
    got = mod._resolve_skin_conf("/opt/weewx", "skins", "MySkin", {"skin": "/abs/path"})
    assert got == "/abs/path/skin.conf"


def test_resolve_skin_conf_relative_skin_path_under_skin_root():
    got = mod._resolve_skin_conf("/opt/weewx", "skins", "MySkin", {"skin": "MySkin"})
    assert got == "/opt/weewx/skins/MySkin/skin.conf"


def test_resolve_skin_conf_no_skin_key_falls_back_to_report_name():
    got = mod._resolve_skin_conf("/opt/weewx", "skins", "MySkin", {})
    assert got == "/opt/weewx/skins/MySkin/skin.conf"


# --------------------------------------------------------------------------
# _age_out_all — full integration under a fixture skin tree
# --------------------------------------------------------------------------


class _FakeService(mod.RefreshStaleOutputs):
    """Bypass StdService.__init__ (which needs a real weewx engine) so
    tests can drive _age_out_all directly."""

    def __init__(self, config_dict):
        self.config_dict = config_dict


def _write_skin(skin_dir: Path, sections: dict) -> None:
    skin_dir.mkdir(parents=True, exist_ok=True)
    conf = configobj.ConfigObj()
    conf.filename = str(skin_dir / "skin.conf")
    for k, v in sections.items():
        conf[k] = v
    conf.write()


def _fixture_skin(tmp_path: Path) -> tuple[Path, Path]:
    """Build a weewx-shaped fixture: skins/MySkin/skin.conf declares one
    Cheetah template with stale_age and one image with stale_age.
    Returns (weewx_root, html_root)."""
    weewx_root = tmp_path
    skin_dir = weewx_root / "skins" / "MySkin"
    html_root = weewx_root / "public_html" / "MySkin"
    _write_skin(
        skin_dir,
        {
            "HTML_ROOT": str(html_root),
            "CheetahGenerator": {
                "view_forecast": {
                    "template": "views/forecast.html.tmpl",
                    "stale_age": "3570",
                },
                "view_live": {
                    "template": "views/live.html.tmpl",  # no stale_age
                },
            },
            "ImageGenerator": {
                "week_images": {
                    "weekcloudbase": {"stale_age": "3600"},
                    "weekbarometer": {},
                },
            },
        },
    )
    (html_root / "views").mkdir(parents=True, exist_ok=True)
    for rel in ("views/forecast.html", "views/live.html", "weekcloudbase.png"):
        f = html_root / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(b"fresh")
        # Set mtime to *now* so the age-out test can detect a change.
        os.utime(f, None)
    return weewx_root, html_root


def test_age_out_all_ages_stale_gated_outputs_only(tmp_path):
    weewx_root, html_root = _fixture_skin(tmp_path)
    now = time.time()
    svc = _FakeService(
        {
            "WEEWX_ROOT": str(weewx_root),
            "StdReport": {"MySkin": {}},
        }
    )
    n = svc._age_out_all()
    # forecast (stale_age) + weekcloudbase (stale_age) = 2
    assert n == 2
    assert int(os.stat(html_root / "views" / "forecast.html").st_mtime) == 0
    assert int(os.stat(html_root / "weekcloudbase.png").st_mtime) == 0
    # live.html has no stale_age — must NOT have been aged
    assert os.stat(html_root / "views" / "live.html").st_mtime > now - 5


def test_age_out_all_respects_disabled_reports(tmp_path):
    weewx_root, html_root = _fixture_skin(tmp_path)
    now = time.time()
    svc = _FakeService(
        {
            "WEEWX_ROOT": str(weewx_root),
            "StdReport": {"MySkin": {"enable": "false"}},
        }
    )
    assert svc._age_out_all() == 0
    # forecast.html and weekcloudbase.png still fresh
    assert os.stat(html_root / "views" / "forecast.html").st_mtime > now - 5
    assert os.stat(html_root / "weekcloudbase.png").st_mtime > now - 5


def test_age_out_all_skips_missing_output_files(tmp_path):
    """A stale_age entry whose output file doesn't yet exist (e.g. a
    template that hasn't ever been rendered on this install) must not
    raise — just skip."""
    weewx_root, html_root = _fixture_skin(tmp_path)
    (html_root / "views" / "forecast.html").unlink()
    svc = _FakeService({"WEEWX_ROOT": str(weewx_root), "StdReport": {"MySkin": {}}})
    # weekcloudbase.png still exists and is aged; forecast just skipped.
    assert svc._age_out_all() == 1


def test_age_out_all_honours_weewx_conf_html_root_override(tmp_path):
    """A user's per-report HTML_ROOT in weewx.conf takes precedence over
    skin.conf's default (which is what StdReportEngine also does)."""
    weewx_root, _ = _fixture_skin(tmp_path)
    # Set up an override HTML_ROOT elsewhere; the fixture skin's outputs
    # under public_html/MySkin/ should NOT be touched.
    alt = weewx_root / "alt-html-root"
    (alt / "views").mkdir(parents=True)
    (alt / "views" / "forecast.html").write_bytes(b"alt")
    (alt / "weekcloudbase.png").write_bytes(b"alt")
    for f in (alt / "views" / "forecast.html", alt / "weekcloudbase.png"):
        os.utime(f, None)

    svc = _FakeService(
        {
            "WEEWX_ROOT": str(weewx_root),
            "StdReport": {"MySkin": {"HTML_ROOT": str(alt)}},
        }
    )
    n = svc._age_out_all()
    assert n == 2
    assert int(os.stat(alt / "views" / "forecast.html").st_mtime) == 0
    assert int(os.stat(alt / "weekcloudbase.png").st_mtime) == 0
    # Default HTML_ROOT files untouched (never referenced because override
    # took precedence).
    default_forecast = weewx_root / "public_html" / "MySkin" / "views" / "forecast.html"
    assert os.stat(default_forecast).st_mtime > 60


def test_age_out_all_skips_defaults_pseudo_report(tmp_path):
    """weewx treats ``[StdReport][[Defaults]]`` as a config seed, not a
    real report — never walks it as a skin. If we walked it, we'd try to
    load ``skins/Defaults/skin.conf`` (which we might actually find if
    the user has scaffolded one) and age files under it."""
    weewx_root, html_root = _fixture_skin(tmp_path)
    # Simulate the exact shape that would trip us up: a real skins/Defaults/
    # directory with a skin.conf declaring a stale_age.
    defaults_skin = weewx_root / "skins" / "Defaults"
    _write_skin(
        defaults_skin,
        {
            "HTML_ROOT": str(html_root),
            "CheetahGenerator": {
                "trap": {
                    "template": "views/live.html.tmpl",
                    "stale_age": "1",
                }
            },
        },
    )
    svc = _FakeService(
        {
            "WEEWX_ROOT": str(weewx_root),
            "StdReport": {
                "MySkin": {},
                "Defaults": {"unit_system": "US"},
            },
        }
    )
    n = svc._age_out_all()
    # MySkin's forecast + weekcloudbase; Defaults not walked as a report.
    assert n == 2
    # views/live.html was NOT aged (Defaults section was skipped)
    now = time.time()
    assert os.stat(html_root / "views" / "live.html").st_mtime > now - 5


def test_age_out_all_skips_report_with_missing_skin_conf(tmp_path):
    """If a [StdReport] entry names a skin whose skin.conf doesn't exist
    on disk (e.g. user renamed a bundled skin without updating the ref),
    the walk logs debug and moves on — no exception, no other report
    affected."""
    weewx_root, html_root = _fixture_skin(tmp_path)
    # Point a second report at a nonexistent skin dir.
    svc = _FakeService(
        {
            "WEEWX_ROOT": str(weewx_root),
            "StdReport": {
                "MySkin": {},
                "GhostSkin": {"skin": "does-not-exist"},
            },
        }
    )
    n = svc._age_out_all()
    # Ghost skipped; MySkin's two aged as normal.
    assert n == 2


def test_age_out_all_swallows_bad_skin_conf(tmp_path):
    """A skin.conf that fails to parse must not crash the walk. The
    service just logs debug and moves on to the next report."""
    weewx_root = tmp_path
    (weewx_root / "skins" / "BadSkin").mkdir(parents=True)
    (weewx_root / "skins" / "BadSkin" / "skin.conf").write_text(
        "[unbalanced\nnot valid ini"
    )
    svc = _FakeService({"WEEWX_ROOT": str(weewx_root), "StdReport": {"BadSkin": {}}})
    # Shouldn't raise. Return 0 because nothing was aged.
    assert svc._age_out_all() == 0


def test_on_startup_never_raises(monkeypatch):
    """The event-bound entry point must swallow all exceptions — the
    report thread continues regardless."""

    def _boom(_self):
        raise RuntimeError("simulated internal failure")

    monkeypatch.setattr(mod.RefreshStaleOutputs, "_age_out_all", _boom)

    svc = _FakeService({"WEEWX_ROOT": ".", "StdReport": {}})
    try:
        svc._on_startup(None)
    except Exception as e:
        pytest.fail(f"_on_startup must not propagate: {e!r}")
