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

nginx -t
