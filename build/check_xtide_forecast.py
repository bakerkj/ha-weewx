#!/usr/bin/env python3
# Copyright (c) 2026 Kenneth Baker <bakerkj@umich.edu>
# All rights reserved.

"""
In-image integration check: run the real XTideForecast service against a
scratch weewx.conf and scratch SQLite DB, then read the archive_forecast
table back to verify at least one XTide row was inserted.

Exercises the exact runtime pipeline a deployment with
    [Forecast]
        [[XTide]]
            location = ...
would follow on each archive interval — subprocess to /usr/bin/tide,
CSV parse by forecast.XTideForecast.parse, save via
Forecast.save_forecast (weewx.manager.addRecord on the forecast_binding
DB). No shortcuts around weewx or weewx-forecast.

Called from build/check_image.sh under a docker run of the built image;
exits 0 on success, non-zero on any failure.
"""

import sys
import tempfile
import textwrap

import configobj

import weewx.engine
import weewx.manager
import user.forecast as forecast_mod


def main() -> int:
    tmpdir = tempfile.mkdtemp(prefix="xtide-check-")
    conf_text = textwrap.dedent(f"""\
        WEEWX_ROOT = {tmpdir}
        debug = 0

        [Station]
            location = "test"
            latitude = 37.4583
            longitude = -122.1050
            altitude = 0, foot
            station_type = Simulator

        [Simulator]
            driver = weewx.drivers.simulator

        [DataBindings]
            [[forecast_binding]]
                database = forecast_sqlite
                table_name = archive
                manager = weewx.manager.Manager
                schema = user.forecast.schema

        [Databases]
            [[forecast_sqlite]]
                database_type = SQLite
                database_name = forecast.sdb

        [DatabaseTypes]
            [[SQLite]]
                driver = weedb.sqlite
                SQLITE_ROOT = {tmpdir}

        [Engine]
            [[Services]]

        [Forecast]
            [[XTide]]
                location = "Palo Alto Yacht Harbor, San Francisco Bay, California"
                single_thread = true
        """)
    config_dict = configobj.ConfigObj(conf_text.splitlines(), encoding="utf-8")

    # DummyEngine loads services against a config_dict without needing a
    # real station driver.
    engine = weewx.engine.DummyEngine(config_dict)

    # Real XTideForecast instantiation: ctor opens the SQLite DB via
    # weewx.manager.open_manager, creates the archive table, asserts
    # schema equality.
    svc = forecast_mod.XTideForecast(engine, config_dict)

    # Run the actual NEW_ARCHIVE_RECORD handler synchronously
    # (single_thread=true). do_forecast → get_forecast → save_forecast.
    svc.update_forecast(None)

    # Read back from the same forecast_binding DB the service just wrote.
    dbm_dict = weewx.manager.get_manager_dict_from_config(config_dict, svc.binding)
    with weewx.manager.open_manager(dbm_dict) as dbm:
        row = dbm.getSql("SELECT COUNT(*) FROM archive WHERE method = ?", ("XTide",))
    count = row[0] if row else 0
    if count < 1:
        print(
            "FAIL: 0 XTide rows in archive_forecast after do_forecast",
            file=sys.stderr,
        )
        return 1
    print(f"ok: {count} XTide rows inserted via weewx-forecast pipeline")
    return 0


if __name__ == "__main__":
    sys.exit(main())
