#!/command/with-contenv bash
# shellcheck shell=bash
set -euo pipefail

mkdir -p /config/www /tmp/client_body /tmp/proxy /tmp/fastcgi /tmp/uwsgi /tmp/scgi

# Seed a placeholder index.html on first start so the ingress panel is not
# blank. Skip if the user has already put their own index.* there.
if ! ls /config/www/index.* >/dev/null 2>&1; then
  cat >/config/www/index.html <<'HTML'
<!doctype html>
<title>WeeWX add-on web root</title>
<h1>This is /config/www/</h1>
<p>Drop static files here (HTML, CSS, JS, images) and they will be served
through the Home Assistant ingress panel.</p>
<p>To surface the WeeWX-generated reports here, set <code>web_root</code> in
the add-on options to <code>/config/www</code> (or edit <code>HTML_ROOT</code>
in <code>weewx.conf</code> after first-seed).</p>
HTML
fi

# Derive the HTML/chart cache window from the user's [StdArchive] archive_interval
# so a downstream caching proxy can serve reports between regenerations without a
# round-trip. Use the venv python (it has configobj; /usr/bin/python3 does not).
# Fall back to 300s if weewx.conf is absent or the key is missing/invalid.
archive_interval="$(
  /opt/weewx/bin/python3 - <<'PY' 2>/dev/null
import configobj
print(int(configobj.ConfigObj("/config/weewx.conf")["StdArchive"]["archive_interval"]))
PY
)" || true
[[ "${archive_interval:-}" =~ ^[1-9][0-9]*$ ]] || archive_interval=300

# location-/ tier: HTML pages + the autoindex root. expire relative to each
# file's mtime so a report is cacheable until its next regeneration.
cat >/tmp/nginx-report-cache.conf <<EOF
expires modified +${archive_interval}s;
add_header Cache-Control "public" always;
EOF

# Per-period default tiers for static assets and chart PNGs. Static assets
# (libraries/fonts/weather icons) change only on a skin update -> flat 1h. Chart
# PNGs expire relative to mtime, keyed to how often WeeWX regenerates each
# period: day plots every archive cycle, week/month hourly, year daily; an
# unprefixed-PNG fallback is treated like a day plot. expires emits only
# max-age, so a second add_header supplies "public" (caches merge the two).
gen_default_cache() {
  cat >/tmp/nginx-cache.conf <<'EOF'
location ^~ /icons/ {
    try_files $uri =404;
    expires 1h;
    add_header Cache-Control "public" always;
}
location ~* \.(?:js|css|woff2?|ttf|otf|eot|svg|ico)$ {
    try_files $uri =404;
    expires 1h;
    add_header Cache-Control "public" always;
}
location ~* ^/day[^/]*\.png$ {
    expires modified +__ARCHIVE__s;
    add_header Cache-Control "public" always;
}
location ~* ^/(?:week|month)[^/]*\.png$ {
    expires modified +3600s;
    add_header Cache-Control "public" always;
}
location ~* ^/year[^/]*\.png$ {
    expires modified +86400s;
    add_header Cache-Control "public" always;
}
location ~* \.png$ {
    expires modified +__ARCHIVE__s;
    add_header Cache-Control "public" always;
}
EOF
  sed -i "s/__ARCHIVE__/${archive_interval}/g" /tmp/nginx-cache.conf
}

# A user can replace the whole asset/PNG tier set by dropping their own raw
# nginx snippet at /config/nginx-cache.conf. The __ARCHIVE__ token is expanded
# to archive_interval (same as the defaults) so an override can track it instead
# of hardcoding a value; everything else is used as-is. Never let a typo brick
# the add-on: if nginx -t rejects the full config, fall back to the generated
# defaults and warn.
override=/config/nginx-cache.conf
if [[ -f "$override" ]]; then
  sed "s/__ARCHIVE__/${archive_interval}/g" "$override" >/tmp/nginx-cache.conf
  echo "Cache tiers: using override ${override} (archive_interval=${archive_interval}s)"
  if ! nginx -t; then
    echo "WARNING: ${override} failed validation; reverting to generated defaults." >&2
    gen_default_cache
  fi
else
  gen_default_cache
  echo "Cache tiers: generated per-period defaults (archive_interval=${archive_interval}s)"
fi

nginx -t
