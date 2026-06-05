// Per-request Cache-Control for WeeWX NOAA climate reports.
//
// WeeWX rewrites only the *current* month and year summaries each report cycle
// (NOAA-YYYY-MM.txt / NOAA-YYYY.txt); every older file is immutable. nginx
// cannot tell them apart by URL alone — it has no notion of "today" at config
// time — so this header filter decides per request: the current period gets a
// short window (archive_interval, passed in as an nginx variable), everything
// else a flat 24h. Because it is recomputed on every request, it stays correct
// across month/year rollovers with no reload.
//
// Local time is used to match WeeWX's NOAA file naming (the station's local
// calendar); when the container has no TZ set, local == UTC, which also matches
// WeeWX running on the same clock.
function setCache(r) {
    var interval = Number(r.variables.archive_interval) || 300;
    var m = r.uri.match(/\/NOAA-(\d{4})(?:-(\d{2}))?\.txt$/);
    if (!m) {
        // Autoindex listing (or any non-report URI under /NOAA/): the listing
        // changes when WeeWX writes a new report, which is on the archive
        // cycle. Treat it like a current-period file.
        r.headersOut["Cache-Control"] = "public, max-age=" + interval;
        return;
    }

    var now = new Date();
    var curYear = String(now.getFullYear());
    var curMonth = ("0" + (now.getMonth() + 1)).slice(-2);
    var isCurrent = m[1] === curYear && (m[2] === undefined || m[2] === curMonth);

    r.headersOut["Cache-Control"] = isCurrent
        ? "public, max-age=" + interval
        : "public, max-age=86400";
}

export default { setCache };
