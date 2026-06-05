# Copyright (c) 2026 Kenneth Baker <bakerkj@umich.edu>
# All rights reserved.

"""Comprehensive felddy unit/device_class sweep.

For every ``KEY_CONFIG`` entry that declares a ``device_class``, assert
that ``get_unit_metadata`` returns a ``unit_of_measurement`` that Home
Assistant actually accepts for that device_class — across all three unit
systems (METRIC, METRICWX, US).

Catches the cases ``patches/venv/0006`` fixes AND any future regression
(a new ``KEY_CONFIG`` entry, a new weewx unit, a new HA device_class
restriction) at build time, before anyone deploys an image that silently
fails HA discovery validation.

Reads HA's canonical ``DEVICE_CLASS_UNITS`` mapping FROM HOME ASSISTANT
ITSELF (pinned to the version the supervisor ships) rather than from a
hand-copied table — so the test stays in sync with HA's actual
allowed-units list automatically as HA evolves.

The check asserts a NECESSARY (not sufficient) condition: felddy emits
HA-known unit names. Live deployments run whatever the supervisor ships;
the HA pin in the test layer can lag slightly.

PYTHONPATH must include ``/opt/weewx-data/bin`` so this script can import
bundled extensions whose module-level code registers ``obs_group_dict``
entries — specifically ``user.rain24h`` sets
``weewx.units.obs_group_dict['rain24h'] = 'group_rain'`` at import time.
Without that, ``get_unit_metadata("rain24h", ...)`` returns ``None`` and
the sweep silently skips ``rain24h`` (a real validation hole) rather than
checking that the rain24h discovery payload gets a HA-valid unit.
"""

import sys

# Import bundled extensions whose module-level code registers
# obs_group_dict entries. Each such import must happen BEFORE any
# get_unit_metadata call for a key the extension contributes a unit for.
import user.rain24h  # noqa: F401  -- registers 'rain24h' -> 'group_rain'

from weewx_ha.utils import KEY_CONFIG, UnitSystem, get_unit_metadata

# KEY_CONFIG TEMPLATE-base entries: felddy keeps these so get_key_config can
# strip numeric suffixes (extraTemp5 -> extraTemp -> friendly name "Extra
# Temperature 5"). The base name itself NEVER appears as a real measurement
# in a loop packet, so calling get_unit_metadata on it correctly returns no
# unit AND correctly emits a "No unit found" WARNING -- but that warning is
# noise here because we'd never check the base key in production. Skip them.
# (Do NOT silence the logger -- those warnings catch real issues like a
# missed obs_group_dict registration. Skipping at the iteration layer
# preserves real-warning visibility.)
TEMPLATE_BASE_KEYS = {
    "extraHumid",
    "extraTemp",
    "leafTemp",
    "leafWet",
    "soilMoist",
    "soilTemp",
    "windburn",
}

# Known upstream felddy bugs NOT in scope for patches/venv/0006 -- they
# need different fixes (device_class change, concentration conversion,
# or a felddy code change), not a UNIT_METADATA addition. Tracked
# separately; revisit when those PRs land.
SKIP_KEYS = {
    "o3",  # device_class=ozone, emits 'ppm'; HA wants µg/m³
    "so2",  # device_class=sulphur_dioxide, emits 'ppm'; HA wants µg/m³
    "rms",  # device_class=wind_speed, emits '<speed>_per_hour2'
    "vecavg",  # device_class=wind_speed, emits '<speed>_per_hour2'
}


def main() -> None:
    from homeassistant.components.sensor.const import DEVICE_CLASS_UNITS

    # DEVICE_CLASS_UNITS maps SensorDeviceClass enum -> set of allowed
    # units. Each unit in the set is a str, a StrEnum member, or None
    # ("no unit"). Normalize to {device_class_string: {unit_string, ...}}
    # for direct comparison against felddy's unit_of_measurement strings.
    ha_allowed: dict[str, set[str]] = {}
    for dc, units in DEVICE_CLASS_UNITS.items():
        dc_name = dc.value if hasattr(dc, "value") else str(dc)
        ha_allowed[dc_name] = {
            (u.value if hasattr(u, "value") else u) for u in units if u is not None
        }

    bad: list[tuple[str, str, str, str]] = []
    checked = 0
    skipped_dc: set[str] = set()
    skipped_keys: set[str] = set()
    for key, cfg in KEY_CONFIG.items():
        if key in TEMPLATE_BASE_KEYS:
            # Skip BEFORE calling get_unit_metadata so we don't emit a
            # noisy "No unit found" WARNING for an entry that never
            # appears as a real measurement.
            continue
        dc = cfg.get("metadata", {}).get("device_class")
        if not dc:
            continue
        if dc not in ha_allowed:
            # enum / timestamp / binary device_class -- HA does no unit check
            skipped_dc.add(dc)
            continue
        if key in SKIP_KEYS:
            skipped_keys.add(key)
            continue
        for us in UnitSystem:
            meta = get_unit_metadata(key, us)
            unit = meta.get("unit_of_measurement")
            if unit is None:
                continue  # explicitly None is fine (e.g. unix_epoch)
            checked += 1
            if unit not in ha_allowed[dc]:
                bad.append((key, dc, us.name, unit))

    if bad:
        print("FAIL: felddy emits HA-invalid unit_of_measurement for these combos:")
        for row in bad:
            print(
                f"  key={row[0]:20s} device_class={row[1]:25s} "
                f"unit_system={row[2]:8s} bad_unit={row[3]!r}"
            )
        sys.exit(1)
    print(
        f"felddy unit/device_class sweep OK: {checked} (key, unit_system) combos "
        f"checked against homeassistant DEVICE_CLASS_UNITS; 0 mismatches"
    )
    if skipped_dc:
        print(f"  (device_classes with no unit validation: {sorted(skipped_dc)})")
    if skipped_keys:
        print(f"  (known-broken keys skipped: {sorted(skipped_keys)})")


if __name__ == "__main__":
    main()
