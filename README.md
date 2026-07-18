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
- **Database** — SQLite at `/config/db/weewx.sdb`. No external DB required out
  of the box.
- **`[StdReport]`** — `Seasons` skin, output written to `/config/www/` so the HA
  ingress panel automatically serves your reports.
- **No extensions wired up** — see [Bundled extensions](#bundled-extensions)
  below for how to enable any of the 18 pre-installed ones.

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

Almost everything is configured by editing `/config/weewx.conf`. To add an
extension that isn't bundled, fork this repo and add it to the
[Dockerfile](Dockerfile) so it's baked into the image.

The HA addon Configuration tab exposes a small set of options for the
**hang-detection watchdog** — disabled by default. When enabled, it periodically
`HEAD`s a URL through the addon's own nginx and verifies the response's
`Last-Modified` is fresh. After N consecutive failures it SIGTERMs PID 1, which
tears the addon down so HA's "Watchdog" toggle can restart it.

| Option                           | Default | Meaning                                                                                                    |
| -------------------------------- | ------- | ---------------------------------------------------------------------------------------------------------- |
| `watchdog_path`                  | `""`    | URL path probed through nginx (e.g. `/index.html`, `/gauge-data.txt`). Empty = watchdog disabled.          |
| `watchdog_max_age_seconds`       | `600`   | Max `Last-Modified` age before a probe counts as a failure. Set to the cadence of whatever writes the URL. |
| `watchdog_consecutive_failures`  | `3`     | How many failures in a row before the addon is torn down.                                                  |
| `watchdog_interval_seconds`      | `30`    | Seconds between probes.                                                                                    |
| `watchdog_startup_grace_seconds` | `600`   | Sleep this long after addon start before the first probe. **Must be >= `watchdog_max_age_seconds`.**       |

> **Why `watchdog_startup_grace_seconds >= watchdog_max_age_seconds`?** If
> `grace` is smaller than `max_age`, the first probe will likely fail on a
> freshly restarted addon — the target file's `mtime` predates the restart by
> more than `grace` seconds, so it looks stale even though weewxd / rtgd are
> perfectly healthy. The threshold then trips in a few probes and the watchdog
> kills the addon for no real reason. The watchdog log calls this out at start;
> fix it by raising `grace`.

Pick a `watchdog_path` whose source you trust to rewrite regularly:
`/index.html` (regenerated every archive cycle) is a safe default;
`/gauge-data.txt` (rewritten by `realtime-gauge-data` every LOOP packet once
rtgd is enabled) is much sharper.

---

## Database

The default is **SQLite** at `/config/db/weewx.sdb` — auto-created on first
weewxd start, persists across image upgrades, no external dependency.

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

### Caching & compression

Responses are compressed on the wire (brotli when the client offers it, gzip
otherwise) and carry `Cache-Control`/`Expires` headers so a downstream caching
proxy can serve reports without re-reading every file across the network. All
tiers are `public`, and `ETag`/`Last-Modified` stay on, so anything past its
window revalidates with a cheap `304` rather than a full re-download.

Report files use `expires modified` — the window is measured from each file's
**modification time**, so a chart is cacheable exactly until WeeWX next
regenerates it, then revalidated. The default tiers:

| Path                                      | Window                                 |
| ----------------------------------------- | -------------------------------------- |
| `gauge-data.txt` (only with rtgd enabled) | `max-age=1` (rewritten every loop)     |
| HTML pages + the directory index          | `archive_interval` (from `weewx.conf`) |
| `forecast.html` (weewx-forecast skin)     | ~1 hour (`stale_age = 3570`)           |
| `day*.png` and any other `*.png`          | `archive_interval`                     |
| `week*.png`                               | 1 hour                                 |
| `month*.png`                              | 3 hours                                |
| `year*.png`                               | 24 hours                               |
| `icons/`, `*.css`, `*.js`, fonts, `*.ico` | 1 hour (flat)                          |
| `NOAA/` directory listing                 | `archive_interval` (per request)       |
| `NOAA/` current month + year              | `archive_interval` (per request)       |
| `NOAA/` past months + years               | 24 hours (immutable)                   |
| `robots.txt`                              | 24 hours (flat)                        |

These PNG windows assume day plots regenerate every archive cycle, week hourly,
month every 3 hours (matching `aggregate_interval = 10800` in
`[[month_images]]`), and year daily — the cadence of the bundled exfoliation
skin. A skin that regenerates plots on a different schedule (e.g. every archive
cycle) can serve a stale chart with a too-long window; retune via the override
below.

The `NOAA/` text reports are handled by a small njs filter (the
`ngx_http_js_module`) rather than a static rule. WeeWX rewrites only the current
month and year summaries each cycle while every older file is immutable, but
nginx can't tell them apart by name — it has no notion of "today". The filter
checks each request against the current date, so the live summaries get the
`archive_interval` window and the frozen history gets 24h, and it stays correct
across month/year rollovers with no reload.

### Tuning report caching

To override the asset/PNG tiers, drop a raw nginx snippet at
`/config/nginx-cache.conf`. It **replaces** the generated default set verbatim
(the HTML/index tier and `gauge-data.txt` are configured separately and stay as
above). It is validated with `nginx -t` on start; if it has an error the add-on
logs a warning and falls back to the generated defaults, so a typo can't keep
the add-on from starting.

The `__ARCHIVE__` token expands to `[StdArchive] archive_interval` at startup
(the same way the defaults are filled in), so a window can track your archive
interval instead of hardcoding it.

> **Restart required after editing `archive_interval`.** The value is read once
> at addon start and substituted into the generated nginx config and into the
> `/NOAA/` filter variable. Changing `archive_interval` in `weewx.conf` only
> takes effect after restarting the addon.

Start from the defaults below and adjust the windows you need:

> **Order matters.** nginx picks the first matching `location` block, so put
> specific patterns above catch-alls — e.g. the `^/day*.png`, `^/week*.png`,
> `^/month*.png`, and `^/year*.png` rules must stay above the unprefixed
> `\.png$` fallback, or the fallback shadows them and every chart gets the same
> window.

> **Advisory denylist.** A small set of directives that typically don't belong
> in cache-tier tuning trigger a startup `WARNING` in the add-on log but the
> override is loaded anyway: `proxy_pass`, `*_pass`, `return`, `rewrite`,
> `auth_basic`/`auth_request`, `deny`/`allow`, `root`/`alias`, `include`, and
> `add_header` for `X-Frame-Options` / `Content-Security-Policy` /
> `Strict-Transport-Security`. If you put one of these in deliberately, just
> ignore the warning.

```nginx
location ~ ^/forecast\.html$ {       # regex, not `location =`, so a user's
    expires modified +3570s;         # exact-match `location = /forecast.html`
    add_header Cache-Control "public" always;   # in /config/nginx-extra.conf
}                                    # can preempt this tier for a redirect
                                     # without a duplicate-block nginx -t error.
location ^~ /icons/ {
    autoindex on;                    # consistent with / and /NOAA/
    autoindex_exact_size off;
    autoindex_localtime on;
    try_files $uri $uri/ =404;
    expires 1h;
    add_header Cache-Control "public" always;
}
location ~* \.(?:js|css|woff2?|ttf|otf|eot|svg|ico)$ {
    try_files $uri =404;
    expires 1h;
    add_header Cache-Control "public" always;
}
location ~* ^/day[^/]*\.png$ {
    expires modified +__ARCHIVE__s;  # tracks archive_interval
    add_header Cache-Control "public" always;
}
location ~* ^/week[^/]*\.png$ {
    expires modified +1h;            # week_images regen hourly
    add_header Cache-Control "public" always;
}
location ~* ^/month[^/]*\.png$ {
    expires modified +3h;            # month_images aggregate_interval=10800
    add_header Cache-Control "public" always;
}
location ~* ^/year[^/]*\.png$ {
    expires modified +24h;
    add_header Cache-Control "public" always;
}
location ~* \.png$ {
    expires modified +__ARCHIVE__s;
    add_header Cache-Control "public" always;
}
```

### Adding redirects and other server-scope directives

For anything that isn't a per-tier cache rule — 301/302 redirects, an
exact-match `location =` for a specific URL, a custom `rewrite`, etc. — drop it
in `/config/nginx-extra.conf`. The addon includes this file at server scope on
startup, alongside `nginx-cache.conf`. Empty by default; validated with
`nginx -t` and reverted to empty (with a WARNING in the addon log) if a broken
snippet would keep the addon from starting.

Because `location =` (exact match) has the highest priority in nginx's request
routing, a redirect defined here fires **before** `location /`'s `try_files`
even if a file with the same name still exists on disk. That makes this the
right home for retiring old report URLs to a client-side router hash — you don't
have to delete the stale files first to prove the redirect.

Example — redirect the classic report paths to a single-page-app hash. **Note
the target is a bare relative path** (`index.html#/live`, no leading `/`). This
matters when the addon is served through HA Supervisor ingress: an absolute path
(`/#/live`) auto-expands to `http://<addon-host>:8099/#/live` using nginx's own
listen port, which strips the `/api/hassio_ingress/<token>/` prefix and points
browsers at a port they can't reach. A relative target resolves against the
current URL's base path, so the ingress prefix is preserved on ingress
deployments and the redirect still works on direct `8099` and behind reverse
proxies.

```nginx
location = /live.html      { return 301 "index.html#/live"; }
location = /forecast.html  { return 301 "index.html#/forecast"; }
location = /almanac.html   { return 301 "index.html#/almanac"; }
location = /history.html   { return 301 "index.html#/history"; }
location = /station.html   { return 301 "index.html#/station"; }
location = /links.html     { return 301 "index.html#/links"; }
```

No advisory denylist applies here — this file is explicitly for the directives
that don't belong in a cache-tier snippet, so `return`, `rewrite`,
`location = ...`, etc. are all first-class.

---

## Bundled extensions

These extensions are pre-installed at `/opt/weewx-data/bin/user/` and (where
applicable) `/opt/weewx-data/skins/`. To enable one, add its service path to the
appropriate `*_services` entry in `[Engine] [[Services]]` and add its
configuration section to `weewx.conf`.

| Extension             | Service path                                     | Service list              | Notes                                                               |
| --------------------- | ------------------------------------------------ | ------------------------- | ------------------------------------------------------------------- |
| weewx-home-assistant  | `weewx_ha.Controller`                            | `report_services`         | MQTT discovery for HA (by felddy)                                   |
| emoncms               | `user.emoncms.EmonCMS`                           | `restful_services`        | matthewwall                                                         |
| report_hook           | `user.report_hook.ReportHook`                    | _(skin `generator_list`)_ | Post-report shell hook — see below                                  |
| exfoliation           | _(skin only)_                                    | —                         | Replacement skin                                                    |
| forecast              | `user.forecast.NWSForecast` (etc.)               | `archive_services`        | Multiple forecast providers, chaunceygardiner                       |
| fuzzy-archer          | _(skin only)_                                    | —                         | Bootstrap-themed skin                                               |
| MQTTSubscribe         | `user.MQTTSubscribe.MQTTSubscribeService`        | `data_services`           | Ingest data from MQTT topics, bellrichm                             |
| opensensemap          | `user.opensensemap.OpenSenseMap`                 | `restful_services`        | sbsrouteur                                                          |
| owm                   | `user.owm.OpenWeatherMap`                        | `restful_services`        | matthewwall                                                         |
| previmeteo            | `user.previmeteo.Previmeteo`                     | `restful_services`        | Patched for Python 3                                                |
| purpleair             | `user.purpleair.PurpleAirMonitor`                | `process_services`        | bakerkj                                                             |
| rain24h               | `user.rain24h.Rain24h`                           | `data_services`           | Injects rolling 24h rain into loop packets, chaunceygardiner        |
| realtime-gauge-data   | `user.rtgd.RealtimeGaugeData`                    | `report_services`         | + RealtimeGauges skin                                               |
| refresh_stale_outputs | `user.refresh_stale_outputs.RefreshStaleOutputs` | `report_services`         | Force-refresh stale_age-gated outputs on weewxd startup — see below |
| thingspeak            | `user.thingspeak.ThingSpeak`                     | `restful_services`        | matthewwall                                                         |
| wcloud                | `user.wcloud.WeatherCloud`                       | `restful_services`        | matthewwall                                                         |
| wetter                | `user.wetter.Wetter`                             | `restful_services`        | matthewwall                                                         |
| windfinder            | `user.windfinder.WindFinder`                     | `restful_services`        | matthewwall                                                         |
| windguru              | `user.windguru.WindGuru`                         | `restful_services`        | claudobahn                                                          |
| windy                 | `user.windy.Windy`                               | `restful_services`        | matthewwall                                                         |
| xaggs                 | `user.xaggs.XAggsService`                        | `xtype_services`          | Historical-day aggregation tags for skins, tkeffer                  |

### Post-report shell hook (`report_hook`)

`user.report_hook.ReportHook` runs an arbitrary shell command when a skin's
report cycle finishes. It slots into the skin's `[Generators] generator_list`
after the generators whose output the command depends on, so WeeWX fires it
exactly when everything else for that skin has completed — no polling.

The command is an **argv list** (`subprocess.run(..., shell=False)`) — no shell,
no injection surface. Each argv element runs through `os.path.expandvars`, so
`$TOKEN` / `${TOKEN}` substitutes from the subprocess env (which is preloaded
with the process's own env plus every `env_*` entry).

Minimal config in `weewx.conf` — configobj parses a comma-separated
`command = a, b, c` line as a Python list, which is exactly the argv shape:

```ini
[StdReport]
    [[MySkin]]
        [[[ReportHook]]]
            command = curl, -fsS, -X, POST,
                      -H, "Authorization: Bearer $TOKEN",
                      https://example.com/hook
            env_TOKEN = xyz-secret

[Generators]
    generator_list = weewx.cheetahgenerator.CheetahGenerator, user.report_hook.ReportHook
```

Options (all optional except `command`; empty/missing `command` is a no-op):

| Option        | Default  | Meaning                                                                                                                              |
| ------------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| `command`     | _(none)_ | argv list. First element is the executable (looked up on `PATH`); the rest are its arguments. Empty = disabled.                      |
| `frequency`   | `every`  | `every` (each report cycle) or `once` (once per addon boot).                                                                         |
| `timeout`     | `10`     | Seconds before the command is killed.                                                                                                |
| `verify_file` | _(none)_ | Optional path — command runs only when the file exists and is non-empty.                                                             |
| `env_<NAME>`  | _(none)_ | Exports `NAME=<value>` to the subprocess env; `env_TOKEN = abc` makes `$TOKEN` available for `expandvars` substitution in `command`. |

Non-zero exit, timeout, or spawn failure is logged at WARNING and never breaks
the report cycle. `frequency = once` tracks "already fired" in a module-level
set that persists across report cycles within a single `weewxd` process;
container restart spawns a fresh interpreter and the set is empty again, so
"once per boot" is the semantic.

### Refresh stale_age-gated outputs on startup (`refresh_stale_outputs`)

`user.refresh_stale_outputs.RefreshStaleOutputs` closes a small but persistent
papercut: a Cheetah template or ImageGenerator plot with `stale_age` set is
**skipped even on the first cycle after a weewxd restart**, up to the length of
its stale window. That means an edit to (say) `views/forecast.html.tmpl` with
`stale_age = 3570` doesn't reach the served output for up to ~59 minutes after
you restart the addon.

The service binds to `weewx.STARTUP`, walks every enabled `[StdReport]` skin's
config, and `os.utime(<output>, (0, 0))` on every output whose skin entry has
`stale_age`. The next report cycle sees the file as ancient, the stale-age
branch decides it must re-render, and the atomic tmp+rename write replaces the
aged file before anyone consumes the ancient mtime.

Wire in `weewx.conf`:

```ini
[Engine]
    [[Services]]
        report_services = ..., user.refresh_stale_outputs.RefreshStaleOutputs
```

No config knobs — it always ages every stale_age-gated output for every enabled
report on every weewxd start. Failures (unreadable skin.conf, read-only
filesystem, missing output files) are logged and skipped; the report thread
continues.

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
