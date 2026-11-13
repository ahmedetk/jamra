"""Aggregate FIRMS archive rows to grid cells, countries and preset areas.

Two passes over the raw CSVs:
  1. per 0.1-degree cell monthly counts -> find persistent cells (likely gas
     flares / industry), and remember which country each cell belongs to;
  2. per area (country / preset) monthly counts + FRP and daily counts, with
     the part coming from persistent cells kept separately so users can switch
     the static-source filter on and off and see what it removes.

Code written with the help of an SI coding assistant (Claude Code).
"""
from __future__ import annotations

import csv
import json
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from . import config
from .firms import cell_id, filter_reason, in_box, month_index, parse_date, sensor_code

SENSOR_DIRS = {"modis": ("A", "T"), "viirs_snpp": ("N",), "viirs_noaa20": ("J",)}


def _nested():
    return defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: [0, 0.0])))


@dataclass
class Aggregates:
    # cells[cid][sensor][mi] = count
    cells: dict = field(default_factory=lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(int))))
    cell_country: dict = field(default_factory=lambda: defaultdict(lambda: defaultdict(int)))
    flagged_cells: set = field(default_factory=set)
    # monthly[area][sensor][mi] = [count, frp]; flagged part in monthly_static
    monthly: dict = field(default_factory=_nested)
    monthly_static: dict = field(default_factory=_nested)
    # daily[area][sensor][ordinal] = count (persistent cells excluded)
    daily: dict = field(default_factory=lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(int))))
    # removed[country][sensor][year][reason] = count ; kept likewise under "kept"
    removed: dict = field(default_factory=lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(int)))))
    first_day: dict = field(default_factory=dict)  # sensor -> first ordinal with data
    last_day: dict = field(default_factory=dict)


def raw_files(cache: Path) -> list[tuple[str, int, str, Path]]:
    cfg = config.load()
    out = []
    for sensor_dir in SENSOR_DIRS:
        s = cfg["firms"]["sensors"][sensor_dir]
        for year in range(s["first_year"], s["last_year"] + 1):
            for country in cfg["countries"]:
                f = cache / "raw" / sensor_dir / str(year) / f"{s['prefix']}_{year}_{country}.csv"
                if f.exists():
                    out.append((sensor_dir, year, country, f))
    return out


def _rows(path: Path):
    with open(path, newline="", encoding="utf-8") as fh:
        yield from csv.DictReader(fh)


def build(cache: Path | None = None, extra_files: list | None = None) -> Aggregates:
    cfg = config.load()
    cache = cache or config.path("cache")
    filters = cfg["filters"]
    deg = cfg["grid"]["cell_deg"]
    presets = cfg["presets"]
    files = raw_files(cache) + (extra_files or [])
    agg = Aggregates()

    # ---------------- pass 1: cells
    for sensor_dir, year, country, f in files:
        for row in _rows(f):
            sensor = sensor_code(row.get("satellite", ""), row.get("instrument", ""))
            if sensor is None or sensor == "K":
                continue
            if filter_reason(row, sensor, filters):
                continue
            lat, lon = float(row["latitude"]), float(row["longitude"])
            d = parse_date(row["acq_date"])
            cid = cell_id(lat, lon, deg)
            agg.cells[cid][sensor][month_index(d.year, d.month)] += 1
            agg.cell_country[cid][country] += 1

    agg.flagged_cells = persistent_cells(agg.cells, filters["persistence"])

    # ---------------- pass 2: areas
    for sensor_dir, year, country, f in files:
        for row in _rows(f):
            sensor = sensor_code(row.get("satellite", ""), row.get("instrument", ""))
            if sensor is None or sensor == "K":
                continue
            reason = filter_reason(row, sensor, filters)
            agg.removed[country][sensor][year][reason or "kept"] += 1
            if reason:
                continue
            lat, lon = float(row["latitude"]), float(row["longitude"])
            d = parse_date(row["acq_date"])
            mi = month_index(d.year, d.month)
            frp = float(row.get("frp") or 0.0)
            static = cell_id(lat, lon, deg) in agg.flagged_cells
            if static:
                agg.removed[country][sensor][year]["persistent_cell"] += 1
            areas = [country] + [p for p, spec in presets.items()
                                 if spec["country"] == country and in_box(lat, lon, spec["box"])]
            for area in areas:
                target = agg.monthly_static if static else agg.monthly
                cell = target[area][sensor][mi]
                cell[0] += 1
                cell[1] += frp
                if not static:
                    agg.daily[area][sensor][d.toordinal()] += 1
            o = d.toordinal()
            agg.first_day[sensor] = min(agg.first_day.get(sensor, o), o)
            agg.last_day[sensor] = max(agg.last_day.get(sensor, o), o)
    return agg


def persistent_cells(cells: dict, spec: dict) -> set:
    """Cells active in most months of most VIIRS-era years: likely static heat sources.

    A cell-year counts as 'persistent' when the cell had detections in at least
    `min_month_share` of that year's months; the cell is flagged when that is
    true in at least `min_year_share` of the years 2012-2025.
    """
    if not spec.get("enabled", True):
        return set()
    years = range(2012, 2026)
    flagged = set()
    for cid, by_sensor in cells.items():
        active = set()
        for sensor, months in by_sensor.items():
            active.update(mi for mi, n in months.items() if n > 0)
        persistent_years = 0
        for y in years:
            base = month_index(y, 1)
            n_active = sum(1 for m in range(12) if base + m in active)
            if n_active / 12 >= spec["min_month_share"]:
                persistent_years += 1
        if persistent_years / len(years) >= spec["min_year_share"]:
            flagged.add(cid)
    return flagged


def cell_owner(agg: Aggregates) -> dict[str, str]:
    """Country that owns each cell (country with most detections in it)."""
    return {cid: max(c.items(), key=lambda kv: kv[1])[0] for cid, c in agg.cell_country.items()}


def save_debug(agg: Aggregates, out: Path) -> None:
    out.write_text(json.dumps({"flagged": sorted(agg.flagged_cells)}))
