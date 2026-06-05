// Per-request Cache-Control for WeeWX NOAA climate reports.
//
// WeeWX rewrites only the *current* month and year summaries each report cycle
// (NOAA-YYYY-MM.txt / NOAA-YYYY.txt); every older file is immutable. nginx
// cannot tell them apart by URL alone — it has no notion of "today" at config
// time — so this header filter decides per request: a recently-modified file
// gets a short window (archive_interval, passed in as an nginx variable),
// everything else a flat 24h. Because it is recomputed on every request, it
// stays correct across month/year rollovers with no reload.
//
// Freshness is decided from the file's mtime, not from a calendar comparison
// against new Date(). new Date() ran in the container's TZ (unset -> UTC); the
// NOAA filename's year/month is in the station's local TZ (WeeWX writes them
// from a local calendar). At month/year boundaries that disagreement opened a
// multi-hour window where a freshly-written file (e.g. NOAA-2026-01.txt at
// local Jan 1) would be tagged immutable until UTC caught up. Comparing mtime
// to now in seconds is timezone-free.
//
// Source of the mtime: the static module sets Last-Modified directly on the
// response structure, *not* via r.headersOut, so it isn't visible here at the
// header_filter phase. ETag, however, is — nginx's default ETag is
// "<mtime-hex>-<size-hex>" (ngx_http_set_etag in src/http/ngx_http_core_module.c),
// so we parse mtime out of the leading hex group. If ETag is absent or shaped
// differently (a user-set ETag, etag off, or a future nginx change), we fall
// back to the short window — wasteful for an immutable file (re-revalidates
// every archive cycle) but correct; the inverse, serving a stale current-period
// file for 24h, is the bug we're fixing.
function setCache(r) {
    var interval = Number(r.variables.archive_interval) || 300;
    var m = r.uri.match(/\/NOAA-(\d{4})(?:-(\d{2}))?\.txt$/);
    if (!m) {
        // Autoindex listing (or any non-report URI under /NOAA/): no per-file
        // mtime to key off, and the listing changes when WeeWX writes a new
        // report (on the archive cycle). Treat as current-period.
        r.headersOut["Cache-Control"] = "public, max-age=" + interval;
        return;
    }

    var isFresh = true;
    var etag = r.headersOut["ETag"];
    if (etag) {
        // strip optional W/ weak prefix and surrounding quotes, then take the
        // hex group before the first '-' as mtime seconds-since-epoch
        var em = etag.replace(/^W\//, "").match(/^"?([0-9a-fA-F]+)-/);
        if (em) {
            var mtimeSec = parseInt(em[1], 16);
            var nowSec = Date.now() / 1000;
            // Two archive_intervals of slack: WeeWX writes the file at the
            // start of a cycle, so by the time a client asks ~one interval may
            // already have elapsed; doubling keeps a just-regenerated
            // current-period file inside the "fresh" window without flapping.
            // An immutable history file's mtime is months/years old -> trivially
            // outside.
            isFresh = !isNaN(mtimeSec) && (nowSec - mtimeSec) < 2 * interval;
        }
    }

    r.headersOut["Cache-Control"] = isFresh
        ? "public, max-age=" + interval
        : "public, max-age=86400";
}

export default { setCache };
