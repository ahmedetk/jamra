"""Live ingest: newest NOAA-20 VIIRS hotspots from NASA FIRMS -> early-warning levels.

Runs every 3 hours (GitHub Actions). Idempotent: rows are de-duplicated by
(lat, lon, acq_date, acq_time, satellite) and merged into a small store of the
current and previous month. If FIRMS fails, the last good live.json is kept and
status.json records the failure, so the website never breaks.

Sources, in order:
  1. FIRMS area API (needs FIRMS_MAP_KEY), source VIIRS_NOAA20_NRT, 5-day chunks
  2. FIRMS public active-fire file J1_VIIRS_C2_Global_7d.csv (no key)

Usage: python -m jamra.live [--public-only] [--regions Europe,Russia_Asia]
Code written with the help of an SI coding assistant (Claude Code).
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import time
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta, timezone
from email.utils import format_datetime
from pathlib import Path
from xml.sax.saxutils import escape

from . import anomaly, config
from .firms import cell_id, dedupe_key, filter_reason, in_box, sensor_code

UA = "jamra-live/1.0 (NASA Space Apps 2026 project)"
PUBLIC_BASE = "https://firms.modaps.eosdis.nasa.gov/data/active_fire/noaa-20-viirs-c2/csv"
STORE_FIELDS = ["latitude", "longitude", "acq_date", "acq_time", "satellite", "confidence", "frp", "daynight"]


def http_get(url: str, timeout: float = 120, retries: int = 4) -> str:
    delay = 3.0
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Encoding": "identity"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            last = e
            if 400 <= e.code < 500 and e.code not in (408, 429):
                raise
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:
            last = e
        time.sleep(delay)
        delay *= 2
    raise RuntimeError(f"GET failed after {retries} tries: {last}")


def key_works(key: str) -> bool:
    if not key:
        return False
    try:
        txt = http_get(f"https://firms.modaps.eosdis.nasa.gov/mapserver/mapkey_status/?MAP_KEY={key}", timeout=40, retries=2)
        return "invalid" not in txt.lower()
    except Exception:
        return False


def fetch_api(key: str, boxes: dict, source: str, start: date, end: date) -> list[dict]:
    rows = []
    api = config.load()["firms"]["api_base"]
    d = start
    while d <= end:
        span = min(5, (end - d).days + 1)
        for name, b in boxes.items():
            url = f"{api}/area/csv/{key}/{source}/{','.join(str(v) for v in b)}/{span}/{d.isoformat()}"
            text = http_get(url)
            if text.lstrip().lower().startswith(("invalid", "error", "<")):
                raise RuntimeError(f"FIRMS API said: {text[:120]}")
            rows += list(csv.DictReader(io.StringIO(text)))
        d += timedelta(days=span)
    return rows


def fetch_public(regions: list[str]) -> list[dict]:
    rows = []
    for r in regions:
        rows += list(csv.DictReader(io.StringIO(http_get(f"{PUBLIC_BASE}/J1_VIIRS_C2_{r}_7d.csv", timeout=300))))
    return rows


def load_store(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def save_store(path: Path, rows: list[dict], keep_from: date) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [r for r in rows if r["acq_date"] >= keep_from.isoformat()]
    rows.sort(key=lambda r: (r["acq_date"], r["acq_time"].zfill(4)))
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=STORE_FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def assign_country(lat: float, lon: float, owner: dict, deg: float) -> str | None:
    cid = cell_id(lat, lon, deg)
    if cid in owner:
        return owner[cid]
    ix, iy = (int(v) for v in cid.split("_"))
    for r in (1, 2):
        for dx in range(-r, r + 1):
            for dy in range(-r, r + 1):
                c = owner.get(f"{ix + dx}_{iy + dy}")
                if c:
                    return c
    return None


def run(public_only: bool = False, regions: list[str] | None = None) -> dict:
    cfg = config.load()
    web = config.path("web_data")
    live_dir = web / "live"
    live_dir.mkdir(parents=True, exist_ok=True)
    status_path = live_dir / "status.json"
    status = json.loads(status_path.read_text()) if status_path.exists() else {}
    now = datetime.now(timezone.utc)
    status["last_attempt_utc"] = now.isoformat(timespec="seconds")
    try:
        meta = json.loads((web / "meta.json").read_text(encoding="utf-8"))
        grid = json.loads((web / "cells.json").read_text(encoding="utf-8"))
        owner = {cid: c["c"] for cid, c in grid["cells"].items()}
        flagged = set(grid["flagged"])
        deg = grid["cell_deg"]
        boxes = cfg["firms"]["live_boxes"]
        today = now.date()
        month_start = today.replace(day=1)
        start = min(month_start, today - timedelta(days=7))

        key = config.secret("FIRMS_MAP_KEY")
        rows, source = [], ""
        coverage_start = None
        if not public_only and key_works(key):
            rows = fetch_api(key, boxes, cfg["firms"]["live_source"], start, today)
            source = f"NASA FIRMS API ({cfg['firms']['live_source']})"
            coverage_start = start
        if not source:
            rows = fetch_public(regions or ["Global"])
            source = "NASA FIRMS active fire file (VIIRS NOAA-20, last 7 days)"

        store_path = config.ROOT / "data" / "live" / "store.csv"
        merged = {dedupe_key(r): r for r in load_store(store_path)}
        new = 0
        for r in rows:
            try:
                lat, lon = float(r["latitude"]), float(r["longitude"])
            except (KeyError, ValueError):
                continue
            if not any(in_box(lat, lon, b) for b in boxes.values()):
                continue
            k = dedupe_key(r)
            if k not in merged:
                new += 1
            merged[k] = {f: r.get(f, "") for f in STORE_FIELDS}
        all_rows = list(merged.values())
        save_store(store_path, all_rows, (month_start - timedelta(days=40)))

        # keep valid, non-static rows inside our countries
        kept = []
        for r in all_rows:
            s = sensor_code(r.get("satellite", ""), "VIIRS")
            if s != "J" or filter_reason(r, s, cfg["filters"]):
                continue
            lat, lon = float(r["latitude"]), float(r["longitude"])
            if cell_id(lat, lon, deg) in flagged:
                continue
            c = assign_country(lat, lon, owner, deg)
            if not c:
                continue
            kept.append((r, lat, lon, c))
        if not kept and not all_rows:
            raise RuntimeError("No rows received from NASA FIRMS")
        through = max((r["acq_date"] for r, *_ in kept), default=today.isoformat())
        th = date.fromisoformat(through)
        month = th.strftime("%Y-%m")
        day = th.day
        # Which days do we really have? The public file holds only 7 days; the store
        # grows with every run. Compare only the covered part of this month.
        store_first = min((r["acq_date"] for r in all_rows), default=through)
        cov = date.fromisoformat(store_first) if coverage_start is None else min(coverage_start, date.fromisoformat(store_first))
        meta_cov = config.ROOT / "data" / "live" / "coverage.json"
        if meta_cov.exists():
            prev = json.loads(meta_cov.read_text())
            if prev.get("month") == month:
                cov = min(cov, date.fromisoformat(prev["from"]))
        win_start = max(th.replace(day=1), cov)
        meta_cov.write_text(json.dumps({"month": month, "from": win_start.isoformat()}))
        from_day = win_start.day
        ndays = day - from_day + 1

        cname = {a["country"]: a["id"] for a in meta["areas"] if a["kind"] == "country"}
        presets = {a["id"]: a for a in meta["areas"] if a["kind"] == "preset"}
        kjn = meta["k_jn_by_country"]
        areas = {}
        acfg = meta["anomaly"]
        last_full = int(meta["data_through"][:4]) - (0 if meta["data_through"][5:7] == "12" else 1)
        for a in meta["areas"]:
            aid = a["id"]
            if a["kind"] == "country":
                mine = [x for x in kept if x[3] == a["country"]]
            else:
                mine = [x for x in kept if x[3] == a["country"] and in_box(x[1], x[2], a["box"])]
            k = kjn.get(cname.get(a["country"]), 1.0)
            mtd_raw = sum(1 for r, *_ in mine if r["acq_date"].startswith(month) and from_day <= int(r["acq_date"][8:10]) <= day)
            last7 = sum(1 for r, *_ in mine if r["acq_date"] > (th - timedelta(days=7)).isoformat())
            hist = json.loads((web / "areas" / f"{aid}.json").read_text(encoding="utf-8"))
            d0 = date.fromisoformat(hist["daily_start"])
            others = []
            for y in range(d0.year, last_full + 1):
                if y == th.year:
                    continue
                s = date(y, th.month, from_day)
                vals = [hist["daily"][(s - d0).days + i] for i in range(ndays) if 0 <= (s - d0).days + i < len(hist["daily"])]
                if len(vals) == ndays and all(v is not None for v in vals):
                    others.append(sum(vals))
            mtd = round(mtd_raw * k, 1)
            w = anomaly.warning_level(mtd, others, acfg)
            areas[aid] = {"mtd_raw": mtd_raw, "mtd": mtd, "day": day, "from_day": from_day, "last7_raw": last7, "k_jn": k,
                          **{kk: (round(v, 1) if isinstance(v, float) else v) for kk, v in w.items()}}

        since7 = (th - timedelta(days=7)).isoformat()
        points = sorted(([round(lat, 4), round(lon, 4), r["acq_date"], r["acq_time"].zfill(4), float(r.get("frp") or 0),
                          (r.get("confidence") or "")[:1].lower(), r.get("satellite", "")]
                         for r, lat, lon, _ in kept if r["acq_date"] > since7), key=lambda p: (p[2], p[3]))
        live = {"generated_utc": now.isoformat(timespec="seconds"), "fetched_utc": now.isoformat(timespec="seconds"),
                "source": source, "through_date": through, "month": month, "day": day, "from_day": from_day,
                "note": "NOAA-20 counts converted to the S-NPP scale with a measured factor; the latest day may be incomplete.",
                "points": points, "areas": areas}
        (live_dir / "live.json").write_text(json.dumps(live, separators=(",", ":")), encoding="utf-8")
        write_feeds(live_dir, live, meta)
        status.update({"ok": True, "last_success_utc": now.isoformat(timespec="seconds"), "source": source,
                       "message": f"{len(rows)} rows received, {new} new; {len(points)} hotspots in the last 7 days",
                       "through_date": through})
    except Exception as e:  # keep the last good data
        status.update({"ok": False, "message": f"Update failed: {e}"[:300]})
        print("LIVE INGEST FAILED:", e)
    status_path.write_text(json.dumps(status, indent=1), encoding="utf-8")
    return status


def write_feeds(live_dir: Path, live: dict, meta: dict) -> None:
    label = {a["id"]: a["label"] for a in meta["areas"]}
    rank = {"extreme": 3, "high": 2, "elevated": 1}
    alerts = []
    for aid, a in live["areas"].items():
        if a.get("level") in rank:
            alerts.append({"area": aid, "label": label.get(aid, aid), "level": a["level"], "month": live["month"],
                           "from_day": a.get("from_day", 1), "through_day": a["day"], "hotspots_month_to_date": a["mtd"], "usual": a.get("median"),
                           "percentile": a.get("percentile"),
                           "text": f"{label.get(aid, aid)}: {a['level'].upper()}. {live['month']} days 1-{a['day']}: "
                                   f"{a['mtd']:.0f} hotspots vs usual {a.get('median', 0):.0f} "
                                   f"(higher than {a.get('percentile', 0):.0f}% of past years)."})
    alerts.sort(key=lambda x: (-rank[x["level"]], -(x["percentile"] or 0)))
    feed = {"generated_utc": live["generated_utc"], "source": live["source"], "alerts": alerts,
            "disclaimer": "Not an emergency service. Satellite data have hours of delay."}
    (live_dir / "alerts.json").write_text(json.dumps(feed, indent=1), encoding="utf-8")
    pub = format_datetime(datetime.fromisoformat(live["generated_utc"]))
    items = "".join(
        f"<item><title>{escape(a['label'])}: {a['level']}</title><description>{escape(a['text'])}</description>"
        f"<guid isPermaLink=\"false\">{escape(a['area'])}-{a['month']}-{a['level']}</guid><pubDate>{pub}</pubDate></item>"
        for a in alerts)
    rss = (f'<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>Jamra unusual fire activity alerts</title>'
           f"<link>https://ahmedetk.github.io/jamra/</link><description>Areas where this month's satellite hotspots are unusual "
           f"compared with the same days in past years. Data: NASA FIRMS.</description><lastBuildDate>{pub}</lastBuildDate>"
           f"{items}</channel></rss>")
    (live_dir / "alerts.xml").write_text(rss, encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--public-only", action="store_true")
    ap.add_argument("--regions", default="Global")
    a = ap.parse_args()
    print(json.dumps(run(a.public_only, a.regions.split(",")), indent=1))


if __name__ == "__main__":
    main()
