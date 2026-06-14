# Copyright (c) 2026 Kenneth Baker <bakerkj@umich.edu>
# All rights reserved.

"""Behavioural regression test for
patches/extensions/0013-rtgd-fieldmap-deepcopy.patch.

``RealtimeGaugeDataThread.__init__`` mutates each FieldMap entry in place
with ``_field_map[field[0]]['default'] = _vt`` (a ValueTuple). Without the
patch the assignment leaks into ``DEFAULT_FIELD_MAP``, so a *second*
``__init__`` in the same Python process (after weewxd's engine retry
loop re-creates services from a WeeWxIOError stall) re-reads
ValueTuple-mutated defaults and crashes on ``float(<ValueTuple>)`` in
the ``len(_default) == 1`` branch.

We exec the patched field-map-build slice twice in the same process. The
second run must not raise.
"""

import importlib
import inspect
import sys
import textwrap
from unittest.mock import Mock


def _fieldmap_slice():
    sys.modules.pop("rtgd", None)
    rtgd = importlib.import_module("rtgd")
    src = inspect.getsource(rtgd.RealtimeGaugeDataThread.__init__)
    # Walk back to the start of the line so dedent sees consistent indent.
    needle = "_src_map = rtgd_config_dict.get('FieldMap'"
    body_start = src.index(needle)
    line_start = src.rfind("\n", 0, body_start) + 1
    end = src.index("self.field_map = _field_map", line_start)
    end = src.index("\n", end) + 1
    slice_text = textwrap.dedent(src[line_start:end])
    return rtgd, slice_text


def _run(rtgd, body, rtgd_config_dict):
    self_mock = Mock()
    self_mock.units_dict = {}
    # Pre-fill the only unit groups referenced by entries that carry a
    # 'default' (only the `bearing` field in the upstream default map).
    g = dict(vars(rtgd))
    g.update(
        {
            "self": self_mock,
            "rtgd_config_dict": rtgd_config_dict,
        }
    )

    # `self.units_dict[_group]` lookups need to succeed; fall back to a
    # dict-of-dicts that returns 'degree_compass' for the bearing default
    # (matches weewx convention for windDir/bearing fields).
    class _UnitsDict(dict):
        def __missing__(self, key):
            return "degree_compass"

    self_mock.units_dict = _UnitsDict()
    exec(body, g)
    return self_mock.field_map


def test_fieldmap_build_runs_idempotently_in_same_process():
    rtgd, body = _fieldmap_slice()
    cfg = {}  # falls back to DEFAULT_FIELD_MAP
    fm1 = _run(rtgd, body, cfg)
    # Without the patch, this second run would crash because
    # DEFAULT_FIELD_MAP['bearing']['default'] is now a ValueTuple, and
    # to_list(ValueTuple(...)) wraps it in a 1-element list, then
    # float(_default[0]) -> TypeError.
    fm2 = _run(rtgd, body, cfg)
    # Both runs produced a field map with the bearing default already
    # converted to a ValueTuple.
    assert "bearing" in fm1 and "bearing" in fm2
    assert isinstance(fm1["bearing"]["default"], rtgd.ValueTuple)
    assert isinstance(fm2["bearing"]["default"], rtgd.ValueTuple)
    # And the *module global* must not have been mutated.
    assert rtgd.DEFAULT_FIELD_MAP["bearing"]["default"] == 0, (
        "patched __init__ must not mutate the module-global DEFAULT_FIELD_MAP; "
        "a leaked ValueTuple default trips a TypeError in the second "
        "in-process __init__ via the weewxd engine retry loop"
    )
