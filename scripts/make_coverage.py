"""Coverage outline for the map: the 8 countries of the Jamra archive, from Natural Earth 1:50m (public domain).

Writes web/public/data/coverage.json (GeoJSON, lightly simplified). The app draws it on the map and uses it to
tell users when a drawn area is outside the archive.
Usage: python scripts/make_coverage.py
Written with the help of an AI coding assistant (Claude Code by Anthropic).
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT.parent / "cache" / "assets" / "ne_50m_admin_0_countries.geojson"
OUT = ROOT / "web" / "public" / "data" / "coverage.json"
NAMES = {"Portugal", "Spain", "Greece", "Turkey", "Cyprus", "Northern Cyprus", "Lebanon", "Jordan", "Palestine"}


def simplify(ring, tol=0.03):
    out = []
    for lon, lat in ring:
        p = [round(lon, 3), round(lat, 3)]
        if not out or abs(p[0] - out[-1][0]) + abs(p[1] - out[-1][1]) >= tol:
            out.append(p)
    if out[0] != out[-1]:
        out.append(out[0])
    return out if len(out) >= 4 else None


def main():
    gj = json.loads(SRC.read_text(encoding="utf-8"))
    feats = []
    for f in gj["features"]:
        name = f["properties"].get("ADMIN")
        if name not in NAMES:
            continue
        g = f["geometry"]
        polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
        rings = [simplify(poly[0]) for poly in polys]
        rings = [[r] for r in rings if r]
        feats.append({"type": "Feature", "properties": {"name": "Türkiye" if name == "Turkey" else name},
                      "geometry": {"type": "MultiPolygon", "coordinates": rings}})
    OUT.write_text(json.dumps({"type": "FeatureCollection", "features": feats}, separators=(",", ":")), encoding="utf-8")
    print(OUT.name, len(feats), "countries", OUT.stat().st_size, "bytes", sorted(f["properties"]["name"] for f in feats))


if __name__ == "__main__":
    main()
