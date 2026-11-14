"""Generate the multi-page static site (one index.html per page folder) from shared parts.

Pages: Home, Calendar, Alerts, Live Data, How It Works, Validation, Limits, Credits.
All links are relative, so the site works under /jamra/ on GitHub Pages and on localhost.
Usage: python scripts/build_pages.py
Written with the help of an SI coding assistant (Claude Code), following Team Astro Byte's design.
"""
from pathlib import Path

PUB = Path(__file__).resolve().parents[1] / "web" / "public"

def logo(ring="#FFFFFF", size=34):
    """Flat Jamra mark: an ember flame with one orbit ring."""
    return (f'<svg viewBox="0 0 48 48" width="{size}" height="{size}" aria-hidden="true">'
            f'<ellipse cx="24" cy="28" rx="21" ry="8.5" transform="rotate(-20 24 28)" fill="none" stroke="{ring}" stroke-width="2.6" opacity=".9"/>'
            '<path d="M24 5c2.6 6.6 10.5 10.6 10.5 20.4A10.5 10.5 0 0 1 13.5 25.4c0-5.6 2.8-8.6 4.7-11.4 1 3.6 2.6 5.4 4.8 5.6-1.6-5.6 0-10.6 1-14.6z" fill="#F28C4B"/>'
            '<path d="M24 20.5c1.4 3 4.8 4.7 4.8 8.6a4.8 4.8 0 0 1-9.6 0c0-2.2 1.2-3.6 2-4.6.5 1.4 1.2 2.2 2 2.2-.6-2.4.2-4.4.8-6.2z" fill="#FDE6D6"/>'
            '</svg>')


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


PURPOSE = {
    "calendar": ("Burning Activity Calendar", "Fire activity for any area, month by month from 2003 to today, compared with its usual."),
    "alerts": ("Alerts", "Is this month unusual here? Checked every 3 hours against the same days in past years."),
    "live": ("Live Data", "The newest satellite fire detections from NASA FIRMS for any area, ready to download."),
    "how-it-works": ("How It Works", "How we put 20+ years of MODIS and VIIRS hotspots on one fair scale."),
    "validation": ("Validation", "How well it works, tested on years the model never saw."),
    "limits": ("Limits", "What the data can and cannot tell you, and how sure each number is."),
    "credits": ("Credits", "Data sources, references, our use of Super Intelligence (SI), and the team."),
}

GLOBE_FALLBACK = """<svg viewBox="0 0 400 400" role="img" aria-label="Globe illustration">
  <defs><radialGradient id="gsea" cx="38%" cy="32%" r="75%"><stop offset="0" stop-color="#4F86F0"/><stop offset=".7" stop-color="#2B5FDB"/><stop offset="1" stop-color="#173C9E"/></radialGradient></defs>
  <circle cx="200" cy="200" r="170" fill="url(#gsea)"/>
  <g fill="none" stroke="#9DBBF5" stroke-opacity=".35" stroke-width="1.2">
    <ellipse cx="200" cy="200" rx="170" ry="60"/><ellipse cx="200" cy="200" rx="170" ry="120"/><ellipse cx="200" cy="200" rx="60" ry="170"/><ellipse cx="200" cy="200" rx="120" ry="170"/><path d="M30 200h340M200 30v340"/>
  </g>
  <path d="M118 128c22-14 58-18 82-8 18 8 40 4 56 14 12 8 6 22-8 26-18 6-26 20-46 22-22 2-30-12-50-10-18 2-40-4-46-18-4-10 2-20 12-26z" fill="#CFE0FA" opacity=".85"/>
  <path d="M182 196c14-6 34 0 40 14 6 16-4 40-16 58-8 12-22 10-26-4-4-18-14-26-12-44 1-12 4-20 14-24z" fill="#CFE0FA" opacity=".85"/>
  <g fill="#FF6A2B"><circle cx="160" cy="152" r="3.5"/><circle cx="214" cy="146" r="3.5"/><circle cx="236" cy="158" r="3"/><circle cx="140" cy="140" r="3"/><circle cx="196" cy="160" r="2.5"/></g>
</svg>"""

PAGES = [  # slug, nav label, title
    ("", "Home", "Jamra · Burning Activity Calendar"),
    ("calendar", "Calendar", "Calendar · Jamra"),
    ("alerts", "Alerts", "Alerts · Jamra"),
    ("live", "Live Data", "Live Data · Jamra"),
    ("how-it-works", "How It Works", "How It Works · Jamra"),
    ("validation", "Validation", "Validation · Jamra"),
    ("limits", "Limits", "Limits · Jamra"),
    ("credits", "Credits", "Credits · Jamra"),
]

AREA_PICKER = """
  <section id="area" class="band">
    <div class="wrap grid-2">
      <div>
        <h2 class="h3">Area</h2>
        <div class="tabs" role="tablist" aria-label="Ways to choose an area">
          <button role="tab" id="tab-preset" aria-controls="pane-preset" aria-selected="true" class="tab">Fire areas</button>
          <button role="tab" id="tab-country" aria-controls="pane-country" aria-selected="false" class="tab" tabindex="-1">Countries</button>
          <button role="tab" id="tab-draw" aria-controls="pane-draw" aria-selected="false" class="tab" tabindex="-1">Draw</button>
          <button role="tab" id="tab-coords" aria-controls="pane-coords" aria-selected="false" class="tab" tabindex="-1">Lat / Lon</button>
        </div>
        <div id="pane-preset" role="tabpanel" aria-labelledby="tab-preset" class="pane"><div id="preset-list" class="chips"></div></div>
        <div id="pane-country" role="tabpanel" aria-labelledby="tab-country" class="pane" hidden><div id="country-list" class="chips"></div></div>
        <div id="pane-draw" role="tabpanel" aria-labelledby="tab-draw" class="pane" hidden>
          <div class="row">
            <button type="button" class="btn" id="draw-polygon">Draw polygon</button>
            <button type="button" class="btn" id="draw-circle">Draw circle</button>
            <button type="button" class="btn ghost" id="draw-clear">Clear</button>
          </div>
          <p class="fine">Polygon: click points, double-click to finish. Circle: click centre, then edge.</p>
        </div>
        <div id="pane-coords" role="tabpanel" aria-labelledby="tab-coords" class="pane" hidden>
          <form id="coords-form" class="form">
            <fieldset><legend>Point and radius</legend>
              <label>Latitude <input name="lat" type="number" step="any" min="-90" max="90" placeholder="38.60" inputmode="decimal"></label>
              <label>Longitude <input name="lon" type="number" step="any" min="-180" max="180" placeholder="23.60" inputmode="decimal"></label>
              <label>Radius (km) <input name="r" type="number" step="1" min="1" max="300" value="25" inputmode="numeric"></label>
            </fieldset>
            <p class="or">or a bounding box</p>
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
        <div id="area-info" class="area-info" aria-live="polite"></div>
      </div>
      <div>
        <div class="map-wrap card">
          <div id="map" class="map" aria-label="Map of the selected area and recent hotspots"></div>
          <div class="map-tools">
            <span>Recent hotspots:</span>
            <div class="seg small" role="group" aria-label="Recent hotspot period">
              <button type="button" class="seg-btn" data-livewin="1" aria-pressed="true">24 h</button>
              <button type="button" class="seg-btn" data-livewin="7" aria-pressed="false">7 days</button>
              <button type="button" class="seg-btn" data-livewin="0" aria-pressed="false">Off</button>
            </div>
          </div>
          <p class="map-note">Imagery: NASA GIBS / Blue Marble · Map data © OpenStreetMap contributors (OpenFreeMap) · Hotspots: NASA FIRMS</p>
        </div>
      </div>
    </div>
  </section>"""

BODY = {
"": """
  <section class="hero" id="hero">
    <div class="wrap hero-grid">
      <div class="hero-text">
        <p class="eyebrow">NASA FIRMS · MODIS + VIIRS · 2003 to today</p>
        <h1>Did fires really increase — or did our satellites get sharper eyes?</h1>
        <p class="lead">Jamra joins 20+ years of NASA MODIS and VIIRS fire data into one fair calendar, with live early warning.</p>
        <div class="cta-row">
          <a class="btn primary big" id="evia-btn" href="calendar/?area=evia&amp;from=2003&amp;to=2025&amp;month=2007-08&amp;mode=abs&amp;detail=1">Try the Evia 2007 example</a>
          <a class="btn outline-white big" data-nav href="calendar/">Open the Calendar</a>
        </div>
        <p class="live-chip" id="live-chip"><span class="dot" aria-hidden="true"></span><span class="txt">Loading live NASA FIRMS data…</span></p>
      </div>
      <div class="hero-globe">
        <div class="globe-box">
          <div class="globe-fallback" id="globe-fallback"><img src="img/earth-blue-marble.webp" width="720" height="720" alt="Earth from space, centred on the Mediterranean (NASA Blue Marble imagery)" fetchpriority="low"></div>
          <div id="globe" class="map" role="img" aria-label="Globe with recent fire hotspots from NASA FIRMS"></div>
        </div>
        <p class="img-credit">Imagery: NASA GIBS / Blue Marble</p>
      </div>
    </div>
  </section>

  <section id="problem" class="band">
    <div class="wrap">
      <div class="section-head">
        <h2>The problem in one picture</h2>
        <p>In our 8 countries the sharper VIIRS sensor recorded <strong data-k-global>6.2×</strong> as many <span class="term" data-term="hotspot">hotspots</span> as MODIS in the same months, so the raw record jumps in 2012. Switch to Harmonized to see the fair record.</p>
      </div>
      <div class="card">
        <div class="hero-head row" style="justify-content:space-between">
          <h3 id="hero-title" style="margin:0">Yearly hotspots</h3>
          <div class="row">
            <label class="sr" for="hero-area">Area</label>
            <select id="hero-area" aria-label="Area for the chart"></select>
            <div class="seg" role="group" aria-label="Record type">
              <button type="button" class="seg-btn" data-hero="raw" aria-pressed="true">Raw (stitched)</button>
              <button type="button" class="seg-btn" data-hero="harm" aria-pressed="false">Harmonized</button>
            </div>
          </div>
        </div>
        <div id="hero-chart" class="chart" role="img" aria-label="Yearly hotspot chart"></div>
        <p id="hero-caption" class="caption"></p>
      </div>
    </div>
  </section>

  <section id="what">
    <div class="wrap">
      <div class="section-head"><h2>What you can do</h2><p>For emergency managers, firefighting teams, land and forest managers, and scientists.</p></div>
      <div class="feature-cards">
        <div class="card feature"><span class="ic">""" + icon("calendar") + """</span><h3>Calendar</h3><p>See any area's fire history, month by month, compared with its usual.</p><a data-nav href="calendar/">Open the Calendar →</a></div>
        <div class="card feature"><span class="ic">""" + icon("bell") + """</span><h3>Alerts</h3><p>Know if this month is unusual, checked every 3 hours.</p><a data-nav href="alerts/">See today's alerts →</a></div>
        <div class="card feature"><span class="ic">""" + icon("radio") + """</span><h3>Live data</h3><p>Get the newest NASA FIRMS detections for your area as a table or CSV.</p><a data-nav href="live/">Get live data →</a></div>
      </div>
      <p class="fine" style="margin-top:14px">Village councils, municipalities and farmers benefit through the local authorities and civil protection teams that use Jamra.</p>
    </div>
  </section>

  <section id="works" class="band">
    <div class="wrap bignum">
      <div><h2 style="margin-bottom:6px">Does it work?</h2><span class="n" id="big-err">87% → 40%</span></div>
      <p id="big-err-text">Typical monthly error, raw MODIS → harmonized, on years the model never saw.</p>
      <a class="btn" data-nav href="validation/">See the validation """ + icon("arrow") + """</a>
    </div>
  </section>""",

"calendar": AREA_PICKER + """
  <section id="kpis" class="wrap">
    <div class="range-row">
      <h2 class="h3" id="area-title">Selected area</h2>
      <div class="range">
        <label>From <select id="from-year"></select></label>
        <label>To <select id="to-year"></select></label>
        <label class="check"><input type="checkbox" id="static-filter" checked> Hide likely gas flares / industry</label>
      </div>
    </div>
    <div class="kpi-grid" id="kpi-grid"><div class="kpi"></div><div class="kpi"></div><div class="kpi"></div><div class="kpi"></div><div class="kpi"></div></div>
  </section>
  <section id="calendar" class="band">
    <div class="wrap">
      <div class="cal-head">
        <p class="sub">Rows are years, columns are months (VIIRS-equivalent hotspots). Select a cell for details.</p>
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
        <div id="cal" class="cal" role="grid" aria-label="Burning activity calendar"></div>
        <div class="cal-foot">
          <span><span class="key hatch-key"></span> estimated from MODIS on the VIIRS scale (<span data-unc-label>±</span>)</span>
          <span><span class="key solid-key"></span> observed (VIIRS)</span>
          <span><span class="key j-key"></span> NOAA-20, converted</span>
          <span><span class="key gap-key"></span> data gap</span>
          <span class="dl">
            <button type="button" class="btn ghost small" id="dl-cal-csv">Download CSV</button>
            <button type="button" class="btn ghost small" id="dl-cal-png">Download PNG</button>
            <button type="button" class="btn small primary" id="dl-summary-png">Summary PNG</button>
            <button type="button" class="btn small primary" id="dl-summary-pdf">Summary PDF</button>
          </span>
        </div>
      </div>
      <div id="detail" class="card detail" hidden tabindex="-1" aria-live="polite"></div>
      <div class="card season" id="season"></div>
    </div>
  </section>""",

"alerts": """
  <section id="alerts" class="wrap">
    <div id="data-status" class="status-panel" aria-live="polite"></div>
    <p class="note" id="scale-note">Live counts come from VIIRS NOAA-20 (S-NPP stopped on 2 Nov 2026) and are converted to the S-NPP scale of our history: NOAA-20 × <span data-k-jn>0.97</span>, a factor measured on 2018–2025 data.</p>
    <div id="alert-list" class="alert-list"></div>
    <p class="feeds">Public feeds: <a href="../data/live/alerts.json">alerts.json</a> · <a href="../data/live/alerts.xml">RSS</a> · <a href="../data/live/status.json">status.json</a></p>
    <p class="note">Not an emergency service: satellite data arrive with hours of delay. In an emergency, call your local emergency number (for example 112 in the EU and Türkiye).</p>
  </section>""",

"live": AREA_PICKER + """
  <section id="live" class="wrap">
    <p class="sub">Newest VIIRS NOAA-20 detections for the selected area, from the NASA FIRMS API (near real time). Raw detections, not converted.</p>
    <form id="live-form" class="row live-row">
      <label>Last <select name="days">
        <option value="1">24 hours</option><option value="2">2 days</option><option value="3">3 days</option>
        <option value="5">5 days</option><option value="7" selected>7 days</option></select></label>
      <button class="btn primary" type="submit">Fetch from NASA FIRMS</button>
      <button class="btn ghost" type="button" id="dl-live-csv" disabled>Download CSV</button>
    </form>
    <p id="live-stamp" class="msg" role="status"></p>
    <div class="table-wrap card"><table id="live-table" class="table"><caption class="sr">Live hotspots</caption><thead></thead><tbody></tbody></table></div>
  </section>""",

"how-it-works": """
  <section id="how" class="wrap">
    <ol class="steps">
      <li class="card"><span class="num">1</span><h2 class="h3">Overlap years</h2><p>From 2012 both sensors watched the same fires. MODIS on Aqua and VIIRS on S-NPP pass at the same time of day (about 1:30 pm and 1:30 am).</p></li>
      <li class="card"><span class="num">2</span><h2 class="h3">Conversion factor</h2><p>For each country and calendar month we measure VIIRS hotspots per MODIS hotspot. A small area gets its own factor, pulled toward the country value when it has few detections: k = (V + λ·k<sub>country</sub>) / (M + λ).</p></li>
      <li class="card"><span class="num">3</span><h2 class="h3">Old record on the new scale</h2><p>MODIS months before 2012 become <em>VIIRS-equivalent hotspots</em> with an error range. Each month is then compared with the same month in other years.</p></li>
    </ol>
    <div class="card why"><h2 class="h3">Methods compared</h2><div id="why-table"></div></div>
    <div class="card arch">
      <h2 class="h3">Data flow</h2>
      <p>History (2003 → last month) comes from NASA FIRMS yearly archive files and the FIRMS API, rebuilt automatically every month. The newest days come from the FIRMS API every 3 hours. <span class="term" data-term="api">Why not fetch 20 years on every click?</span></p>
      <p>S-NPP stopped on 2 Nov 2026. Live data come from NOAA-20 (same VIIRS instrument), converted to the S-NPP scale with a measured factor (×<span data-k-jn>0.97</span>).</p>
    </div>
  </section>""",

"validation": """
  <section id="validation" class="wrap">
    <div class="card split" id="split-text"></div>
    <div class="kpi-grid" id="test-kpis"></div>
    <div class="grid-2">
      <div class="card"><h2 class="h4">High-activity months in the test years (countries)</h2><div id="conf-country"></div></div>
      <div class="card"><h2 class="h4">Small regions: local factor vs country factor (test years)</h2><div id="small-table"></div><p class="fine" id="decision-text"></p></div>
    </div>
    <div class="card"><h2 class="h4">Fire areas one by one (test years)</h2><div id="preset-table"></div></div>
    <div class="grid-2">
      <div class="card"><h2 class="h4">Predicted vs actual (cross-validation, all calibration years)</h2><div id="scatter" class="chart"></div><p class="caption" id="scatter-cap"></p></div>
      <div class="card"><h2 class="h4">Error by method (test years)</h2><div id="err-bars" class="chart"></div><p class="caption" id="err-cap"></p></div>
    </div>
    <div class="kpi-grid" id="val-kpis"></div>
    <div class="grid-2">
      <div class="card"><h2 class="h4">Is the VIIRS / MODIS ratio stable over time?</h2><div id="drift" class="chart"></div><p class="caption" id="drift-cap"></p></div>
      <div class="card"><h2 class="h4">Error by country (cross-validation)</h2><div id="struggle"></div></div>
    </div>
  </section>""",

"limits": """
  <section id="limits" class="wrap">
    <div class="kpi-grid" id="unc-kpis"></div>
    <ul class="limits">
      <li><strong>Hotspots are not fires</strong> and not burned area. One big fire makes many hotspots.</li>
      <li><strong>Clouds and smoke hide fires.</strong> Small or short fires are missed, MODIS more than VIIRS.</li>
      <li><strong>Values before 2012 are estimates</strong> from MODIS on the VIIRS scale, shown with an error range. Small areas have wider ranges.</li>
      <li><strong>Outages and orbit drift.</strong> Old satellites drift in orbit; the VIIRS/MODIS ratio is checked year by year.</li>
      <li><strong>S-NPP stopped on 2 Nov 2026.</strong> Live data come from NOAA-20 (same VIIRS instrument), converted to the S-NPP scale with a measured factor.</li>
      <li><strong>Near-real-time and standard data differ slightly.</strong> Recent months use near-real-time data until NASA's standard data replace them.</li>
      <li><strong>Not every hotspot is a wildfire.</strong> Farm burning, gas flares, industry and, in conflict areas, explosions or burning buildings can create hotspots. The static-source filter can make mistakes.</li>
      <li><strong>Coverage:</strong> Portugal, Spain, Greece, Türkiye, Cyprus, Lebanon, Jordan and Palestine.</li>
      <li><strong>Latency is hours. This is not an emergency service.</strong></li>
    </ul>
  </section>""",

"credits": """
  <section id="credits" class="wrap">
    <h2>Data sources</h2>
    <p class="ack">We acknowledge the use of data and/or imagery from NASA's Fire Information for Resource Management System (FIRMS) (<a href="https://earthdata.nasa.gov/firms">https://earthdata.nasa.gov/firms</a>), part of NASA's Land, Atmosphere Near real-time Capability for Earth observations (LANCE) (<a href="https://earthdata.nasa.gov/lance">https://earthdata.nasa.gov/lance</a>) and NASA's Earth Science Data and Information System (ESDIS).</p>
    <h2 class="h4">Data used</h2>
    <ul>
      <li>MODIS Collection 6.1 active fire (Terra and Aqua), standard processing, FIRMS yearly country files and FIRMS API.</li>
      <li>VIIRS 375 m active fire (S-NPP and NOAA-20), standard processing, FIRMS yearly country files and FIRMS API.</li>
      <li>VIIRS NOAA-20 near-real-time active fire, FIRMS API.</li>
    </ul>
    <h2 class="h4">References</h2>
    <ul class="refs">
      <li>Giglio, L., Schroeder, W., &amp; Justice, C. O. (2016). The collection 6 MODIS active fire detection algorithm and fire products. <em>Remote Sensing of Environment</em>, 178, 31–41.</li>
      <li>Schroeder, W., Oliva, P., Giglio, L., &amp; Csiszar, I. A. (2014). The New VIIRS 375 m active fire detection data product: Algorithm description and initial assessment. <em>Remote Sensing of Environment</em>, 143, 85–96.</li>
      <li>Davies, D. K., Ilavajhala, S., Wong, M. M., &amp; Justice, C. O. (2009). Fire Information for Resource Management System: Archiving and distributing MODIS active fire data. <em>IEEE Transactions on Geoscience and Remote Sensing</em>, 47(1), 72–79.</li>
      <li>NASA Earthdata (2026). Transitioning from Suomi NPP VIIRS &amp; OMPS: What FIRMS Users Need to Know.</li>
    </ul>
    <h2 class="h4">Software and maps</h2>
    <p>MapLibre GL JS (BSD-3-Clause) · OpenFreeMap tiles · © OpenStreetMap contributors (ODbL) · OpenMapTiles · Colour ramps: Viridis and Cividis (matplotlib, CC0), YlOrRd and RdBu (ColorBrewer, Apache-2.0). No NASA logos are used; NASA does not endorse this project.</p>
    <h2 class="h4">Use of Super Intelligence (SI)</h2>
    <p class="si">We used an SI coding assistant (Claude Code by Anthropic) to write the code for the data pipeline, website, live system and slides, following our design and decisions. The team chose the method, checked results against NASA FIRMS data, verified every reference, and wrote and rehearsed the pitch.</p>
    <p>Open source (MIT licence): <a id="repo-link" href="https://github.com/ahmedetk/jamra">github.com/ahmedetk/jamra</a></p>
  </section>
  <section id="team" class="band">
    <div class="wrap">
      <h2>Team Astro Byte</h2>
      <div class="team" id="team-grid"></div>
      <p class="sub"><b>Shared work:</b> choosing the idea and the method, testing the site with real users, and rehearsing the pitch.</p>
      <p class="fine">NASA Space Apps Challenge 2026 (local event by NOVA) · Challenge: Harmonization of MODIS and VIIRS Hot Spots.</p>
    </div>
  </section>""",
}

REDIRECT = """<script>
// Old one-page links (#calendar, #alerts, …) and old shared URLs open the new pages, keeping their parameters.
(function () {
  var map = { calendar: 'calendar/', kpis: 'calendar/', area: 'calendar/', alerts: 'alerts/', live: 'live/', how: 'how-it-works/',
    validation: 'validation/', limits: 'limits/', credits: 'credits/', team: 'credits/' };
  var h = (location.hash || '').slice(1), q = location.search;
  if (map[h]) { location.replace(map[h] + q); return; }
  if (/[?&](month|mode|res|poly|pal)=/.test(q)) location.replace('calendar/' + q);
})();
</script>"""


def page(slug, label, title):
    R = "" if slug == "" else "../"
    nav = "\n".join(
        f'      <a href="{R}{s + "/" if s else ""}" data-nav{" aria-current=\"page\"" if s == slug else ""}>{lab}</a>'
        for s, lab, _ in PAGES)
    body = BODY[slug].replace('href="calendar/', f'href="{R}calendar/').replace('href="alerts/', f'href="{R}alerts/')
    band = ""
    if slug in PURPOSE:
        t, purpose = PURPOSE[slug]
        band = f'<div class="page-band"><div class="wrap"><h1>{t}</h1><p>{purpose}</p></div></div>\n'
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="Jamra harmonizes 20+ years of NASA MODIS and VIIRS active-fire hotspots into one fair burning activity calendar, with live early warning from NASA FIRMS.">
<meta name="theme-color" content="#2B2F36">
<meta property="og:title" content="Jamra · one fair fire record from two satellites">
<meta property="og:description" content="20+ years of NASA MODIS and VIIRS fire data in one fair calendar, with live early warning.">
<meta property="og:image" content="https://ahmedetk.github.io/jamra/icons/og-image.png">
<meta name="twitter:card" content="summary_large_image">
<link rel="preload" href="{R}fonts/plus-jakarta-sans-latin-800-normal.woff2" as="font" type="font/woff2" crossorigin>
{REDIRECT if slug == "" else ""}
<link rel="manifest" href="{R}manifest.webmanifest">
<link rel="icon" href="{R}icons/icon.svg" type="image/svg+xml">
<link rel="icon" href="{R}icons/favicon-32.png" sizes="32x32" type="image/png">
<link rel="apple-touch-icon" href="{R}icons/icon-192.png">
<link rel="stylesheet" href="{R}css/app.css">
<!-- Generated by scripts/build_pages.py. Code written with the help of an SI coding assistant (Claude Code by Anthropic). -->
</head>
<body data-page="{slug or 'home'}">
<a class="skip" href="#main">Skip to content</a>
<header class="top">
  <div class="wrap top-in">
    <a class="brand" href="{R}" data-nav aria-label="Jamra home">{logo()}<span data-product-name>Jamra</span></a>
    <button id="menu-btn" class="menu-btn" type="button" aria-expanded="false" aria-controls="site-nav">Menu</button>
    <nav aria-label="Main" class="nav" id="site-nav">
{nav}
    </nav>
    <a id="status-badge" class="badge" href="{R}alerts/" data-nav aria-live="polite" title="Live connection to NASA FIRMS">
      <span class="dot"></span><span class="txt">Checking live data…</span>
    </a>
  </div>
</header>
<main id="main">
{band}{body}
</main>
<div id="tooltip" class="tooltip" role="tooltip" hidden></div>
<div id="term-pop" class="term-pop" role="dialog" aria-modal="false" hidden></div>
<footer class="foot">
  <div class="wrap foot-grid">
    <div>
      <a class="brand" href="{R}" data-nav aria-label="Jamra home">{logo()}<span>Jamra</span></a>
      <p>Team Astro Byte · Built for the NASA Space Apps Challenge 2026.</p>
      <p class="fine">Not an official NASA product. NASA does not endorse this project.</p>
    </div>
    <div>
      <ul>
        <li><a href="{R}calendar/" data-nav>Calendar</a></li><li><a href="{R}alerts/" data-nav>Alerts</a></li><li><a href="{R}live/" data-nav>Live Data</a></li>
        <li><a href="{R}validation/" data-nav>Validation</a></li><li><a href="{R}credits/" data-nav>Credits and team</a></li>
        <li><a href="https://github.com/ahmedetk/jamra">GitHub (MIT licence)</a></li>
      </ul>
    </div>
    <div>
      <p><b>Data: NASA FIRMS.</b> We acknowledge the use of data and/or imagery from NASA's Fire Information for Resource Management System (FIRMS) (https://earthdata.nasa.gov/firms), part of NASA's Land, Atmosphere Near real-time Capability for Earth observations (LANCE) (https://earthdata.nasa.gov/lance) and NASA's Earth Science Data and Information System (ESDIS).</p>
      <p class="fine">SI disclosure: code written with the help of an SI coding assistant (Claude Code by Anthropic), following our design; the team checked results against NASA FIRMS data.</p>
    </div>
  </div>
</footer>
<script type="module" src="{R}js/app.js"></script>
</body>
</html>
"""


def main():
    for slug, label, title in PAGES:
        d = PUB / slug if slug else PUB
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text(page(slug, label, title), encoding="utf-8")
        print("wrote", (d / "index.html").relative_to(PUB))


if __name__ == "__main__":
    main()
