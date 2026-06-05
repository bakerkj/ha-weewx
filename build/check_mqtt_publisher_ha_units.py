# Copyright (c) 2026 Kenneth Baker <bakerkj@umich.edu>
# All rights reserved.

"""MQTT publisher (by felddy) -> Home Assistant unit validation.

For every ``KEY_CONFIG`` entry the MQTT publisher (by felddy) publishes
with a ``device_class``, verify the discovery payload's
``unit_of_measurement`` is one Home Assistant accepts -- across all
three weewx unit systems (METRIC, METRICWX, US).

``DEVICE_CLASS_UNITS`` is imported from homeassistant itself rather
than hand-copied, so the allowed-units mapping stays in sync as HA
evolves. Necessary but not sufficient: HA may reject a discovery
payload for reasons unrelated to unit names, and live supervisors run
whatever HA version they ship (which may differ from the HA pin used
here).

``PYTHONPATH`` must include ``/opt/weewx-data/bin`` so this script can
import ``user.rain24h``, whose module-level code registers
``weewx.units.obs_group_dict['rain24h'] = 'group_rain'``. Without it,
``get_unit_metadata("rain24h", ...)`` returns ``None`` and ``rain24h``
is silently skipped instead of validated.
"""

import sys

# Import bundled extensions whose module-level code registers
# obs_group_dict entries. Each such import must happen BEFORE any
# get_unit_metadata call for a key the extension contributes a unit for.
import user.rain24h  # noqa: F401  -- registers 'rain24h' -> 'group_rain'

from weewx_ha.utils import KEY_CONFIG, UnitSystem, get_unit_metadata

# KEY_CONFIG TEMPLATE-base entries: the MQTT publisher (by felddy) keeps
# these so get_key_config can strip numeric suffixes (extraTemp5 ->
# extraTemp -> friendly name "Extra Temperature 5"). The base name itself
# NEVER appears as a real measurement
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

# Known upstream bugs in the MQTT publisher (by felddy) that are out of
# scope here: they need different fixes (device_class change,
# concentration conversion, or an upstream code change), not a
# UNIT_METADATA addition.
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
    # for direct comparison against the MQTT publisher's (by felddy)
    # unit_of_measurement strings.
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
        print(
            "FAIL: the MQTT publisher (by felddy) emits HA-invalid "
            "unit_of_measurement for these combos:"
        )
        for row in bad:
            print(
                f"  key={row[0]:20s} device_class={row[1]:25s} "
                f"unit_system={row[2]:8s} bad_unit={row[3]!r}"
            )
        sys.exit(1)
    print(
        f"MQTT publisher (by felddy) -> HA unit validation OK: "
        f"{checked} (key, unit_system) combos checked against "
        f"homeassistant DEVICE_CLASS_UNITS; 0 mismatches"
    )
    if skipped_dc:
        print(f"  (device_classes with no unit validation: {sorted(skipped_dc)})")
    if skipped_keys:
        print(f"  (known-broken keys skipped: {sorted(skipped_keys)})")


if __name__ == "__main__":
    main()
