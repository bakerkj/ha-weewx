# WeeWX Home Assistant Add-on

[WeeWX](https://weewx.com/) is a free, open-source weather station server
written in Python. This add-on runs WeeWX 5.3 inside Home Assistant with a
bundled set of popular extensions, and serves your reports through the HA
ingress sidebar via nginx.

The add-on is intentionally hands-off: there are no big options forms in the HA
UI. Instead, you edit a real `weewx.conf` — `/config/weewx.conf` inside the
container, surfaced on the host at `/addon_configs/<addon-slug>/weewx.conf` (see
[Editing the configuration](#editing-the-configuration)) — the same way you
would on any standalone WeeWX install.

---

## Installation

1. In Home Assistant, go to **Settings → Add-ons → Add-on Store**.
2. Click the **⋮ menu → Repositories** and add:
   ```
   https://github.com/bakerkj/ha-weewx
   ```
3. Find **WeeWX** in the store and click **Install** → **Start**.
4. Open `/addon_configs/<addon-slug>/weewx.conf` (e.g. via the **File Editor**
   or **Studio Code Server** add-on) and edit the `[Station]`, `[Simulator]`,
   `[StdReport]`, etc. sections to match your hardware and preferences.
5. Restart the add-on.

---

## Quick start

On first start the add-on copies a starter `weewx.conf` template into
`/config/weewx.conf`. The template configures:

- **`[Station]`** — placeholder location/lat/lon (edit these).
- **Driver** — `Simulator` (replace with your real driver section, e.g.
  `[Vantage]`, `[FineOffsetUSB]`, `[Interceptor]`).
- **Database** — SQLite at `/config/weewx.sdb`. No external DB required out of
  the box.
- **`[StdReport]`** — `Seasons` skin, output written to `/config/www/` so the HA
  ingress panel automatically serves your reports.
- **No extensions wired up** — see [Bundled extensions](#bundled-extensions)
  below for how to enable any of the 17 pre-installed ones.

To re-seed from the template, delete `/config/weewx.conf` and restart.

---

## Editing the configuration

Edit `/addon_configs/<addon-slug>/weewx.conf` directly — the add-on reads it
as-is on every restart and never overwrites it. Standard `weewx.conf` syntax
(ConfigObj INI), full reference:
<https://weewx.com/docs/5.3/reference/weewx-options/>.

> **Where is `<addon-slug>`?** Inside the container the file is always
> `/config/weewx.conf`. Home Assistant surfaces the container's `/config` on the
> host under `/addon_configs/<addon-slug>/`, where `<addon-slug>` is
> `local_weewx` for a locally-installed add-on, or `<repository-id>_weewx` when
> installed from this repository in the add-on store. Run `ls /addon_configs/`
> from the **Terminal & SSH** add-on to find the exact name.

After editing, restart the add-on for changes to take effect.

---

## Add-on options

There are no HA UI options. Everything is configured by editing
`/config/weewx.conf`. To add an extension that isn't bundled, fork this repo and
add it to the [Dockerfile](Dockerfile) so it's baked into the image.

---

## Database

The default is **SQLite** at `/config/weewx.sdb` — auto-created on first weewxd
start, persists across image upgrades, no external dependency.

To switch to **MariaDB**:

1. Install the **MariaDB** add-on, create a `weewx` database and user.
2. In `/config/weewx.conf`, change `[DataBindings] [[wx_binding]]` `database`
   from `archive_sqlite` to `archive_mysql`.
3. Fill in the credentials in `[Databases] [[archive_mysql]]`.
4. Restart.

Both `[[archive_sqlite]]` and `[[archive_mysql]]` are pre-defined in the
template — only the `wx_binding`'s `database` field selects which one is active.

---

## MQTT to Home Assistant

The
[felddy/weewx-home-assistant](https://github.com/felddy/weewx-home-assistant)
extension is bundled. To publish your weather data to HA via MQTT discovery, add
a `[HomeAssistant]` section to `/config/weewx.conf`:

```ini
[HomeAssistant]
    node_id                = weewx
    discovery_topic_prefix = homeassistant
    state_topic_prefix     = weather
    unit_system            = METRICWX

    [[mqtt]]
        hostname = core-mosquitto
        port     = 1883
        username = your-mqtt-user
        password = your-mqtt-pass
        use_tls  = False

    [[station]]
        name         = My Weather Station
        model        = Vantage Pro2
        manufacturer = Davis
```

…and add `weewx_ha.Controller` to `[Engine] [[Services]] report_services`.

Full options: <https://github.com/felddy/weewx-home-assistant#configuration>.

---

## Web reports & ingress

nginx serves `/config/www/` on the HA ingress port. By default the seeded
template writes WeeWX reports there (`HTML_ROOT = /config/www`) so the WeeWX UI
shows in the HA sidebar with no extra configuration.

You can also drop arbitrary static files (HTML, CSS, JS, images) into
`/config/www/` and they will be served alongside.

---

## Bundled extensions

These extensions are pre-installed at `/opt/weewx-data/bin/user/` and (where
applicable) `/opt/weewx-data/skins/`. To enable one, add its service path to the
appropriate `*_services` entry in `[Engine] [[Services]]` and add its
configuration section to `weewx.conf`.

| Extension            | Service path                       | Service list       | Notes                                         |
| -------------------- | ---------------------------------- | ------------------ | --------------------------------------------- |
| weewx-home-assistant | `weewx_ha.Controller`              | `report_services`  | MQTT discovery for HA (felddy)                |
| emoncms              | `user.emoncms.EmonCMS`             | `restful_services` | matthewwall                                   |
| exfoliation          | _(skin only)_                      | —                  | Replacement skin                              |
| forecast             | `user.forecast.NWSForecast` (etc.) | `archive_services` | Multiple forecast providers, chaunceygardiner |
| fuzzy-archer         | _(skin only)_                      | —                  | Bootstrap-themed skin                         |
| opensensemap         | `user.opensensemap.OpenSenseMap`   | `restful_services` | sbsrouteur                                    |
| owm                  | `user.owm.OpenWeatherMap`          | `restful_services` | matthewwall                                   |
| previmeteo           | `user.previmeteo.Previmeteo`       | `restful_services` | Patched for Python 3                          |
| purpleair            | `user.purpleair.PurpleAirMonitor`  | `process_services` | bakerkj                                       |
| realtime-gauge-data  | `user.rtgd.RealtimeGaugeData`      | `report_services`  | + RealtimeGauges skin                         |
| thingspeak           | `user.thingspeak.ThingSpeak`       | `restful_services` | matthewwall                                   |
| wcloud               | `user.wcloud.WeatherCloud`         | `restful_services` | matthewwall                                   |
| wetter               | `user.wetter.Wetter`               | `restful_services` | matthewwall                                   |
| windfinder           | `user.windfinder.WindFinder`       | `restful_services` | matthewwall                                   |
| windguru             | `user.windguru.WindGuru`           | `restful_services` | claudobahn                                    |
| windy                | `user.windy.Windy`                 | `restful_services` | matthewwall                                   |

---

## Hardware setup

USB and serial weather station devices are passed through automatically:
`/dev/ttyUSB0..2`, `/dev/ttyS0..1`, `/dev/ttyACM0..1`.

For other devices (e.g. a USB radio for the Interceptor driver), add them to the
`devices` array in `config.json` and rebuild, or use the **Local add-on**
workflow.

---

## Troubleshooting

**weewxd isn't starting / errors in the log**

Check the add-on log. Common causes:

- Syntax error in `/config/weewx.conf` — run `weewxd --check-config` from a
  terminal in the container.
- Driver section missing or misnamed — `[Station] station_type` must exactly
  match the section header below it.
- Database credentials wrong (if you switched to MariaDB).

**Reset to a clean conf**

```
docker exec -it addon_local_weewx rm /config/weewx.conf
ha addons restart weewx
```

(or just delete the file via File Editor and restart from the HA UI).

**WeeWX reports aren't showing in the ingress panel**

Make sure `[StdReport] HTML_ROOT = /config/www` (the default in the template).

---

## License

MIT — see [LICENSE](LICENSE).

WeeWX itself is GPL v3+ — <https://weewx.com/>.
