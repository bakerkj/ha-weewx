# Copyright (c) 2026 Kenneth Baker <bakerkj@umich.edu>
# All rights reserved.

# Originally by Ken Baker (bakerkj). Ported from Python 2 / WeeWX 3 to
# Python 3 / WeeWX 5 for the ha-weewx Home Assistant add-on.
import logging
import queue
from traceback import format_exc

import weeutil
import weewx
import weewx.manager
import weewx.restx
import weewx.units
from weeutil.weeutil import to_bool, accumulateLeaves

log = logging.getLogger(__name__)


def logdbg(msg):
    log.debug(msg)


def loginf(msg):
    log.info(msg)


def logerr(msg):
    log.error(msg)


class LogToFile(weewx.restx.StdRESTful):
    """Append a one-line summary of each archive record to a local file."""

    def __init__(self, engine, config_dict):
        super().__init__(engine, config_dict)

        try:
            _log_to_file_dict = accumulateLeaves(
                config_dict["StdRESTful"]["LogToFile"], max_level=1
            )
            _log_to_file_dict["path"]
        except KeyError as e:
            logdbg("LogToFile: data will not be logged: missing option %s" % e)
            return

        _manager_dict = weewx.manager.get_manager_dict(
            config_dict["DataBindings"], config_dict["Databases"], "wx_binding"
        )

        _log_to_file_dict.setdefault("log_success", False)
        _log_to_file_dict.setdefault("log_failure", False)
        _log_to_file_dict.setdefault("max_backlog", 0)
        _log_to_file_dict.setdefault("max_tries", 1)

        self.loop_queue = queue.Queue()
        self.loop_thread = LogToFileThread(
            self.loop_queue, _manager_dict, **_log_to_file_dict
        )
        self.loop_thread.start()

        self.bind(weewx.NEW_LOOP_PACKET, self.new_loop_packet)
        self.bind(weewx.NEW_ARCHIVE_RECORD, self.new_archive_record)

        loginf("LogToFile: data will be logged to file %s" % _log_to_file_dict["path"])

    def new_loop_packet(self, event):
        self.loop_queue.put(event.packet)

    def new_archive_record(self, event):
        self.loop_queue.put(event.record)


class LogToFileThread(weewx.restx.RESTThread):
    """Worker thread that drains the queue and writes one CSV-ish line per record."""

    _tuple_type_mapping = {
        "degree_F": "F",
        "degree_compass": "degree",
        "watt_per_meter_squared": "watts/m^2",
    }
    _skip_keys = {
        "usUnits": True,
        "dateTime": True,
    }
    _data_map = {
        "UV": ["UV", False, False],
        "dayET": ["ET", "%.3f", False],
        "forecastRule": ["rule", "%d", False],
        "monthET": ["ET", "%.3f", False],
        "txBatteryStatus": ["status", "%d", False],
        "yearET": ["ET", "%.3f", False],
        "sunrise": ["time", "%d", False],
        "sunset": ["time", "%d", False],
        "station": ["", False, True],
        "interval": ["minutes", "%d", False],
    }

    def __init__(
        self,
        q,
        manager_dict,
        path,
        skip_upload=False,
        post_interval=None,
        max_backlog=0,
        stale=None,
        log_success=True,
        log_failure=True,
        timeout=60,
        max_tries=3,
        retry_wait=5,
    ):
        super().__init__(
            q,
            protocol_name="LogToFile",
            manager_dict=manager_dict,
            post_interval=post_interval,
            max_backlog=max_backlog,
            stale=stale,
            log_success=log_success,
            log_failure=log_failure,
            timeout=timeout,
            max_tries=max_tries,
            retry_wait=retry_wait,
        )
        self.path = path
        self.skip_upload = to_bool(skip_upload)
        self.last_result = None
        self.last_result_time = None

    def process_record(self, record, archive):
        """Log record to disk."""
        # Normalize to the database's unit system before querying for
        # cumulative aggregates. RESTThread.get_record() does a strict
        # unit-system comparison between the incoming record and the
        # database; loop packets that arrive before StdConvert has converted
        # them (or any record from a driver that emits a different unit
        # system than the database stores) would otherwise raise
        # "Inconsistent units …" and kill the worker thread.
        if (
            archive.std_unit_system is not None
            and record.get("usUnits") != archive.std_unit_system
        ):
            record = weewx.units.to_std_system(record, archive.std_unit_system)
        _full_record = self.get_record(record, archive)
        _us_record = weewx.units.to_US(_full_record)

        if self.skip_upload:
            return

        try:
            results = []

            for k in _us_record.keys():
                raw_value_tuple = weewx.units.as_value_tuple(_us_record, k)
                value_helper = weewx.units.ValueHelper(raw_value_tuple)

                if (k in LogToFileThread._skip_keys) or (raw_value_tuple[0] is None):
                    continue

                if raw_value_tuple[1] in LogToFileThread._tuple_type_mapping:
                    label = LogToFileThread._tuple_type_mapping[raw_value_tuple[1]]
                else:
                    label = value_helper.formatter.get_label_string(
                        raw_value_tuple[1]
                    ).strip()

                try:
                    value = value_helper.toString(addLabel=False)
                except TypeError:
                    if isinstance(raw_value_tuple[0], str):
                        value = raw_value_tuple[0]
                    else:
                        continue

                if k in LogToFileThread._data_map:
                    mapping = LogToFileThread._data_map[k]
                    label = mapping[0]
                    if mapping[1]:
                        value = mapping[1] % (raw_value_tuple[0])

                if label == "" and not LogToFileThread._data_map.get(k, False):
                    continue

                results.append("%s:%s:%s" % (k, value, label))

            results.sort()

            if (
                (self.last_result_time is None)
                or (self.last_result is None)
                or ((_us_record["dateTime"] - self.last_result_time) > 60.0)
                or (self.last_result != results)
            ):
                self.last_result_time = _us_record["dateTime"]
                self.last_result = results

                with open(self.path, "a") as out:
                    print(
                        ",".join(
                            [
                                weeutil.weeutil.timestamp_to_string(
                                    _us_record["dateTime"]
                                )
                            ]
                            + results
                        ),
                        file=out,
                    )

        except Exception as e:
            logerr("LogToFile: %s" % str(e))
            logerr("LogToFile: %s" % format_exc())
