# Copyright (c) 2026 Kenneth Baker <bakerkj@umich.edu>
# All rights reserved.
"""RefreshStaleOutputs: on weewxd startup, age-out every skin output whose
config has ``stale_age`` set so the next report cycle re-renders it,
and sweep any ``.weewx-tmp-*`` fragments left over from a hard-killed
copy in the same walk.

WeeWX's CheetahGenerator and ImageGenerator both honour ``stale_age``: if a
template's output file is younger than that many seconds, they skip
re-rendering. That behaviour is correct in steady state (a report thread
firing every archive cycle for a template that only meaningfully changes
hourly is wasted work), but it also gates ``first_run`` — the first cycle
after a fresh weewxd start. That means a source edit made **after** the
last restart but **before** an addon restart lands in the runtime tree
only once the output ages past its ``stale_age``, up to ~59 minutes for a
1-hour gate.

This service closes that gap by walking every enabled ``[StdReport]``
skin at startup and calling ``os.utime(dest, (0, 0))`` on every output
file whose skin config has ``stale_age`` set — in both
``[CheetahGenerator]`` and ``[ImageGenerator]``. The first report cycle
then sees the file as ancient, the stale-age branch trivially decides it
must re-render, and Cheetah's atomic tmp+rename replaces the aged content
before anyone reads the ancient mtime.

The same walk also sweeps ``.weewx-tmp-*`` fragments from every visited
``HTML_ROOT``. weewx's patched ``weeutil.deep_copy_path`` writes to a
same-directory tmp file then ``os.replace``s it over the final path.
Normal-path cleanup on Python-visible exceptions is in place; a hard
kill (SIGKILL/OOM/power loss) can leave a tmp fragment behind. Any that
survives the previous weewxd process is a stale artefact — its final
destination either already got the newer content on a subsequent copy
cycle or will on the next one — so unlinking it at startup is always
safe.

Wire in ``weewx.conf``:

    [Engine]
        [[Services]]
            report_services = ..., user.refresh_stale_outputs.RefreshStaleOutputs

Non-fatal by design: every filesystem or config-parse failure is logged
and moved on from. The report cycle continues even if the aging pass
finds nothing or bumps into a permissions error.
"""

from __future__ import annotations

import logging
import os
import time
from collections.abc import Iterator
from typing import Any

import configobj
import weeutil.config
import weeutil.weeutil
import weewx
from weewx.engine import StdService

log = logging.getLogger(__name__)


class RefreshStaleOutputs(StdService):
    """StdService that ages-out ``stale_age``-gated outputs on
    ``weewx.STARTUP`` so the first report cycle after each weewxd start
    re-renders them regardless of the age gate."""

    def __init__(self, engine, config_dict):
        super().__init__(engine, config_dict)
        self.bind(weewx.STARTUP, self._on_startup)

    def _on_startup(self, _event) -> None:
        try:
            aged, html_roots = self._age_out_all()
        except Exception as e:  # noqa: BLE001  # never break weewxd startup over a config quirk
            log.warning("RefreshStaleOutputs: unexpected error: %s", e)
            return
        if aged:
            log.info("RefreshStaleOutputs: aged %d stale-gated output files", aged)
        # Independent from the aging pass so a failure in either doesn't
        # abandon the other. `html_roots` is the deduped set of every
        # HTML_ROOT the walk resolved — sweep tmp fragments in each.
        try:
            swept = self._sweep_tmp_all(html_roots)
        except Exception as e:  # noqa: BLE001  # sweep independence: aging pass already succeeded, don't rethrow
            log.warning("RefreshStaleOutputs: tmp-sweep failed: %s", e)
            return
        if swept:
            log.info(
                "RefreshStaleOutputs: swept %d stale .weewx-tmp-* fragments",
                swept,
            )

    def _age_out_all(self) -> tuple[int, set[str]]:
        """Walk every enabled ``[StdReport]`` skin, load its skin.conf,
        find every leaf with ``stale_age``, and age-out the corresponding
        output. Returns ``(aged_count, html_roots)`` — the number of files
        touched and the deduped set of every ``HTML_ROOT`` the walk
        resolved. The tmp-sweep pass consumes ``html_roots`` next, so
        both concerns share the same skin-config resolution work."""
        aged = 0
        html_roots: set[str] = set()
        weewx_root = self.config_dict.get("WEEWX_ROOT", ".")
        std_report_cfg = self.config_dict.get("StdReport", {})
        skin_root = std_report_cfg.get("SKIN_ROOT", "skins")

        for report_name, report_cfg in std_report_cfg.items():
            if not isinstance(report_cfg, dict):
                # SKIN_ROOT / HTML_ROOT / defaults etc. at [StdReport] scope.
                continue
            # weewx skips [StdReport][[Defaults]] as a report itself
            # (reportengine.py: `if report == 'Defaults': continue`).
            # Match that.
            if report_name == "Defaults":
                continue

            try:
                if not weeutil.weeutil.to_bool(report_cfg.get("enable", "true")):
                    continue
            except Exception as e:  # noqa: BLE001  # skip malformed report; don't halt walk
                log.debug(
                    "RefreshStaleOutputs: invalid enable= for %s: %s",
                    report_name,
                    e,
                )
                continue

            # Everything below this point is per-report scoped: one
            # malformed report (e.g. configobj coercing a trailing-comma
            # scalar into a list, which breaks `template.endswith()` in
            # the stale-outputs walk) must NOT abort the remaining
            # reports. Log the offender, skip it, move on.
            try:
                skin_conf_path = _resolve_skin_conf(
                    weewx_root, skin_root, report_name, report_cfg
                )
                if not skin_conf_path or not os.path.isfile(skin_conf_path):
                    continue

                try:
                    skin_dict: dict[str, Any] = configobj.ConfigObj(skin_conf_path)
                except Exception as e:  # noqa: BLE001  # skip unloadable skin; don't halt walk
                    log.debug(
                        "RefreshStaleOutputs: could not load %s: %s",
                        skin_conf_path,
                        e,
                    )
                    continue

                # Merge weewx.conf's report-scoped overrides onto skin.conf so
                # a stale_age set in weewx.conf (not just skin.conf) still
                # contributes to the walk. Merges shallowly-onto-deeply, so
                # weewx.conf wins where it defines a value — matching what
                # StdReportEngine does when it builds each skin's real config.
                # HTML_ROOT is resolved separately below with the full
                # weewx precedence, not from this merge.
                try:
                    weeutil.config.merge_config(skin_dict, report_cfg)
                except Exception as e:  # noqa: BLE001  # proceed with unmerged skin_dict rather than halt
                    log.debug(
                        "RefreshStaleOutputs: merge failed for %s: %s",
                        report_name,
                        e,
                    )

                html_root = _resolve_html_root(
                    weewx_root, report_name, report_cfg, skin_dict, std_report_cfg
                )
                html_roots.add(html_root)

                for rel_out in _stale_outputs(skin_dict):
                    out = os.path.join(html_root, rel_out)
                    if _age_out(out):
                        aged += 1
            except Exception as e:  # noqa: BLE001  # per-report isolation: one bad skin must not abort the walk
                log.debug(
                    "RefreshStaleOutputs: skipping report %s after unexpected error: %s",
                    report_name,
                    e,
                )
                continue
        return aged, html_roots

    def _sweep_tmp_all(self, html_roots: set[str]) -> int:
        """Delete every ``.weewx-tmp-*`` fragment beneath each of
        ``html_roots``. Returns the count of files unlinked.

        ``weeutil.deep_copy_path`` writes to a same-directory tmp file
        (``tempfile.mkstemp(dir=d, prefix=".weewx-tmp-")``) then
        ``os.replace``s it over the final path. On a Python-visible
        exception the cleanup ``except`` block unlinks the tmp; on a
        hard kill (SIGKILL/OOM/power loss) the fragment can survive.
        Any tmp fragment older than the previous weewxd process is a
        stale artefact whose final destination already got the newer
        content on a subsequent copy cycle, so unlinking it is always
        safe. Per-directory os.walk failures are logged and skipped so
        one bad HTML_ROOT doesn't halt the sweep."""
        swept = 0
        for html_root in html_roots:
            if not os.path.isdir(html_root):
                continue
            try:
                walker = os.walk(html_root, onerror=self._walk_error)
                for dirpath, _dirnames, filenames in walker:
                    for name in filenames:
                        if not name.startswith(".weewx-tmp-"):
                            continue
                        path = os.path.join(dirpath, name)
                        try:
                            os.unlink(path)
                            swept += 1
                            log.debug("RefreshStaleOutputs: swept %s", path)
                        except OSError as e:
                            log.debug(
                                "RefreshStaleOutputs: could not sweep %s: %s",
                                path,
                                e,
                            )
            except Exception as e:  # noqa: BLE001  # per-root isolation: one bad html_root must not abort sweep
                log.debug(
                    "RefreshStaleOutputs: sweep of %s failed: %s",
                    html_root,
                    e,
                )
        return swept

    @staticmethod
    def _walk_error(err: OSError) -> None:
        log.debug("RefreshStaleOutputs: os.walk error: %s", err)


# --------------------------------------------------------------------------
# helpers — pure functions, no service state
# --------------------------------------------------------------------------


def _resolve_skin_conf(
    weewx_root: str, skin_root: str, report_name: str, report_cfg: dict[str, Any]
) -> str | None:
    """Return the absolute path to this report's skin.conf, or None if it
    can't be located. Mirrors the resolution weewx does itself."""
    skin = report_cfg.get("skin")
    if skin:
        if os.path.isabs(skin):
            return os.path.join(skin, "skin.conf")
        return os.path.join(weewx_root, skin_root, skin, "skin.conf")
    # Fallback: skin dir named after the report itself.
    return os.path.join(weewx_root, skin_root, report_name, "skin.conf")


def _resolve_html_root(
    weewx_root: str,
    report_name: str,
    report_cfg: dict[str, Any],
    skin_dict: dict[str, Any],
    std_report_cfg: dict[str, Any],
) -> str:
    """Return the absolute HTML_ROOT for this report. Precedence — high
    to low — matches ``StdReportEngine.build_skin_dict``:

      1. ``[StdReport][<report>] HTML_ROOT`` — per-report user override
      2. ``[StdReport] HTML_ROOT`` — top-level user scalar
      3. ``[StdReport][[Defaults]] HTML_ROOT`` — user-set default across
         every skin
      4. ``skin.conf`` HTML_ROOT — the skin's own default
      5. ``public_html`` — weewx's shipped default (``weewx/defaults.py``)

    Any relative value is joined against ``WEEWX_ROOT``, matching
    ``StdReportEngine``'s ``os.path.join(WEEWX_ROOT, HTML_ROOT)``."""
    html_root = None
    if isinstance(report_cfg, dict):
        html_root = report_cfg.get("HTML_ROOT")
    if not html_root and isinstance(std_report_cfg, dict):
        html_root = std_report_cfg.get("HTML_ROOT")
    if not html_root and isinstance(std_report_cfg, dict):
        defaults = std_report_cfg.get("Defaults")
        if isinstance(defaults, dict):
            html_root = defaults.get("HTML_ROOT")
    if not html_root:
        html_root = skin_dict.get("HTML_ROOT")
    if not html_root:
        html_root = "public_html"
    if not os.path.isabs(html_root):
        html_root = os.path.join(weewx_root, html_root)
    return html_root


def _stale_outputs(skin_dict: dict[str, Any]) -> Iterator[str]:
    """Yield every output filename (relative to HTML_ROOT) whose
    skin_dict entry has ``stale_age`` set. Covers both
    ``[CheetahGenerator]`` (output = ``template`` with ``.tmpl`` stripped)
    and ``[ImageGenerator]`` (output = section name + ``.png``)."""
    cheetah = skin_dict.get("CheetahGenerator")
    if isinstance(cheetah, dict):
        yield from _cheetah_stale_outputs(cheetah)
    image = skin_dict.get("ImageGenerator")
    if isinstance(image, dict):
        yield from _image_stale_outputs(image)


_YYYYMMDD_KEYS = (("YYYY", "%Y"), ("MM", "%m"), ("DD", "%d"), ("WW", "%W"))


def _expand_template_placeholders(name: str, now: float) -> str:
    """Apply the same substitutions weewx's own ``weeutil.getFileName``
    performs on Cheetah template paths: literal ``YYYY/MM/DD/WW`` and any
    ``%``-style strftime tokens, both against ``now``. weewx's shipped
    Seasons/Standard skins use the literal form (``NOAA-YYYY-MM.txt.tmpl``);
    3rd-party skins tend to use the ``%Y-%m`` form. Handle both."""
    for literal, code in _YYYYMMDD_KEYS:
        if literal in name:
            name = name.replace(literal, time.strftime(code, time.localtime(now)))
    if "%" in name:
        name = time.strftime(name, time.localtime(now))
    return name


def _cheetah_stale_outputs(
    cfg: dict[str, Any],
    inherit_stale: bool = False,
    now: float | None = None,
) -> Iterator[str]:
    """Recurse the CheetahGenerator tree; yield the output path (relative
    to HTML_ROOT) for every leaf that has ``template`` set AND either
    ``stale_age`` on itself or ``stale_age`` on any ancestor section
    (weewx propagates it down the tree). Date placeholders in the template
    name — both weewx's literal ``YYYY/MM/DD/WW`` (shipped Seasons NOAA
    reports) and ``%``-style strftime tokens — are expanded against
    ``now`` so we age the current period's output, not a template with
    literal placeholders. Past periods are immutable so their files never
    need aging."""
    if now is None:
        now = time.time()
    for section in cfg.values():
        if not isinstance(section, dict):
            continue
        stale_here = inherit_stale or "stale_age" in section
        template = section.get("template")
        if template and stale_here and template.endswith(".tmpl"):
            out = template[: -len(".tmpl")]
            out = _expand_template_placeholders(out, now)
            yield out
        yield from _cheetah_stale_outputs(section, stale_here, now)


def _image_stale_outputs(
    cfg: dict[str, Any],
    depth: int = 0,
    inherit_stale: bool = False,
) -> Iterator[str]:
    """Recurse the ImageGenerator tree and yield ``<plot>.png`` for every
    plot whose section has ``stale_age`` OR inherits it from a container
    ancestor. weewx uses ``accumulateLeaves`` to build each plot's
    effective config, so a ``stale_age`` at
    ``[ImageGenerator][[year_images]]`` gates every plot inside
    ``year_images``, not the (nonexistent) file ``year_images.png``. We
    track depth so we only yield at the plot level (grandchildren of
    ``[ImageGenerator]``, depth == 1 in this recursion where depth == 0
    iterates the top-level containers)."""
    for key, section in cfg.items():
        if not isinstance(section, dict):
            continue
        stale_here = inherit_stale or "stale_age" in section
        if depth == 1 and stale_here:
            yield key + ".png"
        yield from _image_stale_outputs(section, depth + 1, stale_here)


def _age_out(path: str) -> bool:
    """Set ``path``'s mtime to epoch so downstream stale_age gates see it
    as ancient. Silently skips missing files. Returns True if the file
    was actually touched."""
    if not os.path.isfile(path):
        return False
    try:
        os.utime(path, (0, 0))
        log.debug("RefreshStaleOutputs: aged %s", path)
        return True
    except OSError as e:
        log.warning("RefreshStaleOutputs: could not age %s: %s", path, e)
        return False
