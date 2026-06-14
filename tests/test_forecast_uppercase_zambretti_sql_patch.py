# Copyright (c) 2026 Kenneth Baker <bakerkj@umich.edu>
# All rights reserved.

"""Regression tests for patches/extensions/0004-forecast-uppercase-zambretti-sql.patch.

chaunceygardiner/weewx-forecast v4.1 emits its Zambretti SELECT with
lowercase SQL keywords. weewx core's weedb/mysql.py auto-backticks reserved
words used as column names; the lowercase ``desc`` direction keyword in
``order by dateTime desc limit 1`` was getting rewritten into a backticked
column name, producing invalid MariaDB syntax. Uppercasing the statement
keeps the rewriter from touching direction keywords. SQLite is
case-insensitive on keywords so it is unaffected.
"""

import pathlib

PATCH = (
    pathlib.Path(__file__).resolve().parent.parent
    / "patches/extensions/0004-forecast-uppercase-zambretti-sql.patch"
)


def test_zambretti_sql_uppercased():
    """The Zambretti SELECT must be fully uppercased so the weedb/mysql
    auto-backtick rewriter (see patches/weewx/0001-weedb-mysql-quote-desc-offset)
    does not mangle the lowercase ``desc`` direction keyword into a backticked
    column name and break MariaDB syntax.
    """
    src = PATCH.read_text()
    assert (
        "SELECT dateTime,zcode FROM %s WHERE method = 'Zambretti' ORDER BY dateTime DESC LIMIT 1"
        in src
    ), (
        "Zambretti SQL must use uppercase SELECT/FROM/WHERE/ORDER BY/DESC/LIMIT "
        "so weedb's reserved-word rewriter cannot backtick the `desc` keyword"
    )
    assert (
        "-            sql = \"select dateTime,zcode from %s where method = 'Zambretti' order by dateTime desc limit 1\""
        in src
    ), (
        "patch must explicitly delete the lowercase SQL line; without the "
        "removal line the rewriter still hits the lowercase `desc` keyword"
    )
