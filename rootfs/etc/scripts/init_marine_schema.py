# Copyright (c) 2026 Kenneth Baker <bakerkj@umich.edu>
# All rights reserved.

"""Create marine_data's three tables at addon startup if they don't exist.

Marine data's own installer creates its tables (``coops_realtime``,
``tide_table``, ``ndbc_data``) inside a curses-based ``configure()``
that ``weectl extension install --yes`` cannot drive non-interactively.
The addon's ``build/install_marine_data.py`` manual-installs the
extension files but skips ``configure()``; this shim runs at addon
start and invokes ``MarineDataInstaller._create_marine_tables_weewx_compliant``
against a stubbed engine so the tables are created from the YAML field
definitions the extension ships. Idempotent: ``CREATE TABLE IF NOT EXISTS``.

Why call the private method rather than extract the SQL: schema
management stays with the extension. A Renovate bump that changes a
column upstream (added field in marine_data_fields.yaml, renamed
per-table helper) is picked up here without a matching edit to our
repo. The private-API coupling is caught by CI on the bump (a rename
or signature change fails this shim's import or call, which fails the
addon startup smoke test).

Runs from ``weewx-init.sh`` after ``weewx.conf`` is in place, before
``weewxd`` starts.
"""

from __future__ import annotations

import os
import sys
from types import SimpleNamespace

import configobj

# The extension's install.py (renamed to avoid weewx trying to import it as
# a user module) lives here — copied by build/install_marine_data.py.
_INSTALLER_DIR = "/opt/weewx-data/scripts"
_WEEWX_CONF = os.environ.get("WEEWX_CONF", "/config/weewx.conf")


def _load_config() -> configobj.ConfigObj | None:
    if not os.path.exists(_WEEWX_CONF):
        print(f"init_marine_schema: {_WEEWX_CONF} not found; skipping", file=sys.stderr)
        return None
    return configobj.ConfigObj(_WEEWX_CONF, file_error=True)


def _marine_enabled(config: configobj.ConfigObj) -> bool:
    """Skip if marine_data isn't actually going to run — no point creating
    tables that will sit unused, and we'd waste addon-start latency on
    the upstream import. Two independent kill-switches to respect: the
    service must be listed in ``[Engine] [[Services]] data_services``,
    AND ``[MarineDataService] enable`` must not be a false-ish literal
    (the runtime service itself honors this at marine_data.py:75-77 —
    ``enable in ('false', 'no', '0')``)."""
    services = config.get("Engine", {}).get("Services", {})
    data_services = services.get("data_services", [])
    if isinstance(data_services, str):
        data_services = [data_services]
    if not any("marine_data" in s for s in data_services):
        return False
    enable = config.get("MarineDataService", {}).get("enable", "true")
    return str(enable).lower() not in ("false", "no", "0")


def main() -> int:
    config = _load_config()
    if config is None:
        return 0
    if not _marine_enabled(config):
        print("init_marine_schema: marine_data not in data_services; skipping")
        return 0

    # WEEWX_ROOT must be resolvable so MarineDataConfigurator can find the
    # YAML file at bin/user/marine_data_fields.yaml. The addon's template
    # sets WEEWX_ROOT to /opt/weewx-data; honor whatever's in the file.
    if "WEEWX_ROOT" not in config:
        config["WEEWX_ROOT"] = "/opt/weewx-data"

    if _INSTALLER_DIR not in sys.path:
        sys.path.insert(0, _INSTALLER_DIR)

    # Imports deferred until we know we have work to do so a missing
    # extension file surfaces as a specific error at first use, not as an
    # ImportError at every addon boot.
    try:
        from marine_data_installer import (  # type: ignore[import-not-found]
            MarineDataConfigurator,
            MarineDataInstaller,
        )
    except ImportError as e:
        print(
            f"init_marine_schema: cannot import marine_data_installer "
            f"from {_INSTALLER_DIR}: {e}",
            file=sys.stderr,
        )
        return 1

    # The installer's __init__ calls ExtensionInstaller.__init__ (which
    # sets self['config'] etc. from the class-level dict); no side effects
    # that matter here. If a future version's __init__ starts doing
    # network fetches or prompts, this call will surface it.
    installer = MarineDataInstaller()

    # MarineDataConfigurator.__init__ loads marine_data_fields.yaml into
    # self.yaml_data. It's the run_interactive_setup() method that is
    # curses/input-driven; the bare constructor is safe.
    engine = SimpleNamespace(config_dict=config)
    configurator = MarineDataConfigurator(config_dict=config, engine=engine)
    if not configurator.yaml_data:
        print(
            "init_marine_schema: MarineDataConfigurator loaded no yaml_data; "
            "check marine_data_fields.yaml is present under WEEWX_ROOT/bin/user/",
            file=sys.stderr,
        )
        return 1

    print("init_marine_schema: creating marine tables (idempotent)")
    installer._create_marine_tables_weewx_compliant(
        engine, config, {"configurator": configurator}
    )
    print("init_marine_schema: done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
