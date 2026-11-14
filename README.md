# Jamra · Burning Activity Calendar

Team **Astro Byte** · NASA Space Apps Challenge 2026 · Challenge: *Harmonization of MODIS and VIIRS Hot Spots*

Jamra turns 20+ years of NASA FIRMS active-fire hotspots from MODIS (1 km) and VIIRS (375 m)
into one fair, harmonized burning activity calendar (2003 → today) for any area in its coverage
region (Portugal, Spain, Greece, Türkiye, Cyprus, Lebanon, Jordan, Palestine), with live
early-warning checks every 3 hours. It is an installable web app (PWA). All explanations for users
live inside the app.

## Run locally
```bash
python -m venv .venv && .venv/Scripts/pip install pyyaml pytest    # Linux/macOS: .venv/bin/pip
PYTHONPATH=pipeline python -m jamra.download    # NASA FIRMS yearly files, our countries only (~150 MB)
PYTHONPATH=pipeline python -m jamra.build       # grid, quality checks, M0–M5 cross-validation, web data
PYTHONPATH=pipeline python -m jamra.live        # newest NOAA-20 hotspots + early-warning levels
PYTHONPATH=pipeline python -m pytest -q         # unit tests
python -m http.server 8000 --directory web/public
```
Or `make data`, `make test`, `make live`, `make serve`. Website pages: `python scripts/build_pages.py`.
Site checks (JavaScript errors, downloads, phone layout): `npm i puppeteer-core`, then `node scripts/site_check.mjs`.

## Architecture (always on, free)
- **History:** FIRMS yearly country archives (standard processing). `jamra.download` reads only our
  countries out of each yearly ZIP with HTTP range requests. Rebuilt monthly by `.github/workflows/archive.yml`.
- **Live:** `.github/workflows/site.yml` runs every 3 hours: FIRMS API (`VIIRS_NOAA20_NRT`, needs
  `FIRMS_MAP_KEY`) or the public FIRMS 7-day file as fallback → de-duplicated store → month-to-date vs
  past years → `live.json`, `status.json`, `alerts.json`, `alerts.xml` → GitHub Pages. If FIRMS fails,
  the last good data stay online and the status badge shows "Delayed".
- **On-demand live queries (optional):** `worker/` is a Cloudflare Worker that hides the MAP_KEY,
  caches for 15 minutes and limits box size. Put its URL in `web/public/data/site.json` → `"proxy"`.
  Without it, the app answers from the latest saved NASA snapshot.
- **Why not fetch 20 years from the API on each click?** The FIRMS API allows 5,000 transactions per
  10 minutes and each day counts; one area's full history is ~8,700 days per satellite.
- S-NPP VIIRS stopped on 2 Nov 2026 (NASA FIRMS notice), so live data come from NOAA-20, converted to
  the S-NPP scale with a factor measured on 2018–2025 (shown on the site).

## Secrets
`FIRMS_MAP_KEY` lives only in GitHub → Settings → Secrets and variables → Actions (and as a Worker
secret). Locally it is read from `../secrets.txt`, outside the repository. Never commit keys.

## Data and credits
We acknowledge the use of data and/or imagery from NASA's Fire Information for Resource Management
System (FIRMS) (https://earthdata.nasa.gov/firms), part of NASA's Land, Atmosphere Near real-time
Capability for Earth observations (LANCE) (https://earthdata.nasa.gov/lance) and NASA's Earth Science
Data and Information System (ESDIS). Map: MapLibre GL JS (BSD-3), OpenFreeMap, © OpenStreetMap
contributors. NASA does not endorse this project.

## Use of artificial intelligence (AI)
We used an AI coding assistant (Claude Code by Anthropic) to write the code for the data pipeline,
the website and the live system, following our design and decisions. The team chose the method,
checked results against NASA FIRMS data and verified every reference. Our demo video was made with
AI tools, and its voice-over is AI-generated (ElevenLabs).

MIT licence.
