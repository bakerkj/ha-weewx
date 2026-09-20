# Copyright (c) 2026 Kenneth Baker <bakerkj@umich.edu>
# All rights reserved.

"""
In-image integration check: run the real init_marine_schema shim against
a scratch weewx.conf + scratch SQLite DB, then read the DB back to prove
the three marine tables (coops_realtime, tide_table, ndbc_data) were
actually created.

Also exercises the shim's guardrails via a MARINE_FIELDS_YAML env
override: reserved-prefix rejection, standard-column redeclaration
rejection, tide-operational-field overlap rejection, and the
to_bool-hostile enable fall-through. Every guard has a negative test
here so a future refactor that drops one goes red.

Fast standalone signal that catches shim breakage before the e2e even
boots. Called from build/check_image.sh under a docker run of the built
image; exits 0 on success, non-zero on any failure.
"""

from __future__ import annotations

import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import textwrap

EXPECTED_TABLES = ("coops_realtime", "tide_table", "ndbc_data")
SHIM = "/etc/scripts/init_marine_schema.py"
PYTHON = "/opt/weewx/bin/python3"


def _scratch_conf(
    tmpdir: str, db_path: str, enable: str = "true", data_service: bool = True
) -> str:
    services = "user.marine_data.MarineDataService" if data_service else ""
    conf_path = os.path.join(tmpdir, "weewx.conf")
    conf_text = textwrap.dedent(f"""\
        WEEWX_ROOT = /opt/weewx-data
        debug = 0

        [Station]
            location = "test"
            latitude = 0
            longitude = 0
            altitude = 0, foot
            station_type = Simulator

        [Simulator]
            driver = weewx.drivers.simulator

        [DataBindings]
            [[wx_binding]]
                database = archive_sqlite
                table_name = archive
                manager = weewx.manager.DaySummaryManager
                schema = schemas.wview_extended.schema

        [Databases]
            [[archive_sqlite]]
                database_type = SQLite
                database_name = {db_path}

        [DatabaseTypes]
            [[SQLite]]
                driver = weedb.sqlite

        [MarineDataService]
            enable = {enable}

        [Engine]
            [[Services]]
                data_services = {services}
        """)
    with open(conf_path, "w") as f:
        f.write(conf_text)
    return conf_path


def _run_shim(
    conf_path: str, fields_yaml: str | None = None
) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["WEEWX_CONF"] = conf_path
    if fields_yaml is not None:
        env["MARINE_FIELDS_YAML"] = fields_yaml
    return subprocess.run(
        [PYTHON, SHIM],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def _write_yaml(path: str, body: str) -> None:
    with open(path, "w") as f:
        f.write(body)


def _positive_happy_path(tmpdir: str) -> int:
    db_path = os.path.join(tmpdir, "wx.sdb")
    conf_path = _scratch_conf(tmpdir, db_path)
    proc = _run_shim(conf_path)
    if proc.returncode != 0:
        print(f"FAIL: happy path exited {proc.returncode}", file=sys.stderr)
        print(f"stderr:\n{proc.stderr}", file=sys.stderr)
        return 1
    if not os.path.exists(db_path):
        print(f"FAIL: happy path ran but no DB at {db_path}", file=sys.stderr)
        return 1
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"
        ).fetchall()
    tables = {r[0] for r in rows}
    missing = [t for t in EXPECTED_TABLES if t not in tables]
    if missing:
        print(f"FAIL: happy path missing marine tables: {missing}", file=sys.stderr)
        print(f"       tables present: {sorted(tables)}", file=sys.stderr)
        return 1
    print(f"ok: happy path created {list(EXPECTED_TABLES)}")
    return 0


def _enable_fallthrough_on_hostile_value(tmpdir: str) -> int:
    # `enable = on` (a common config-file spelling) trips to_bool's
    # ValueError. The shim must NOT propagate the exception or set -euo
    # pipefail in weewx-init.sh blocks weewxd from starting.
    db_path = os.path.join(tmpdir, "hostile.sdb")
    conf_path = _scratch_conf(tmpdir, db_path, enable="on", data_service=True)
    proc = _run_shim(conf_path)
    if proc.returncode != 0:
        print(f"FAIL: to_bool fallthrough exited {proc.returncode}", file=sys.stderr)
        print(f"stderr:\n{proc.stderr}", file=sys.stderr)
        return 1
    # Fall-through must land on the data_services gate; tables get created.
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name IN "
            "('coops_realtime','tide_table','ndbc_data')"
        ).fetchall()
    if len(rows) != 3:
        print(
            f"FAIL: to_bool fallthrough didn't create tables; got {rows}",
            file=sys.stderr,
        )
        return 1
    print("ok: enable=on falls through to data_services check")
    return 0


def _negative(tmpdir: str, label: str, yaml_body: str, expected_substring: str) -> int:
    db_path = os.path.join(tmpdir, f"{label}.sdb")
    conf_path = _scratch_conf(tmpdir, db_path)
    yaml_path = os.path.join(tmpdir, f"{label}.yaml")
    _write_yaml(yaml_path, yaml_body)
    proc = _run_shim(conf_path, fields_yaml=yaml_path)
    if proc.returncode == 0:
        print(f"FAIL: {label}: shim accepted hostile YAML", file=sys.stderr)
        return 1
    if expected_substring not in proc.stderr:
        print(
            f"FAIL: {label}: expected {expected_substring!r} in stderr; got:\n{proc.stderr}",
            file=sys.stderr,
        )
        return 1
    if os.path.exists(db_path):
        with sqlite3.connect(db_path) as conn:
            rows = conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name IN "
                "('coops_realtime','tide_table','ndbc_data')"
            ).fetchall()
        if rows:
            print(
                f"FAIL: {label}: marine tables created despite reject", file=sys.stderr
            )
            return 1
    print(f"ok: {label} rejected")
    return 0


def _reserved_prefix_rejected(tmpdir: str) -> int:
    return _negative(
        tmpdir,
        "reserved-prefix",
        textwrap.dedent("""\
            fields:
              bogus:
                database_table: sqlite_evil
                database_field: value
                database_type: REAL
            """),
        "database_table identifier",
    )


def _standard_column_redeclare_rejected(tmpdir: str) -> int:
    return _negative(
        tmpdir,
        "std-col-redeclare",
        textwrap.dedent("""\
            fields:
              bad:
                database_table: coops_realtime
                database_field: station_id
                database_type: REAL
            """),
        "redeclares standard column",
    )


def _tide_overlap_rejected(tmpdir: str) -> int:
    return _negative(
        tmpdir,
        "tide-overlap",
        textwrap.dedent("""\
            fields:
              collision:
                database_table: tide_table
                database_field: tide_time
                database_type: TEXT
            """),
        "operational-fields would clobber",
    )


def main() -> int:
    tmpdir = tempfile.mkdtemp(prefix="marine-schema-check-")
    try:
        checks = [
            _positive_happy_path,
            _enable_fallthrough_on_hostile_value,
            _reserved_prefix_rejected,
            _standard_column_redeclare_rejected,
            _tide_overlap_rejected,
        ]
        fail = 0
        for check in checks:
            fail |= check(tmpdir)
        return fail
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
