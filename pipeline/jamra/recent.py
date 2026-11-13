"""Fill the months after the newest yearly archive (e.g. Jan-Oct 2026) from the FIRMS API.

Uses standard-processing (SP) sources where FIRMS has them and near-real-time
(NRT) after that, in 5-day chunks, throttled under the 5,000 transactions per
10 minutes limit. Rows are assigned to countries with the archive's own grid
(cell -> country) and written in the same layout as the yearly archive files,
so `jamra.build` treats them like any other year.

Usage: python -m jamra.recent [--year 2026] [--through 2026-10-31]
Code written with the help of an SI coding assistant (Claude Code).
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta

from . import config
from .firms import dedupe_key
from .live import assign_country, http_get

BOXES = {
    "iberia": [-9.6, 35.9, 4.4, 43.9],
    "canaries": [-18.3, 27.5, -13.3, 29.5],
    "azores_madeira": [-31.5, 32.3, -16.0, 40.0],
    "greece": [19.3, 34.8, 29.7, 41.8],
    "east": [25.6, 29.1, 44.9, 42.2],  # Türkiye, Cyprus, Lebanon, Palestine, Jordan
}
SENSORS = {  # sensor dir -> (SP source, NRT source)
    "modis": ("MODIS_SP", "MODIS_NRT"),
    "viirs_snpp": ("VIIRS_SNPP_SP", "VIIRS_SNPP_NRT"),
    "viirs_noaa20": ("VIIRS_NOAA20_SP", "VIIRS_NOAA20_NRT"),
}
FIELDS = ["latitude", "longitude", "brightness", "bright_ti4", "scan", "track", "acq_date", "acq_time", "satellite",
          "instrument", "confidence", "version", "bright_t31", "bright_ti5", "frp", "daynight", "type"]


def availability(key: str) -> dict:
    api = config.load()["firms"]["api_base"]
    rows = csv.DictReader(io.StringIO(http_get(f"{api}/data_availability/csv/{key}/ALL")))
    return {r["data_id"]: (date.fromisoformat(r["min_date"]), date.fromisoformat(r["max_date"])) for r in rows}


class Budget:
    """Stay under the FIRMS transaction limit using the official status endpoint."""

    def __init__(self, key: str, limit: int = 4000):
        self.key, self.limit, self.last = key, limit, 0.0

    def wait(self):
        if time.time() - self.last < 20:
            return
        self.last = time.time()
        while True:
            try:
                st = json.loads(http_get(f"https://firms.modaps.eosdis.nasa.gov/mapserver/mapkey_status/?MAP_KEY={self.key}", timeout=40))
                used = int(st.get("current_transactions", 0))
            except Exception:
                return
            if used < self.limit:
                return
            print(f"  FIRMS budget {used}/5000 used, waiting 60 s…", flush=True)
            time.sleep(60)


def fetch(key, source, box, start, span, budget):
    api = config.load()["firms"]["api_base"]
    budget.wait()
    url = f"{api}/area/csv/{key}/{source}/{','.join(map(str, box))}/{span}/{start.isoformat()}"
    text = http_get(url, timeout=180)
    if text.lstrip().lower().startswith(("invalid", "error", "<")):
        raise RuntimeError(f"{source} {start}: {text[:100]}")
    return list(csv.DictReader(io.StringIO(text)))


def run(year: int, through: date) -> None:
    cfg = config.load()
    key = config.secret("FIRMS_MAP_KEY")
    if not key:
        raise SystemExit("FIRMS_MAP_KEY missing")
    avail = availability(key)
    grid = json.loads((config.path("web_data") / "cells.json").read_text(encoding="utf-8"))
    owner = {cid: c["c"] for cid, c in grid["cells"].items()}
    deg = grid["cell_deg"]
    budget = Budget(key)
    for sensor_dir, (sp, nrt) in SENSORS.items():
        prefix = cfg["firms"]["sensors"][sensor_dir]["prefix"]
        out_dir = config.path("cache") / "raw" / sensor_dir / str(year)
        if (out_dir / "_done.json").exists():
            print(sensor_dir, year, "already done")
            continue
        jobs = []
        d = date(year, 1, 1)
        while d <= through:
            span = min(5, (through - d).days + 1)
            src = sp if sp in avail and d + timedelta(days=span - 1) <= avail[sp][1] else nrt
            if src in avail and d <= avail[src][1] and d + timedelta(days=span - 1) >= avail[src][0]:
                for b in BOXES.values():
                    jobs.append((src, b, d, span))
            d += timedelta(days=span)
        print(f"{sensor_dir}: {len(jobs)} API calls", flush=True)
        rows: dict = {}
        t0 = time.time()
        with ThreadPoolExecutor(max_workers=4) as ex:
            for i, res in enumerate(ex.map(lambda j: fetch(key, j[0], j[1], j[2], j[3], budget), jobs), 1):
                for r in res:
                    if r.get("acq_date", "") <= through.isoformat():
                        rows[dedupe_key(r)] = r
                if i % 50 == 0:
                    print(f"  {i}/{len(jobs)} calls, {len(rows):,} rows, {time.time() - t0:.0f}s", flush=True)
        by_country: dict = {}
        for r in rows.values():
            c = assign_country(float(r["latitude"]), float(r["longitude"]), owner, deg)
            if c:
                by_country.setdefault(c, []).append(r)
        out_dir.mkdir(parents=True, exist_ok=True)
        records = []
        for c, rs in by_country.items():
            rs.sort(key=lambda r: (r["acq_date"], r["acq_time"].zfill(4)))
            f = out_dir / f"{prefix}_{year}_{c}.csv"
            with open(f, "w", newline="", encoding="utf-8") as fh:
                w = csv.DictWriter(fh, fieldnames=[k for k in FIELDS if k in rs[0]], extrasaction="ignore")
                w.writeheader()
                w.writerows(rs)
            records.append({"sensor": sensor_dir, "year": year, "country": c, "rows": len(rs),
                            "file": f"raw/{sensor_dir}/{year}/{f.name}", "source": "FIRMS API (SP then NRT)",
                            "through": through.isoformat()})
        (out_dir / "_done.json").write_text(json.dumps(records, indent=1))
        print(f"{sensor_dir}: {sum(len(v) for v in by_country.values()):,} rows in our countries", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int, default=date.today().year)
    ap.add_argument("--through", default=None)
    a = ap.parse_args()
    t = date.fromisoformat(a.through) if a.through else date.today().replace(day=1) - timedelta(days=1)
    run(a.year, t)


if __name__ == "__main__":
    main()
