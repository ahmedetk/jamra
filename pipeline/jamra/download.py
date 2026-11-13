"""Download NASA FIRMS yearly country CSVs (standard processing) for our countries.

Reads only the needed country files out of FIRMS' yearly "all countries" ZIPs
using HTTP range requests (see rangezip.py). Writes a manifest with file sizes,
row counts and SHA-256 hashes so the archive is reproducible.

Usage: python -m jamra.download [--workers 4]
Code written with the help of an SI coding assistant (Claude Code).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

from . import config
from .rangezip import RemoteZip


def jobs() -> list[tuple[str, str, int]]:
    cfg = config.load()
    out = []
    for sensor, s in cfg["firms"]["sensors"].items():
        for year in range(s["first_year"], s["last_year"] + 1):
            out.append((sensor, s["prefix"], year))
    return out


def fetch_year(sensor: str, prefix: str, year: int, force: bool = False) -> list[dict]:
    cfg = config.load()
    countries = list(cfg["countries"].keys())
    out_dir = config.path("cache") / "raw" / sensor / str(year)
    out_dir.mkdir(parents=True, exist_ok=True)
    done_flag = out_dir / "_done.json"
    if done_flag.exists() and not force:
        return json.loads(done_flag.read_text())
    url = f"{cfg['firms']['archive_base']}/{prefix}_{year}_all_countries.zip"
    z = RemoteZip(url)
    by_name = {e.name.rsplit("/", 1)[-1]: e for e in z.entries}
    records = []
    for country in countries:
        fname = f"{prefix}_{year}_{country}.csv"
        entry = by_name.get(fname)
        if entry is None:
            # FIRMS omits a country file when there were no detections that year.
            records.append({"sensor": sensor, "year": year, "country": country,
                            "file": None, "rows": 0, "bytes": 0, "sha256": None,
                            "source_url": url, "note": "no file in archive (no detections)"})
            continue
        data = z.read_entry(entry)
        (out_dir / fname).write_bytes(data)
        rows = max(data.count(b"\n") - 1, 0)
        records.append({"sensor": sensor, "year": year, "country": country,
                        "file": f"raw/{sensor}/{year}/{fname}", "rows": rows,
                        "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
                        "source_url": url})
    done_flag.write_text(json.dumps(records, indent=1))
    return records


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args(argv)
    todo = jobs()
    manifest: list[dict] = []
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(fetch_year, s, p, y, args.force): (s, y) for s, p, y in todo}
        for i, fut in enumerate(as_completed(futs), 1):
            s, y = futs[fut]
            try:
                recs = fut.result()
                manifest.extend(recs)
                rows = sum(r["rows"] for r in recs)
                print(f"[{i}/{len(todo)}] {s} {y}: {rows:,} rows ({time.time() - t0:.0f}s)", flush=True)
            except Exception as e:  # keep going; report at the end
                print(f"[{i}/{len(todo)}] {s} {y}: FAILED {e}", flush=True)
                manifest.append({"sensor": s, "year": y, "error": str(e)})
    manifest.sort(key=lambda r: (r["sensor"], r["year"], r.get("country") or ""))
    out = config.path("cache") / "manifest.json"
    out.write_text(json.dumps({"created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                               "files": manifest}, indent=1))
    failed = [r for r in manifest if "error" in r]
    print(f"Done in {time.time() - t0:.0f}s. Files: {len(manifest)}. Failed years: {len(failed)}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
