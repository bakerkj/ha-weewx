# Copyright (c) 2026 Kenneth Baker <bakerkj@umich.edu>
# All rights reserved.

"""MariaDB e2e - asserts that weewx + the addon image writes archive rows
to MariaDB and that the Seasons report is generated + served by nginx.

Run inside docker-compose.mariadb.yml against the live addon container
(MariaDB-backed via e2e-tests/configs/mariadb/weewx.conf). The weewx service's
healthcheck gates this container to start only once an archive record
exists, so the data + report are already present by the time these run.
"""

import os
import re
import time

import pymysql
import pytest
import requests

MARIADB = {
    "host": os.environ.get("MARIADB_HOST", "mariadb"),
    "port": int(os.environ.get("MARIADB_PORT", "3306")),
    "user": os.environ.get("MARIADB_USER", "weewx"),
    "password": os.environ.get("MARIADB_PASSWORD", "weewxpass"),
    "database": os.environ.get("MARIADB_DB", "weewx"),
}
WEEWX_URL = os.environ.get("WEEWX_URL", "http://weewx:8099").rstrip("/")


def test_archive_record_written():
    """At least one archive row landed in MariaDB."""
    conn = pymysql.connect(connect_timeout=10, **MARIADB)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM archive")
            (count,) = cur.fetchone()
    finally:
        conn.close()
    assert count >= 1, f"expected >=1 archive record, got {count}"


def test_seasons_report_served():
    """CopyGenerator drops seasons.css into HTML_ROOT; nginx serves it."""
    last = None
    for _ in range(30):
        try:
            r = requests.get(f"{WEEWX_URL}/seasons.css", timeout=10)
            last = r.status_code
            if r.status_code == 200:
                return
        except requests.RequestException as e:
            last = repr(e)
        time.sleep(2)
    pytest.fail(f"seasons.css never served 200 (last={last})")


def test_loopdata_json_served():
    """weewx-loopdata writes /dev/shm/weewx/loop-data.txt on every LOOP;
    nginx aliases it at /loop-data.txt. Prove the whole chain."""
    last = None
    for _ in range(30):
        try:
            r = requests.get(f"{WEEWX_URL}/loop-data.txt", timeout=10)
            last = r.status_code
            if r.status_code == 200 and r.text.strip().startswith("{"):
                return
        except requests.RequestException as e:
            last = repr(e)
        time.sleep(2)
    pytest.fail(f"/loop-data.txt never served valid JSON (last={last})")


def test_celestial_report_served():
    """weewx-celestial's Celestial skin renders index.html into HTML_ROOT."""
    last = None
    for _ in range(30):
        try:
            r = requests.get(f"{WEEWX_URL}/celestial/", timeout=10)
            last = r.status_code
            if r.status_code == 200:
                return
        except requests.RequestException as e:
            last = repr(e)
        time.sleep(2)
    pytest.fail(f"celestial page never served 200 (last={last})")


def test_celestial_report_has_dynamic_markers():
    """/celestial/ must contain PANEL_MARK and a countdown data-ts epoch.

    A 200 response only proves Cheetah opened the template; the panel
    bodies (countdown, geocentric, dome, pass) emit
    ``data-celestial="<ver>"`` (PANEL_MARK), and each countdown chip
    carries ``data-ts="<epoch>"`` set by Skyfield's next-event
    computation. Both being present proves the whole ``$celestial``
    pipeline resolved, not just the template shell.
    """
    r = requests.get(f"{WEEWX_URL}/celestial/", timeout=10)
    assert r.status_code == 200
    assert 'data-celestial="' in r.text, (
        f"celestial page missing PANEL_MARK (first 300 chars: {r.text[:300]!r})"
    )
    assert re.search(r'data-ts="\d{10,}"', r.text), (
        "celestial page has no countdown chip with data-ts "
        "(Skyfield next-event computation didn't render)"
    )


def test_marine_tables_created():
    """init_marine_schema.py runs at boot and creates the three marine
    tables in wx_binding."""
    conn = pymysql.connect(connect_timeout=10, **MARIADB)
    try:
        with conn.cursor() as cur:
            cur.execute("SHOW TABLES")
            tables = {row[0] for row in cur.fetchall()}
    finally:
        conn.close()
    expected = {"coops_realtime", "tide_table", "ndbc_data"}
    missing = expected - tables
    present_marine = sorted(expected & tables)
    assert not missing, (
        f"marine tables missing: {sorted(missing)}; marine tables present: {present_marine}"
    )
