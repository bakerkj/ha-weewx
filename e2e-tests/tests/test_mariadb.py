# Copyright (c) 2026 Kenneth Baker <bakerkj@umich.edu>
# All rights reserved.

"""MariaDB e2e — asserts that weewx + the addon image writes archive rows
to MariaDB and that the Seasons report is generated + served by nginx.

Run inside docker-compose.mariadb.yml against the live addon container
(MariaDB-backed via e2e-tests/configs/mariadb/weewx.conf). The weewx service's
healthcheck gates this container to start only once an archive record
exists, so the data + report are already present by the time these run.
"""

import os
import time

import pymysql
import pytest
import requests

MARIADB = dict(
    host=os.environ.get("MARIADB_HOST", "mariadb"),
    port=int(os.environ.get("MARIADB_PORT", "3306")),
    user=os.environ.get("MARIADB_USER", "weewx"),
    password=os.environ.get("MARIADB_PASSWORD", "weewxpass"),
    database=os.environ.get("MARIADB_DB", "weewx"),
)
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
