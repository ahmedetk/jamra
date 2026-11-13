"""Static real-Earth image (globe fallback) from NASA GIBS Blue Marble tiles.

Downloads zoom-3 tiles of BlueMarble_ShadedRelief_Bathymetry (GoogleMapsCompatible_Level8),
stitches a world mosaic and projects it to an orthographic globe centred on the Mediterranean,
with gentle limb shading and a thin, subtle atmosphere. Imagery: NASA GIBS / Blue Marble.
Usage: python scripts/make_earth.py
Written with the help of an SI coding assistant (Claude Code).
"""
import io
import math
import urllib.request
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT.parent / "cache" / "gibs"
OUT = ROOT / "web" / "public" / "img"
URL = "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/BlueMarble_ShadedRelief_Bathymetry/default/GoogleMapsCompatible_Level8/{z}/{y}/{x}.jpeg"
Z = 3


def mosaic():
    CACHE.mkdir(parents=True, exist_ok=True)
    n = 2 ** Z
    img = Image.new("RGB", (256 * n, 256 * n))
    for y in range(n):
        for x in range(n):
            f = CACHE / f"{Z}_{y}_{x}.jpeg"
            if not f.exists():
                req = urllib.request.Request(URL.format(z=Z, y=y, x=x), headers={"User-Agent": "jamra/1.0"})
                for attempt in range(6):
                    try:
                        f.write_bytes(urllib.request.urlopen(req, timeout=90).read())
                        break
                    except OSError:
                        if attempt == 5:
                            raise
            img.paste(Image.open(io.BytesIO(f.read_bytes())).convert("RGB"), (256 * x, 256 * y))
    return img


def globe(src, size=720, lat0=34.0, lon0=18.0):
    W, H = src.size
    px = src.load()
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    po = out.load()
    R = size * 0.46
    cx = cy = size / 2
    la0, lo0 = math.radians(lat0), math.radians(lon0)
    for j in range(size):
        for i in range(size):
            u, v = (i - cx) / R, (cy - j) / R
            d2 = u * u + v * v
            if d2 <= 1.0:
                zz = math.sqrt(1 - d2)
                lat = math.asin(max(-1, min(1, zz * math.sin(la0) + v * math.cos(la0))))
                lon = lo0 + math.atan2(u, zz * math.cos(la0) - v * math.sin(la0))
                lat = max(-1.48, min(1.48, lat))
                X = ((math.degrees(lon) + 180) % 360) / 360 * W
                Y = (1 - math.log(math.tan(lat) + 1 / math.cos(lat)) / math.pi) / 2 * H
                r, g, b = px[min(W - 1, int(X)), min(H - 1, max(0, int(Y)))]
                shade = 0.62 + 0.38 * zz ** 0.6           # gentle limb darkening
                po[i, j] = (int(r * shade), int(g * shade), int(b * shade), 255)
            else:
                d = math.sqrt(d2)
                if d < 1.03:                               # thin, subtle atmosphere
                    a = int(40 * (1 - (d - 1) / 0.03) ** 2.2)
                    po[i, j] = (140, 185, 255, a)
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    g = globe(mosaic())
    g.save(OUT / "earth-blue-marble.webp", quality=88)
    g.save(OUT / "earth-blue-marble.png", optimize=True)
    print("saved", [(p.name, p.stat().st_size) for p in OUT.glob("earth-blue-marble.*")])


if __name__ == "__main__":
    main()
