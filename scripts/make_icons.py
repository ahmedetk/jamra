"""Make the PWA icons (PNG) with pure Python. Written with an SI coding assistant (Claude Code)."""
import math
import struct
import zlib
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "web" / "public" / "icons"
NAVY, EMBER, GLOW = (20, 33, 61), (255, 122, 48), (255, 196, 92)


def flame(x, y):
    """Signed test: inside a teardrop flame centred in a unit square."""
    cx, cy, r = 0.5, 0.62, 0.22
    if (x - cx) ** 2 + (y - cy) ** 2 <= r * r:
        return True
    # upper tip: triangle-ish curve from circle to tip at (0.5, 0.14)
    if 0.14 <= y <= cy:
        t = (cy - y) / (cy - 0.14)
        half = r * math.cos(t * math.pi / 2) ** 1.2
        return abs(x - cx + 0.04 * math.sin(t * math.pi)) <= half
    return False


def inner(x, y):
    cx, cy, r = 0.5, 0.68, 0.11
    if (x - cx) ** 2 + (y - cy) ** 2 <= r * r:
        return True
    if 0.42 <= y <= cy:
        t = (cy - y) / (cy - 0.42)
        return abs(x - cx) <= r * math.cos(t * math.pi / 2)
    return False


def png(size: int, path: Path, maskable: bool = False):
    rows = []
    s = 4  # supersampling
    for py in range(size):
        row = bytearray([0])
        for px in range(size):
            acc = [0, 0, 0]
            for sy in range(s):
                for sx in range(s):
                    x = (px + (sx + 0.5) / s) / size
                    y = (py + (sy + 0.5) / s) / size
                    if maskable:  # keep the flame inside the safe zone
                        x, y = 0.5 + (x - 0.5) / 0.8, 0.5 + (y - 0.5) / 0.8
                    c = GLOW if inner(x, y) else EMBER if flame(x, y) else NAVY
                    for k in range(3):
                        acc[k] += c[k]
            row += bytes(v // (s * s) for v in acc)
        rows.append(bytes(row))
    raw = b"".join(rows)

    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)

    data = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0)) \
        + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")
    path.write_bytes(data)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    png(192, OUT / "icon-192.png")
    png(512, OUT / "icon-512.png")
    png(512, OUT / "icon-maskable-512.png", maskable=True)
    (OUT / "icon.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="14" fill="#14213d"/>'
        '<path d="M32 9c3 9 14 15 14 28a14 14 0 0 1-28 0c0-7 3-11 5-14 2 5 4 7 7 7-2-7 0-15 2-21z" fill="#ff7a30"/>'
        '<path d="M32 30c2 4 6 6 6 11a6 6 0 0 1-12 0c0-3 2-5 3-6 1 2 2 3 3 3-1-3 0-6 0-8z" fill="#ffc45c"/></svg>')
    print("icons written to", OUT)
