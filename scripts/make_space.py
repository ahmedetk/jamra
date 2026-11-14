"""Space assets for the Home hero: a real star sky and the Earth texture.

1. Star sky: every naked-eye star of the Yale Bright Star Catalogue (BSC5, via NASA HEASARC) in one
   region of the real sky (around Orion and Taurus), drawn at its true position, brightness (V mag)
   and colour (B-V). No invented stars, no nebula effects. Credit: "Stars: Yale Bright Star Catalogue (NASA HEASARC)".
2. Earth texture: NASA GIBS Blue Marble (shaded relief + bathymetry), one equirectangular image
   (EPSG:4326 WMS GetMap), saved at 4096 and 2048 px. Credit: "Imagery: NASA GIBS / Blue Marble".

Inputs are cached in ../cache/assets (see the download commands in the repo history).
Usage: python scripts/make_space.py
Written with the help of an SI coding assistant (Claude Code).
"""
import gzip
import math
from pathlib import Path

from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT.parent / "cache" / "assets"
OUT = ROOT / "web" / "public" / "img"


def stars():
    rows, fields = [], None
    with gzip.open(CACHE / "bsc5p.tdat.gz", "rt", encoding="latin-1") as f:
        data = False
        for line in f:
            if line.startswith("line[1]"):
                fields = line.split("=", 1)[1].split()
            elif line.startswith("<DATA>"):
                data = True
            elif line.startswith("<END>"):
                break
            elif data and fields:
                v = dict(zip(fields, line.rstrip("\n").split("|")))
                try:
                    rows.append((float(v["ra"]), float(v["dec"]), float(v["vmag"]), float(v["bv_color"] or 0.6)))
                except (ValueError, KeyError):
                    pass
    return rows


def bv_rgb(bv):
    """Approximate star colour from B-V (blue-white to orange), kept gentle."""
    bv = max(-0.4, min(2.0, bv))
    t = (bv + 0.4) / 2.4
    r = 0.80 + 0.20 * min(1, t * 1.6)
    g = 0.86 - 0.10 * t
    b = 1.00 - 0.42 * t
    return r, g, b


def star_sky(W=2560, H=1280, ra0=80.0, dec0=8.0, width_deg=110.0):
    """Gnomonic (camera-like) projection of a sky region centred on (ra0, dec0)."""
    scale = W / (2 * math.tan(math.radians(width_deg / 2)))
    acc = [[0.0, 0.0, 0.0] for _ in range(W * H)]
    a0, d0 = math.radians(ra0), math.radians(dec0)
    n = 0
    for ra, dec, vmag, bv in stars():
        a, d = math.radians(ra), math.radians(dec)
        cosc = math.sin(d0) * math.sin(d) + math.cos(d0) * math.cos(d) * math.cos(a - a0)
        if cosc <= 0.2:
            continue
        x = math.cos(d) * math.sin(a - a0) / cosc
        y = (math.cos(d0) * math.sin(d) - math.sin(d0) * math.cos(d) * math.cos(a - a0)) / cosc
        px, py = W / 2 - x * scale, H / 2 - y * scale          # sky seen from inside: east to the left
        if not (-4 <= px < W + 4 and -4 <= py < H + 4):
            continue
        flux = 10 ** (-0.4 * (vmag - 1.0))                      # relative brightness
        peak = min(1.0, 0.24 + 0.6 * flux ** 0.5)              # compressed so bright stars stay small
        sigma = 0.55 + 0.75 * min(1.0, flux ** 0.35)
        cr, cg, cb = bv_rgb(bv)
        rad = int(math.ceil(sigma * 3))
        for j in range(int(py) - rad, int(py) + rad + 1):
            if not 0 <= j < H:
                continue
            for i in range(int(px) - rad, int(px) + rad + 1):
                if not 0 <= i < W:
                    continue
                w = peak * math.exp(-((i - px) ** 2 + (j - py) ** 2) / (2 * sigma * sigma))
                c = acc[j * W + i]
                c[0] += w * cr; c[1] += w * cg; c[2] += w * cb
        n += 1
    img = Image.new("RGB", (W, H))
    base = (3, 5, 9)                                            # deep black, very slightly blue
    img.putdata([tuple(min(255, int(base[k] + 255 * c[k] * 0.92)) for k in range(3)) for c in acc])
    print("stars drawn:", n)
    return img


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    sky = star_sky()
    sky.save(OUT / "space-stars.webp", quality=82, method=6)
    sky.resize((1280, 640), Image.LANCZOS).save(OUT / "space-stars-1280.webp", quality=82, method=6)
    bm = Image.open(CACHE / "bluemarble_4326_4096.jpg").convert("RGB")
    bm.save(OUT / "earth-texture-4096.webp", quality=86, method=6)
    bm.resize((2048, 1024), Image.LANCZOS).filter(ImageFilter.UnsharpMask(1, 40, 2)).save(OUT / "earth-texture-2048.webp", quality=86, method=6)
    for p in sorted(OUT.glob("space-*")) + sorted(OUT.glob("earth-texture-*")):
        print(p.name, p.stat().st_size)


if __name__ == "__main__":
    main()
