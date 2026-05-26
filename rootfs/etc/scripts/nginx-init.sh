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
printf 'add_header Cache-Control "public, max-age=%s" always;\n' "$archive_interval" \
  >/tmp/nginx-report-cache.conf
echo "Report cache window: max-age=${archive_interval}s (from archive_interval)"

nginx -t
