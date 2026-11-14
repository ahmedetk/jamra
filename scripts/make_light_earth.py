"""Light cartographic Earth (Design v4): the same colours as our light detail map.

Warm light-grey land, soft blue-grey water, thin light country borders, drawn from Natural Earth
1:50m admin-0 countries (public domain), cached in ../cache/assets/ne_50m_admin_0_countries.geojson.
Outputs (web/public/img/):
  earth-light-4096.webp, earth-light-2048.webp   equirectangular textures for the three.js globe
  earth-light.webp / earth-light.png             a static orthographic globe (fallback, og-image, guide, slides)
Usage: python scripts/make_light_earth.py
Written with the help of an SI coding assistant (Claude Code).
"""
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT.parent / "cache" / "assets" / "ne_50m_admin_0_countries.geojson"
OUT = ROOT / "web" / "public" / "img"
LAND = (243, 241, 235)      # #F3F1EB (same as the map land)
WATER = (183, 202, 219)     # #B7CADB (soft blue, map water)
BORDER = (206, 202, 193)    # thin light borders
COAST = (160, 182, 202)     # slightly deeper blue at the coast, for a crisp edge


def polygons():
    gj = json.loads(SRC.read_text(encoding="utf-8"))
    for f in gj["features"]:
        g = f["geometry"]
        polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
        for poly in polys:
            yield poly


def texture(W=8192):
    H = W // 2
    img = Image.new("RGB", (W, H), WATER)
    d = ImageDraw.Draw(img)
    P = lambda lon, lat: ((lon + 180) / 360 * W, (90 - lat) / 180 * H)
    polys = list(polygons())
    for poly in polys:                               # land
        d.polygon([P(*c) for c in poly[0]], fill=LAND)
        for hole in poly[1:]:
            d.polygon([P(*c) for c in hole], fill=WATER)
    lw = max(1, W // 4096)
    for poly in polys:                               # coast + borders
        ring = [P(*c) for c in poly[0]]
        d.line(ring + [ring[0]], fill=BORDER, width=lw)
    return img


def ortho(src, size=720, lat0=34.0, lon0=18.0):
    W, H = src.size
    px = src.load()
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    po = out.load()
    R = size * 0.47
    c = size / 2
    la0, lo0 = math.radians(lat0), math.radians(lon0)
    for j in range(size):
        for i in range(size):
            u, v = (i - c) / R, (c - j) / R
            d2 = u * u + v * v
            if d2 <= 1:
                z = math.sqrt(1 - d2)
                lat = math.asin(max(-1, min(1, z * math.sin(la0) + v * math.cos(la0))))
                lon = lo0 + math.atan2(u, z * math.cos(la0) - v * math.sin(la0))
                X = ((math.degrees(lon) + 180) % 360) / 360 * W
                Y = (90 - math.degrees(lat)) / 180 * H
                r, g, b = px[min(W - 1, int(X)), min(H - 1, int(Y))]
                s = 0.86 + 0.14 * z ** 0.5                  # very gentle shading toward the limb
                po[i, j] = (int(r * s), int(g * s), int(b * s), 255)
            elif d2 < 1.0045:                               # thin crisp outline
                po[i, j] = (*COAST, 160)
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    big = texture(8192)
    t4 = big.resize((4096, 2048), Image.LANCZOS)
    t4.save(OUT / "earth-light-4096.webp", quality=88, method=6)
    t2 = big.resize((2048, 1024), Image.LANCZOS)
    t2.save(OUT / "earth-light-2048.webp", quality=88, method=6)
    g = ortho(t2, 720)
    g.save(OUT / "earth-light.webp", quality=90, method=6)
    g.save(OUT / "earth-light.png", optimize=True)
    for p in sorted(OUT.glob("earth-light*")):
        print(p.name, p.stat().st_size)


if __name__ == "__main__":
    main()
