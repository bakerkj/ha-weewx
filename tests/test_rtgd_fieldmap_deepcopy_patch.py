# Copyright (c) 2026 Kenneth Baker <bakerkj@umich.edu>
# All rights reserved.

"""Regression tests for patches/extensions/0013-rtgd-fieldmap-deepcopy.patch.

``RealtimeGaugeDataThread.__init__`` reads ``FieldMap`` (defaulting to the
module global ``DEFAULT_FIELD_MAP``) and ``FieldMapExtensions`` (from the
configobj-backed weewx.conf section), then mutates each entry in place:
``_field_map[field[0]]['default'] = _vt`` (where ``_vt`` is a ValueTuple).
The assignment is to a reference, so the mutation leaks into both
``DEFAULT_FIELD_MAP`` and the configobj section. On a second ``__init__``
in the same process (e.g. after a driver WeeWxIOError trips weewxd's
retry loop) the now-ValueTuple defaults blow up the
``float(_default[0])`` path with TypeError. ``copy.deepcopy`` is *not*
usable here: configobj's Section invokes the interpolation engine and
explodes against the [Logging] formatter's ``%(asctime)s`` token.
"""

import pathlib

PATCH = (
    pathlib.Path(__file__).resolve().parent.parent
    / "patches/extensions/0013-rtgd-fieldmap-deepcopy.patch"
)


def test_fieldmap_built_as_fresh_nested_dict():
    """The merged field map must be built as a fresh dict-of-dicts via
    ``dict(_src_map[k])`` so the per-entry ``['default'] = _vt`` mutation
    does NOT leak into ``DEFAULT_FIELD_MAP`` or the configobj section. A
    second __init__ otherwise re-reads ValueTuple defaults and crashes on
    ``float(<ValueTuple>)`` in the len==1 branch.
    """
    src = PATCH.read_text()
    assert "_field_map = {k: dict(_src_map[k]) for k in _src_map}" in src, (
        "field map must be rebuilt as a fresh dict-of-dicts; alias to "
        "DEFAULT_FIELD_MAP leaks ValueTuple mutations across re-inits"
    )
    assert "_extensions = {k: dict(_src_ext[k]) for k in _src_ext}" in src, (
        "FieldMapExtensions must also be copied; otherwise mutation "
        "leaks into the configobj section"
    )


def test_fieldmap_copies_each_inner_section():
    """The fix must clone *each inner section* via ``dict(_src_map[k])`` —
    not just rebind the outer name — because the per-field mutation
    ``_field_map[field[0]]['default'] = _vt`` writes into the *inner* dict.
    A shallow outer copy alone still aliases the inner Section objects and
    re-exposes the second-init TypeError on float(<ValueTuple>).
    """
    src = PATCH.read_text()
    added_lines = [
        ln for ln in src.splitlines() if ln.startswith("+") and not ln.startswith("+++")
    ]
    joined = "\n".join(added_lines)
    assert "dict(_src_map[k]) for k in _src_map" in joined, (
        "field-map clone must copy each inner section; a shallow outer "
        "rebind leaves the inner default dicts aliased and re-exposes the bug"
    )
    assert "dict(_src_ext[k]) for k in _src_ext" in joined, (
        "FieldMapExtensions clone must also copy each inner section"
    )
