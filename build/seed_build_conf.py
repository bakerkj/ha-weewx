# Copyright (c) 2026 Kenneth Baker <bakerkj@umich.edu>
# All rights reserved.

"""Generate the build-time stub weewx.conf at /opt/weewx-data/weewx.conf.

This file is consumed only by ``weectl extension install`` so it can find
WEEWX_ROOT (where to drop user modules under ``bin/user/`` and skins under
``skins/``). It is deleted at the end of the build — runtime uses
``/config/weewx.conf`` only.

Logging is configured so that:
  - stdout (the HA console) + a rotating ``/config/weewx.log`` get all
    weewx INFO messages, mirroring the runtime template.
  - root is WARNING, which suppresses weectl's ~14-line INFO startup banner
    on every extension install (~200 lines of noise across the 17 installs
    below). The install progress + any real warnings/errors still print.

Without a ``[Logging]`` block, weectl falls back to WeeWX's syslog default
(``/dev/log``) — absent in the build container — and spams a ``Logging
error`` traceback on every record. The rotating handler needs ``/config``
(the runtime addon_config mount) to exist at build time, so we create it.
"""

import os

import configobj


def main() -> None:
    os.makedirs("/config", exist_ok=True)

    c = configobj.ConfigObj()
    c["WEEWX_ROOT"] = "/opt/weewx-data"
    c["Station"] = {
        "station_type": "Simulator",
        "location": "Build",
        "latitude": "0",
        "longitude": "0",
        "altitude": "0, meter",
    }
    c["Simulator"] = {"driver": "weewx.drivers.simulator", "mode": "simulator"}
    c["StdRESTful"] = {"StationRegistry": {"register_this_station": "False"}}
    c["StdReport"] = {
        "HTML_ROOT": "/tmp/html",
        "SKIN_ROOT": "skins",
        "data_binding": "wx_binding",
    }
    c["StdConvert"] = {"target_unit": "METRICWX"}
    c["StdCalibrate"] = {"Corrections": {}}
    c["StdQC"] = {"MinMax": {}}
    c["StdArchive"] = {
        "archive_interval": "300",
        "archive_delay": "15",
        "no_catchup": "False",
        "data_binding": "wx_binding",
    }
    c["DataBindings"] = {
        "wx_binding": {
            "database": "archive_sqlite",
            "table_name": "archive",
            "manager": "weewx.manager.DaySummaryManager",
            "schema": "schemas.wview_extended.schema",
        }
    }
    c["Databases"] = {
        "archive_sqlite": {
            "database_name": "/tmp/weewx-build.sdb",
            "driver": "weedb.sqlite",
        }
    }
    c["Engine"] = {
        "Services": {
            "prep_services": "weewx.engine.StdTimeSynch",
            "data_services": "",
            "process_services": (
                "weewx.engine.StdConvert, weewx.engine.StdCalibrate, "
                "weewx.engine.StdQC, weewx.wxservices.StdWXCalculate"
            ),
            "xtype_services": (
                "weewx.wxxtypes.StdWXXTypes, weewx.wxxtypes.StdPressureCooker, "
                "weewx.wxxtypes.StdRainRater, weewx.wxxtypes.StdDelta"
            ),
            "archive_services": "weewx.engine.StdArchive",
            "restful_services": "weewx.restx.StdStationRegistry",
            "report_services": (
                "weewx.engine.StdPrint, weewx.engine.StdReport, weewx_ha.Controller"
            ),
        }
    }
    c["Logging"] = {
        "version": 1,
        "disable_existing_loggers": False,
        "root": {"level": "WARNING", "handlers": ["console", "rotate"]},
        "formatters": {
            "standard": {"format": "%(asctime)s  %(name)s %(levelname)s %(message)s"}
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "standard",
                "stream": "ext://sys.stdout",
            },
            "rotate": {
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "standard",
                "filename": "/config/log/weewx.log",
                "maxBytes": 10485760,
                "backupCount": 5,
                "encoding": "utf-8",
            },
        },
        "loggers": {
            "weewx": {
                "level": "INFO",
                "handlers": ["console", "rotate"],
                "propagate": False,
            }
        },
    }
    c.filename = "/opt/weewx-data/weewx.conf"
    c.write()
    print("Generated build-time weewx.conf")


if __name__ == "__main__":
    main()
