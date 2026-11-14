"""Generate the multi-page static site (one index.html per page folder) from shared parts.

Pages: Home, Calendar, Alerts, Live Data, About (+ redirects from the removed information pages).
All links are relative, so the site works under /jamra/ on GitHub Pages and on localhost.
Usage: python scripts/build_pages.py
Written with the help of an SI coding assistant (Claude Code), following Team Astro Byte's design.
"""
from pathlib import Path

PUB = Path(__file__).resolve().parents[1] / "web" / "public"

EMBER = "#E8833A"


def ember_mark(cx, cy, r, ink, orbit=True, sw=2.2):
    """The ember: a solid calm-orange circle, crossed by one thin dark orbit arc (flat, no glow)."""
    if not orbit:
        return f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{EMBER}"/>'
    rx, ry = r * 1.7, r * 0.5
    # back half of the orbit (behind the ember), the ember, then the front half
    back = f'<path d="M{cx - rx:.2f} {cy:.2f}A{rx:.2f} {ry:.2f} 0 0 1 {cx + rx:.2f} {cy:.2f}" fill="none" stroke="{ink}" stroke-width="{sw}" stroke-linecap="round" transform="rotate(-18 {cx} {cy})"/>'
    front = f'<path d="M{cx + rx:.2f} {cy:.2f}A{rx:.2f} {ry:.2f} 0 0 1 {cx - rx:.2f} {cy:.2f}" fill="none" stroke="{ink}" stroke-width="{sw}" stroke-linecap="round" transform="rotate(-18 {cx} {cy})"/>'
    return back + f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{EMBER}"/>' + front


# Inter SemiBold metrics (measured, in em): x-height 0.547, dot of the "j" centred 0.131 right of the
# origin and 0.693 above the baseline, j advance 0.262, word "jamra" 2.698.
def logo(ink="#111827", height=30, font_face=""):
    """The wordmark IS the logo: lowercase "jamra" in Inter SemiBold; the dot of the j is the ember."""
    B, X0 = 82, 6                      # baseline and left margin, in units where font-size = 100
    W, H = 278, 108
    jx = X0
    ax = X0 + 26.17 - 1.0              # "amra" right after the j (tight tracking)
    clip_y = B - 58.5                  # hide the font's own j dot (everything above 0.585 em)
    cid = "jc" + ink.strip("#")
    return (f'<svg class="wordmark" viewBox="0 0 {W} {H}" height="{height}" width="{round(height * W / H)}" role="img" aria-label="jamra">'
            f'{font_face}<defs><clipPath id="{cid}"><rect x="0" y="{clip_y}" width="40" height="{H}"/></clipPath></defs>'
            f'<g font-family="Inter, system-ui, sans-serif" font-weight="600" font-size="100" fill="{ink}">'
            f'<text x="{jx}" y="{B}" clip-path="url(#{cid})">j</text>'
            f'<text x="{ax}" y="{B}" letter-spacing="-1.6">amra</text></g>'
            f'{ember_mark(jx + 13.05, B - 69.3, 8.2, ink, sw=1.5)}</svg>')


def j_icon(size=512, bg="#FFFFFF", ink="#111827", radius=0.22, pad=0.16, font_face="", bold=0.0):
    """App icon: just the j with the ember dot, centred on a white rounded square."""
    fs = 100
    # ink box of j + ember (em): x from -0.03 to 0.22, y from 0.78 above to 0.21 below the baseline
    ink_w, ink_h = 0.25 * fs, 0.99 * fs
    S = 100
    scale = (S * (1 - 2 * pad)) / ink_h
    tx = S / 2 - (0.095 * fs) * scale
    ty = S / 2 + (0.285 * fs) * scale
    rr = S * radius
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {S} {S}" width="{size}" height="{size}">{font_face}'
            + (f'<rect width="{S}" height="{S}" rx="{rr}" fill="{bg}"/>' if bg else '')
            + f'<defs><clipPath id="ic"><rect x="-20" y="-58.5" width="60" height="100"/></clipPath></defs>'
            f'<g transform="translate({tx:.2f} {ty:.2f}) scale({scale:.4f})">'
            f'<text x="0" y="0" font-family="Inter, sans-serif" font-weight="700" font-size="{fs}" fill="{ink}" clip-path="url(#ic)"'
            + (f' stroke="{ink}" stroke-width="{bold}" stroke-linejoin="round"' if bold else '') + '>j</text>'
            f'<circle cx="13.55" cy="-69.3" r="{10.5 + bold / 2}" fill="{EMBER}"/></g></svg>')


# Lucide icons (ISC licence), inline so no icon font is needed
ICON = {
    "calendar": '<rect width="18" height="18" x="3" y="4" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/>',
    "bell": '<path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/>',
    "radio": '<path d="M4.9 19.1C1 15.2 1 8.8 4.9 4.9"/><path d="M7.8 16.2c-2.3-2.3-2.3-6.1 0-8.5"/><circle cx="12" cy="12" r="2"/><path d="M16.2 7.8c2.3 2.3 2.3 6.1 0 8.5"/><path d="M19.1 4.9C23 8.8 23 15.1 19.1 19"/>',
    "check": '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><path d="m9 11 3 3L22 4"/>',
    "arrow": '<path d="M5 12h14"/><path d="m12 5 7 7-7 7"/>',
}


def icon(name, cls="icon"):
    return f'<svg class="{cls}" viewBox="0 0 24 24" aria-hidden="true">{ICON[name]}</svg>'


TITLES = {
    "calendar": "Calendar",
    "alerts": "Alerts",
    "live": "Live Data",
    "about": "About",
}

PAGES = [  # slug, nav label, <title>
    ("", "Home", "jamra · 20 years of NASA fire data, one fair calendar"),
    ("calendar", "Calendar", "Calendar · jamra"),
    ("alerts", "Alerts", "Alerts · jamra"),
    ("live", "Live Data", "Live Data · jamra"),
    ("about", "About", "About · jamra"),
]
# removed information pages: their content is in the Arabic user guide; old links land on About
OLD_PAGES = {"how-it-works": "about/", "validation": "about/", "limits": "about/", "credits": "about/"}

import json as _json
_META = _json.loads((PUB / "data" / "meta.json").read_text(encoding="utf-8"))
CHIPS = {k: "".join(f'<button type="button" class="chip" data-area="{a['id']}" aria-pressed="false">{a['label']}</button>' for a in _META["areas"] if a["kind"] == k) for k in ("preset", "country")}
TEAM = [("Shahd Farraj", "Problem and users", "Slides 1–2"), ("Ahmed Etkaidek", "NASA data and live system", "Slide 3"),
        ("Aya Salman", "Science: method and validation", "Slides 4 and 6"), ("Ahmad Akhras", "Calendar and live demo", "Slide 5"),
        ("Tala Yousef", "UX, design and communication", "Slide 7")]
TEAM_HTML = "".join(f'<div class="member"><b>{n}</b><span>{r}</span><p class="fine">{d}</p></div>' for n, r, d in TEAM)

AREA_PICKER = """
  <section id="area">
    <div class="wrap grid-2">
      <div>
        <div class="tabs" role="tablist" aria-label="Choose an area">
          <button role="tab" id="tab-preset" aria-controls="pane-preset" aria-selected="true" class="tab">Fire areas</button>
          <button role="tab" id="tab-country" aria-controls="pane-country" aria-selected="false" class="tab" tabindex="-1">Countries</button>
          <button role="tab" id="tab-draw" aria-controls="pane-draw" aria-selected="false" class="tab" tabindex="-1">Draw</button>
          <button role="tab" id="tab-coords" aria-controls="pane-coords" aria-selected="false" class="tab" tabindex="-1">Lat / Lon</button>
        </div>
        <div id="pane-preset" role="tabpanel" aria-labelledby="tab-preset" class="pane"><div id="preset-list" class="chips">""" + CHIPS["preset"] + """</div></div>
        <div id="pane-country" role="tabpanel" aria-labelledby="tab-country" class="pane" hidden><div id="country-list" class="chips">""" + CHIPS["country"] + """</div></div>
        <div id="pane-draw" role="tabpanel" aria-labelledby="tab-draw" class="pane" hidden>
          <div class="row">
            <button type="button" class="btn" id="draw-polygon">Draw polygon</button>
            <button type="button" class="btn" id="draw-circle">Draw circle</button>
            <button type="button" class="btn ghost" id="draw-clear">Clear</button>
          </div>
        </div>
        <div id="pane-coords" role="tabpanel" aria-labelledby="tab-coords" class="pane" hidden>
          <form id="coords-form" class="form">
            <fieldset><legend>Point and radius</legend>
              <label>Latitude <input name="lat" type="number" step="any" min="-90" max="90" placeholder="38.60" inputmode="decimal"></label>
              <label>Longitude <input name="lon" type="number" step="any" min="-180" max="180" placeholder="23.60" inputmode="decimal"></label>
              <label>Radius (km) <input name="r" type="number" step="1" min="1" max="300" value="25" inputmode="numeric"></label>
            </fieldset>
            <p class="or">or a box</p>
            <fieldset><legend>Bounding box</legend>
              <label>West <input name="w" type="number" step="any" placeholder="22.8"></label>
              <label>South <input name="s" type="number" step="any" placeholder="37.9"></label>
              <label>East <input name="e" type="number" step="any" placeholder="24.6"></label>
              <label>North <input name="n" type="number" step="any" placeholder="39.0"></label>
            </fieldset>
            <button class="btn primary" type="submit">Use this area</button>
            <p id="coords-msg" class="msg" role="status"></p>
          </form>
        </div>
        <div id="area-info" class="area-info" aria-live="polite"><b>Loading the area…</b><br><span>Fire area, country or your own shape</span><br><span>1 MODIS hotspot ≈ … VIIRS hotspots · ±…% on a month</span></div>
      </div>
      <div>
        <div class="map-wrap card">
          <div id="map" class="map" role="region" aria-label="Map of the selected area and recent hotspots"><div class="map-loader" id="map-loader"></div></div>
          <div class="map-tools">
            <span>Recent hotspots</span>
            <div class="seg small" role="group" aria-label="Recent hotspot period">
              <button type="button" class="seg-btn" data-livewin="1" aria-pressed="true">24 h</button>
              <button type="button" class="seg-btn" data-livewin="7" aria-pressed="false">7 days</button>
              <button type="button" class="seg-btn" data-livewin="0" aria-pressed="false">Off</button>
            </div>
          </div>
          <p class="map-note">Imagery: NASA GIBS / Blue Marble · Map © OpenStreetMap contributors (OpenFreeMap) · Hotspots: NASA FIRMS</p>
        </div>
      </div>
    </div>
  </section>"""

EVIA = "calendar/?area=evia&amp;from=2003&amp;to=2025&amp;month=2007-08&amp;mode=abs&amp;detail=1"

BODY = {
"": """
  <section class="hero" id="hero">
    <div class="globe-wrap" id="globe-wrap">
      <img class="globe-still" id="globe-still" src="img/earth-blue-marble.webp" width="720" height="720" alt="Earth from space, centred on the Mediterranean (NASA Blue Marble imagery)" fetchpriority="low">
      <canvas id="globe" role="img" aria-label="Globe with recent fire hotspots from NASA FIRMS. Drag to turn it."></canvas>
    </div>
    <div class="wrap hero-in">
      <h1>20 years of NASA fire data. One fair calendar.</h1>
      <div class="cta-row">
        <a class="btn primary big" data-nav href="calendar/">Open the Calendar</a>
        <a class="btn big" id="evia-btn" href=\"""" + EVIA + """\">Try Evia 2007</a>
      </div>
      <p class="live-chip" id="live-chip"><span class="dot" aria-hidden="true"></span><span class="txt">Loading live data · Data: NASA FIRMS</span></p>
    </div>
    <p class="img-credit">Earth: NASA GIBS / Blue Marble · Stars: Yale Bright Star Catalogue (NASA HEASARC)</p>
  </section>

  <section id="tools">
    <div class="wrap tools">
      <a class="tool" data-nav href="calendar/"><span class="ic">""" + icon("calendar") + """</span><b>Calendar</b><span>Fire history, month by month</span><span class="go">Open """ + icon("arrow") + """</span></a>
      <a class="tool" data-nav href="alerts/"><span class="ic">""" + icon("bell") + """</span><b>Alerts</b><span>Is this month unusual?</span><span class="go">Open """ + icon("arrow") + """</span></a>
      <a class="tool" data-nav href="live/"><span class="ic">""" + icon("radio") + """</span><b>Live Data</b><span>Newest detections, as CSV</span><span class="go">Open """ + icon("arrow") + """</span></a>
    </div>
  </section>""",

"calendar": AREA_PICKER + """
  <section id="yearly" class="band">
    <div class="wrap">
      <div class="card">
        <div class="chart-head">
          <h2 id="hero-title">Yearly hotspots</h2>
          <div class="seg" role="group" aria-label="Record type">
            <button type="button" class="seg-btn" data-hero="raw" aria-pressed="true">Raw</button>
            <button type="button" class="seg-btn" data-hero="harm" aria-pressed="false">Harmonized</button>
          </div>
        </div>
        <div id="hero-chart" class="chart" role="img" aria-label="Yearly hotspot chart"></div>
        <p id="hero-caption" class="caption"></p>
      </div>
    </div>
  </section>
  <section id="kpis">
    <div class="wrap">
      <div class="range-row">
        <h2 id="area-title">Selected area</h2>
        <div class="range">
          <label>From <select id="from-year"></select></label>
          <label>To <select id="to-year"></select></label>
          <label class="check"><input type="checkbox" id="static-filter" checked> Hide gas flares / industry</label>
        </div>
      </div>
      <div class="kpi-grid" id="kpi-grid"><div class="kpi"></div><div class="kpi"></div><div class="kpi"></div><div class="kpi"></div><div class="kpi"></div></div>
    </div>
  </section>
  <section id="calendar" class="band">
    <div class="wrap">
      <div class="cal-head">
        <h2>Burning activity calendar</h2>
        <div class="cal-controls">
          <div class="seg" role="group" aria-label="Calendar mode">
            <button type="button" class="seg-btn" data-mode="abs" aria-pressed="true">Hotspots</button>
            <button type="button" class="seg-btn" data-mode="anomaly" aria-pressed="false">Compared with usual</button>
          </div>
          <div class="seg" role="group" aria-label="Time resolution">
            <button type="button" class="seg-btn" data-res="month" aria-pressed="true">Months</button>
            <button type="button" class="seg-btn" data-res="week" aria-pressed="false">Weeks</button>
          </div>
          <label class="pal">Colours <select id="palette">
            <option value="viridis">Viridis</option><option value="cividis">Cividis</option><option value="ylorrd">YlOrRd</option>
          </select></label>
        </div>
      </div>
      <div class="card cal-card">
        <div id="cal-legend" class="legend"></div>
        <div id="cal" class="cal" role="grid" aria-label="Burning activity calendar: rows are years, columns are months"></div>
        <div class="cal-foot">
          <span><span class="key hatch-key"></span>estimated from MODIS (<span data-unc-label>±</span>)</span>
          <span><span class="key solid-key"></span>observed · VIIRS</span>
          <span><span class="key j-key"></span>NOAA-20, converted</span>
          <span><span class="key gap-key"></span>data gap</span>
          <span class="dl">
            <button type="button" class="btn ghost small" id="dl-cal-csv">CSV</button>
            <button type="button" class="btn ghost small" id="dl-cal-png">PNG</button>
            <button type="button" class="btn ghost small" id="dl-summary-png">Summary PNG</button>
            <button type="button" class="btn ghost small" id="dl-summary-pdf">Summary PDF</button>
          </span>
        </div>
      </div>
      <div id="detail" class="card detail" hidden tabindex="-1" aria-live="polite"></div>
      <div class="card season" id="season"></div>
    </div>
  </section>""",

"alerts": """
  <section id="alerts">
    <div class="wrap">
      <div id="data-status" class="status-panel" aria-live="polite"><div class="st"><b>Checking live data</b> · reading the newest NASA FIRMS update and its time (UTC) · one moment</div></div>
      <div id="alert-list" class="alert-list"></div>
      <p class="fine" id="scale-note">Live: VIIRS NOAA-20 × <span data-k-jn>0.97</span> (S-NPP scale) · vs the same days in past years · Data: NASA FIRMS</p>
      <p class="feeds">Feeds: <a href="../data/live/alerts.json">alerts.json</a> · <a href="../data/live/alerts.xml">RSS</a> · <a href="../data/live/status.json">status.json</a></p>
      <p class="fine"><b>Not an emergency service.</b> Satellite data arrive hours late. In an emergency call your local number (112 in the EU and Türkiye).</p>
    </div>
  </section>""",

"live": AREA_PICKER + """
  <section id="live" class="band">
    <div class="wrap">
      <form id="live-form" class="row live-row">
        <label>Last <select name="days">
          <option value="1">24 hours</option><option value="2">2 days</option><option value="3">3 days</option>
          <option value="5">5 days</option><option value="7" selected>7 days</option></select></label>
        <button class="btn primary" type="submit">Get data from NASA FIRMS</button>
        <button class="btn" type="button" id="dl-live-csv" disabled>Download CSV</button>
      </form>
      <p id="live-stamp" class="msg" role="status">VIIRS NOAA-20 near real time · raw detections</p>
      <div class="table-wrap card"><table id="live-table" class="table"><caption class="sr">Live hotspots</caption><thead></thead><tbody></tbody></table></div>
    </div>
  </section>""",

"about": """
  <section id="about">
    <div class="wrap about">
      <h2>Team Astro Byte</h2>
      <div class="team" id="team-grid">""" + TEAM_HTML + """</div>
      <p class="fine">NASA Space Apps Challenge 2026 · local event by NOVA · Challenge: Harmonization of MODIS and VIIRS Hot Spots.</p>

      <h2>Data acknowledgment</h2>
      <p class="ack">We acknowledge the use of data and/or imagery from NASA's Fire Information for Resource Management System (FIRMS) (<a href="https://earthdata.nasa.gov/firms">https://earthdata.nasa.gov/firms</a>), part of NASA's Land, Atmosphere Near real-time Capability for Earth observations (LANCE) (<a href="https://earthdata.nasa.gov/lance">https://earthdata.nasa.gov/lance</a>) and NASA's Earth Science Data and Information System (ESDIS).</p>
      <ul>
        <li>MODIS Collection 6.1 active fire (Terra, Aqua) and VIIRS 375 m active fire (S-NPP, NOAA-20), standard processing: FIRMS yearly files and FIRMS API.</li>
        <li>VIIRS NOAA-20 near real time: FIRMS API, every 3 hours.</li>
      </ul>

      <h2>Imagery and map credits</h2>
      <ul>
        <li>Earth imagery: NASA GIBS / Blue Marble (shaded relief and bathymetry).</li>
        <li>Star sky: Yale Bright Star Catalogue, 5th edition (Hoffleit &amp; Warren 1991), via NASA HEASARC.</li>
        <li>Detail map: © OpenStreetMap contributors (ODbL) · OpenMapTiles · OpenFreeMap.</li>
        <li>Software: MapLibre GL JS (BSD-3-Clause), three.js (MIT), Inter typeface (SIL OFL). Colour ramps: Viridis and Cividis (matplotlib, CC0), YlOrRd (ColorBrewer, Apache-2.0).</li>
      </ul>

      <h2>References</h2>
      <ul class="refs">
        <li>Giglio, L., Schroeder, W., &amp; Justice, C. O. (2016). The collection 6 MODIS active fire detection algorithm and fire products. <em>Remote Sensing of Environment</em>, 178, 31–41.</li>
        <li>Schroeder, W., Oliva, P., Giglio, L., &amp; Csiszar, I. A. (2014). The New VIIRS 375 m active fire detection data product: Algorithm description and initial assessment. <em>Remote Sensing of Environment</em>, 143, 85–96.</li>
        <li>Davies, D. K., Ilavajhala, S., Wong, M. M., &amp; Justice, C. O. (2009). Fire Information for Resource Management System: Archiving and distributing MODIS active fire data. <em>IEEE Transactions on Geoscience and Remote Sensing</em>, 47(1), 72–79.</li>
        <li>NASA Earthdata (2026). Transitioning from Suomi NPP VIIRS &amp; OMPS: What FIRMS Users Need to Know.</li>
        <li>Hoffleit, D., &amp; Warren, W. H. (1991). The Bright Star Catalogue, 5th Revised Ed. NASA HEASARC.</li>
      </ul>

      <h2>Use of Super Intelligence (SI)</h2>
      <p>We used an SI coding assistant (Claude Code by Anthropic) to write the code for the data pipeline, website, live system and slides, following our design and decisions. The team chose the method, checked results against NASA FIRMS data, verified every reference, and wrote and rehearsed the pitch.</p>

      <h2>Notices</h2>
      <ul class="notice-list">
        <li>Built for the NASA Space Apps Challenge 2026.</li>
        <li>Not an official NASA product. NASA does not endorse this project. No NASA logos are used.</li>
        <li>Not an emergency service. Satellite data arrive hours late; in an emergency call your local emergency number.</li>
        <li>Method, validation and limits: see our user guide. Open source (MIT): <a id="repo-link" href="https://github.com/ahmedetk/jamra">github.com/ahmedetk/jamra</a></li>
      </ul>
    </div>
  </section>""",
}

REDIRECT = """<script>
// Old links (one-page #hashes, removed pages) open the right page and keep their parameters.
(function () {
  var map = { calendar: 'calendar/', kpis: 'calendar/', area: 'calendar/', problem: 'calendar/', alerts: 'alerts/', live: 'live/',
    how: 'about/', validation: 'about/', limits: 'about/', credits: 'about/', team: 'about/', works: 'about/' };
  var h = (location.hash || '').slice(1), q = location.search;
  if (map[h]) { location.replace(map[h] + q); return; }
  if (/[?&](month|mode|res|poly|pal|hero)=/.test(q)) location.replace('calendar/' + q);
})();
</script>"""

HOME_PRELOAD = ('<link rel="preload" as="image" href="img/space-stars-1280.webp" media="(max-width: 1299px)">'
                '<link rel="preload" as="image" href="img/space-stars.webp" media="(min-width: 1300px)">')

MENU_ICON = '<svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M4 7h16M4 12h16M4 17h16"/></svg>'


def page(slug, label, title):
    R = "" if slug == "" else "../"
    nav = "\n".join(
        f'      <a href="{R}{s + "/" if s else ""}" data-nav{" class=\"about\"" if s == "about" else ""}{" aria-current=\"page\"" if s == slug else ""}>{lab}</a>'
        for s, lab, _ in PAGES)
    body = BODY[slug]
    for p in ("calendar/", "alerts/", "live/", "about/"):
        body = body.replace(f'href="{p}', f'href="{R}{p}')
    head = f'<div class="page-head"><div class="wrap"><h1>{TITLES[slug]}</h1></div></div>\n' if slug in TITLES else ""
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="jamra harmonizes 20+ years of NASA MODIS and VIIRS active-fire hotspots into one fair burning activity calendar, with live early warning from NASA FIRMS.">
<meta name="theme-color" content="#FFFFFF">
<meta property="og:title" content="jamra · 20 years of NASA fire data, one fair calendar">
<meta property="og:description" content="NASA MODIS and VIIRS fire data in one fair calendar, with live early warning. Data: NASA FIRMS.">
<meta property="og:image" content="https://ahmedetk.github.io/jamra/icons/og-image.png">
<meta name="twitter:card" content="summary_large_image">
<link rel="preload" href="{R}fonts/inter-latin-600-normal.woff2" as="font" type="font/woff2" crossorigin>
{HOME_PRELOAD if slug == "" else ""}
{REDIRECT if slug == "" else ""}
<link rel="manifest" href="{R}manifest.webmanifest">
<link rel="icon" href="{R}icons/favicon-32.png" sizes="32x32" type="image/png">
<link rel="icon" href="{R}icons/favicon-16.png" sizes="16x16" type="image/png">
<link rel="apple-touch-icon" href="{R}icons/apple-touch-icon.png">
<link rel="stylesheet" href="{R}css/app.css">
<!-- Generated by scripts/build_pages.py. Code written with the help of an SI coding assistant (Claude Code by Anthropic). -->
</head>
<body data-page="{slug or 'home'}">
<a class="skip" href="#main">Skip to content</a>
<header class="top">
  <div class="wrap top-in">
    <a class="brand" href="{R}" data-nav aria-label="jamra home">{logo(height=32)}</a>
    <nav aria-label="Main" class="nav" id="site-nav">
{nav}
    </nav>
    <a id="status-badge" class="badge" href="{R}alerts/" data-nav aria-live="polite" title="Live connection to NASA FIRMS">
      <span class="dot"></span><span class="txt">Checking live data…</span>
    </a>
    <button id="menu-btn" class="menu-btn" type="button" aria-expanded="false" aria-controls="site-nav" aria-label="Menu">{MENU_ICON}</button>
  </div>
</header>
<main id="main">
{head}{body}
</main>
<div id="tooltip" class="tooltip" role="tooltip" hidden></div>
<div id="term-pop" class="term-pop" role="dialog" aria-modal="false" hidden></div>
<footer class="foot">
  <div class="wrap foot-in">
    <div>
      <a class="brand" href="{R}" data-nav aria-label="jamra home">{logo(height=26)}</a>
      <p>Team Astro Byte · Built for the NASA Space Apps Challenge 2026</p>
      <p>Not an official NASA product · Not an emergency service · <b>Data: NASA FIRMS</b></p>
    </div>
    <ul>
      <li><a href="{R}calendar/" data-nav>Calendar</a></li><li><a href="{R}alerts/" data-nav>Alerts</a></li><li><a href="{R}live/" data-nav>Live Data</a></li>
      <li><a href="{R}about/" data-nav>About</a></li><li><a href="https://github.com/ahmedetk/jamra">GitHub</a></li>
    </ul>
  </div>
</footer>
<script type="module" src="{R}js/app.js"></script>
</body>
</html>
"""


def stub(target):
    """A removed page: send visitors (and old shared links, with their parameters) to the new page."""
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Moved · jamra</title>
<meta name="robots" content="noindex">
<script>location.replace('../{target}' + location.search + location.hash);</script>
<meta http-equiv="refresh" content="0; url=../{target}">
<link rel="canonical" href="../{target}">
</head><body><p>This page moved: <a href="../{target}">open it here</a>.</p></body></html>
"""


def main():
    for slug, label, title in PAGES:
        d = PUB / slug if slug else PUB
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text(page(slug, label, title), encoding="utf-8")
        print("wrote", (d / "index.html").relative_to(PUB))
    for old, target in OLD_PAGES.items():
        d = PUB / old
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text(stub(target), encoding="utf-8")
        print("redirect", old, "->", target)


if __name__ == "__main__":
    main()
