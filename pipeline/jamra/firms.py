"""Parsing and filtering of NASA FIRMS active-fire rows (archive CSV and API CSV).

Column names follow FIRMS: latitude, longitude, acq_date, acq_time, satellite,
instrument, confidence (MODIS 0-100, VIIRS l/n/h), frp, daynight, type.
Code written with the help of an AI coding assistant (Claude Code by Anthropic).
"""
from __future__ import annotations

import math
from datetime import date

# One-letter sensor codes used everywhere in Jamra.
#   A = MODIS Aqua, T = MODIS Terra, N = VIIRS S-NPP, J = VIIRS NOAA-20, K = VIIRS NOAA-21
SENSOR_NAMES = {
    "A": "MODIS Aqua",
    "T": "MODIS Terra",
    "N": "VIIRS S-NPP",
    "J": "VIIRS NOAA-20",
    "K": "VIIRS NOAA-21",
}

_SAT = {
    "aqua": "A", "a": "A",
    "terra": "T", "t": "T",
    "n": "N", "npp": "N", "suomi npp": "N", "snpp": "N", "s-npp": "N",
    "1": "J", "n20": "J", "noaa-20": "J", "noaa20": "J", "j1": "J",
    "2": "K", "n21": "K", "noaa-21": "K", "noaa21": "K", "j2": "K",
}

MONTH0_YEAR = 2000  # month index 0 = January 2000


def sensor_code(satellite: str, instrument: str = "") -> str | None:
    s = (satellite or "").strip().lower()
    code = _SAT.get(s)
    if code is None and instrument.strip().upper() == "MODIS":
        code = "A" if s.startswith("a") else ("T" if s.startswith("t") else None)
    return code


def month_index(year: int, month: int) -> int:
    return (year - MONTH0_YEAR) * 12 + (month - 1)


def month_label(mi: int) -> str:
    return f"{MONTH0_YEAR + mi // 12}-{mi % 12 + 1:02d}"


def cell_id(lat: float, lon: float, deg: float = 0.1) -> str:
    """0.1-degree grid cell id 'ix_iy' (ix from -180 east, iy from -90 north)."""
    ix = int(math.floor((lon + 180.0) / deg + 1e-9))
    iy = int(math.floor((lat + 90.0) / deg + 1e-9))
    return f"{ix}_{iy}"


def cell_center(cid: str, deg: float = 0.1) -> tuple[float, float]:
    ix, iy = (int(v) for v in cid.split("_"))
    return (iy + 0.5) * deg - 90.0, (ix + 0.5) * deg - 180.0  # lat, lon


def normalize_confidence(value: str) -> str:
    v = (value or "").strip().lower()
    return {"low": "l", "nominal": "n", "high": "h"}.get(v, v)


def filter_reason(row: dict, sensor: str, cfg_filters: dict) -> str | None:
    """Return None if the row is kept, else the reason it was removed."""
    t = (row.get("type") or "").strip()
    if t != "" and int(float(t)) not in cfg_filters["keep_types"]:
        return f"type_{int(float(t))}"
    conf = row.get("confidence", "")
    if sensor in ("A", "T"):
        try:
            if float(conf) < cfg_filters["modis_min_confidence"]:
                return "low_confidence"
        except ValueError:
            return "low_confidence"
    else:
        if normalize_confidence(conf) not in cfg_filters["viirs_confidence"]:
            return "low_confidence"
    if not cfg_filters.get("keep_day_and_night", True) and row.get("daynight") == "N":
        return "night"
    return None


def parse_date(s: str) -> date:
    return date(int(s[0:4]), int(s[5:7]), int(s[8:10]))


def in_box(lat: float, lon: float, box: list[float]) -> bool:
    w, s, e, n = box
    return w <= lon <= e and s <= lat <= n


def dedupe_key(row: dict) -> tuple:
    """Key used to make the live ingest idempotent."""
    return (
        round(float(row["latitude"]), 4),
        round(float(row["longitude"]), 4),
        row["acq_date"].strip(),
        row["acq_time"].strip().zfill(4),
        (row.get("satellite") or "").strip(),
    )
