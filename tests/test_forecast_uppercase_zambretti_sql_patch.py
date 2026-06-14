# Copyright (c) 2026 Kenneth Baker <bakerkj@umich.edu>
# All rights reserved.

"""Behavioural regression test for
patches/extensions/0004-forecast-uppercase-zambretti-sql.patch.

forecast.py emits a SQL statement that uses lowercase ``select / from / where /
order by / desc / limit``. weewx core's weedb/mysql.py auto-backticks reserved
words used as column names, and the lowercase ``desc`` direction keyword would
be mangled. The patch uppercases the statement so the rewriter only acts on
real column names.
"""

import importlib
import inspect
import sys


def _get_zambretti_source():
    sys.modules.pop("forecast", None)
    forecast = importlib.import_module("forecast")
    return inspect.getsource(forecast.ForecastVariables.zambretti)


def test_zambretti_sql_keywords_are_uppercase():
    src = _get_zambretti_source()
    # The patched method must hold a string using the full uppercase form.
    assert (
        "SELECT dateTime,zcode FROM %s WHERE method = 'Zambretti' "
        "ORDER BY dateTime DESC LIMIT 1" in src
    ), (
        "Zambretti SELECT must use uppercase SQL keywords; lowercase `desc` "
        "collides with weedb/mysql.py auto-backticking and mangles the "
        "ORDER BY direction on MariaDB"
    )
    # And there must not be a lingering lowercase form.
    assert "order by dateTime desc limit 1" not in src, (
        "lowercase `desc` direction keyword must not appear in the Zambretti "
        "SQL; weedb/mysql.py would backtick it as a reserved column name"
    )
