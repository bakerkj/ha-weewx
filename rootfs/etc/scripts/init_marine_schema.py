# Copyright (c) 2026 Kenneth Baker <bakerkj@umich.edu>
# All rights reserved.

"""Create marine_data's three tables at addon startup if they don't exist.

Marine data's own installer creates its tables (``coops_realtime``,
``tide_table``, ``ndbc_data``) inside a curses-based ``configure()``
that ``weectl extension install --yes`` cannot drive non-interactively.
The addon's ``build/install_marine_data.py`` manual-installs the
extension files but skips ``configure()``; this shim runs at addon
start and creates the tables directly from ``marine_data_fields.yaml``
(idempotent: ``CREATE TABLE IF NOT EXISTS``).

We own the DDL rather than call the upstream installer's private
``_create_*_table`` helpers: those emit MySQL-only prefix-index syntax
(``station_id(20)``, ``tide_type(1)``) and inline ``INDEX`` clauses
inside ``CREATE TABLE`` that SQLite rejects. This shim emits portable
SQL that runs on both MariaDB and SQLite.

The two upstream inputs we depend on (marine_data_fields.yaml for the
schema, and the tide_table's five hardcoded operational fields) are
SHA-pinned at build time; any upstream change forces a build failure
and a re-audit.

Runs from ``weewx-init.sh`` after ``weewx.conf`` is in place, before
``weewxd`` starts.
"""

from __future__ import annotations

import os
import re
import sys
from typing import Any

import configobj
import weeutil.weeutil

_WEEWX_CONF = os.environ.get("WEEWX_CONF", "/config/weewx.conf")
_FIELDS_YAML = os.environ.get(
    "MARINE_FIELDS_YAML", "/opt/weewx-data/bin/user/marine_data_fields.yaml"
)

# Defense in depth on YAML-sourced identifiers we interpolate into DDL.
# ASCII identifier + rejects the DB engines' own namespaces via a negative
# lookahead. The YAML is SHA-pinned, so this catches upstream renames.
_SQL_IDENT_RE = re.compile(r"^(?!(?i:sqlite_|pg_|mysql))[A-Za-z_][A-Za-z0-9_]*$")
_ALLOWED_SQL_TYPES = {
    "INTEGER",
    "INTEGER NOT NULL",
    "REAL",
    "REAL NOT NULL",
    "TEXT",
    "TEXT NOT NULL",
    "VARCHAR(1) NOT NULL",
    "VARCHAR(20) NOT NULL",
}

# tide_table's operational fields, hardcoded in the upstream installer's
# _create_tide_table alongside the YAML fields. Upstream is SHA-pinned,
# so a bump that changes this list fails the build.
_TIDE_OPERATIONAL_FIELDS: dict[str, str] = {
    "tide_time": "INTEGER NOT NULL",
    "tide_type": "VARCHAR(1) NOT NULL",
    "predicted_height": "REAL",
    "datum": "TEXT",
    "days_ahead": "INTEGER",
}

# (table, index_name, indexed_columns) mirrored from the upstream installer
# for the three marine tables. Emitted as separate CREATE INDEX statements
# rather than inline INDEX clauses so SQLite accepts them.
_INDEXES: list[tuple[str, str, str]] = [
    ("coops_realtime", "idx_recent_coops", "station_id, dateTime"),
    ("tide_table", "idx_upcoming_tides", "station_id, tide_time"),
    ("ndbc_data", "idx_recent_ndbc", "station_id, dateTime"),
]

# Table name -> PRIMARY KEY column list.
_PRIMARY_KEYS: dict[str, str] = {
    "coops_realtime": "dateTime, station_id",
    "tide_table": "station_id, tide_time, tide_type",
    "ndbc_data": "dateTime, station_id",
}


def _load_config() -> configobj.ConfigObj | None:
    if not os.path.exists(_WEEWX_CONF):
        print(f"init_marine_schema: {_WEEWX_CONF} not found; skipping", file=sys.stderr)
        return None
    return configobj.ConfigObj(_WEEWX_CONF, file_error=True)


def _marine_enabled(config: configobj.ConfigObj) -> bool:
    """Prepare tables if EITHER signal of intent is set: ``[MarineDataService]
    enable`` truthy, or ``user.marine_data.MarineDataService`` listed in
    ``[Engine] [[Services]] data_services``. Users may reasonably enable one
    without the other (config the service now, register in data_services
    later, or vice versa)."""
    enable = config.get("MarineDataService", {}).get("enable")
    if enable is not None:
        try:
            if weeutil.weeutil.to_bool(enable):
                return True
        except (ValueError, TypeError):
            # to_bool rejects "on"/"off"/""/unknown; a bad value must not
            # crash the shim under set -e or s6 will not start weewxd.
            pass
    services = config.get("Engine", {}).get("Services", {})
    data_services = services.get("data_services", [])
    if isinstance(data_services, str):
        data_services = [data_services]
    return any(s.strip() == "user.marine_data.MarineDataService" for s in data_services)


def _build_columns(fields: dict[str, Any]) -> dict[str, dict[str, str]]:
    """Group YAML field definitions by their database_table into per-table
    ordered column dicts, starting with the two standard columns every
    marine table carries. station_id is VARCHAR(20) rather than TEXT so
    MariaDB accepts it in a PRIMARY KEY (TEXT-in-key needs a prefix
    length there); SQLite treats VARCHAR(N) as TEXT dynamically."""
    by_table: dict[str, dict[str, str]] = {}
    for field_config in fields.values():
        table = field_config.get("database_table", "archive")
        if table == "archive":
            continue
        if not _SQL_IDENT_RE.match(table):
            raise RuntimeError(f"unsafe marine database_table identifier: {table!r}")
        if table not in by_table:
            by_table[table] = {
                "dateTime": "INTEGER NOT NULL",
                "station_id": "VARCHAR(20) NOT NULL",
            }
        db_field = field_config["database_field"]
        db_type = field_config.get("database_type", "REAL")
        if not _SQL_IDENT_RE.match(db_field):
            raise RuntimeError(f"unsafe marine database_field identifier: {db_field!r}")
        if db_field in {"dateTime", "station_id"}:
            raise RuntimeError(f"YAML redeclares standard column {db_field!r}")
        if db_type not in _ALLOWED_SQL_TYPES:
            raise RuntimeError(f"unsafe marine database_type: {db_type!r}")
        by_table[table][db_field] = db_type
    if "tide_table" in by_table:
        overlap = _TIDE_OPERATIONAL_FIELDS.keys() & by_table["tide_table"].keys()
        if overlap:
            raise RuntimeError(
                f"YAML declares columns that operational-fields would clobber: {sorted(overlap)}"
            )
        by_table["tide_table"].update(_TIDE_OPERATIONAL_FIELDS)
    return by_table


def _create_tables(config: configobj.ConfigObj) -> None:
    import weewx.manager
    import yaml

    with open(_FIELDS_YAML) as f:
        yaml_data = yaml.safe_load(f)
    fields = yaml_data.get("fields", {})
    if not fields:
        raise RuntimeError(f"no 'fields' section in {_FIELDS_YAML}")

    by_table = _build_columns(fields)

    with weewx.manager.open_manager_with_config(
        config, "wx_binding", initialize=True
    ) as manager:
        for table, columns in sorted(by_table.items()):
            pk = _PRIMARY_KEYS.get(table)
            if pk is None:
                raise RuntimeError(f"no PRIMARY KEY defined for marine table {table}")
            col_sql = ", ".join(f"{name} {type_}" for name, type_ in columns.items())
            manager.connection.execute(
                f"CREATE TABLE IF NOT EXISTS {table} ({col_sql}, PRIMARY KEY ({pk}))"
            )
        for table, index_name, cols in _INDEXES:
            if table in by_table:
                manager.connection.execute(
                    f"CREATE INDEX IF NOT EXISTS {index_name} ON {table} ({cols})"
                )


def main() -> int:
    config = _load_config()
    if config is None:
        return 0
    if not _marine_enabled(config):
        print("init_marine_schema: marine_data not enabled; skipping")
        return 0

    print("init_marine_schema: creating marine tables (idempotent)")
    _create_tables(config)
    print("init_marine_schema: done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
