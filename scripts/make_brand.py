"""Make the Jamra logo files, PWA icons, favicon and og-image (rendered with Edge headless).

Logo: a flat ember flame with one orbit ring. Two versions: white ring on blue, navy ring on white.
Usage: python scripts/make_brand.py
Written with the help of an SI coding assistant (Claude Code).
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_pages import logo  # noqa: E402

PUB = ROOT / "web" / "public"
ICONS = PUB / "icons"
TMP = ROOT / "report" / ".brand"
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
FONT = (PUB / "fonts").as_uri()


def mark_svg(ring, size):
    return logo(ring=ring, size=size)


def render(name, html, w, h):
    TMP.mkdir(parents=True, exist_ok=True)
    f = TMP / f"{name}.html"
    f.write_text(html, encoding="utf-8")
    subprocess.run([EDGE, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run",
                    f"--user-data-dir={ROOT / 'report' / '.edge-profile'}", f"--window-size={w},{h}",
                    "--default-background-color=00000000", f"--screenshot={ICONS / name}", f.as_uri()],
                   capture_output=True, check=False)
    print(name, (ICONS / name).stat().st_size if (ICONS / name).exists() else "missing")


def icon_page(size, inset, radius):
    m = int(size * (1 - 2 * inset))
    return f"""<html><body style="margin:0;width:{size}px;height:{size}px;overflow:hidden">
<div style="width:{size}px;height:{size}px;border-radius:{radius}px;background:linear-gradient(135deg,#0B1D51,#1F4FD8);display:grid;place-items:center">
{mark_svg('#FFFFFF', m)}</div></body></html>"""


def main():
    ICONS.mkdir(parents=True, exist_ok=True)
    # scalable files
    (ICONS / "logo-on-blue.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48"><rect width="48" height="48" rx="10" fill="#0B1D51"/>'
        + mark_svg("#FFFFFF", 48).split(">", 1)[1].replace("</svg>", "") + "</svg>", encoding="utf-8")
    (ICONS / "logo-on-white.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48">'
        + mark_svg("#0B1D51", 48).split(">", 1)[1].replace("</svg>", "") + "</svg>", encoding="utf-8")
    (ICONS / "icon.svg").write_text((ICONS / "logo-on-blue.svg").read_text(encoding="utf-8"), encoding="utf-8")
    render("icon-192.png", icon_page(192, 0.1, 40), 192, 192)
    render("icon-512.png", icon_page(512, 0.1, 108), 512, 512)
    render("icon-maskable-512.png", icon_page(512, 0.22, 0), 512, 512)
    render("favicon-32.png", icon_page(32, 0.04, 7), 32, 32)
    og = f"""<html><head><style>
@font-face {{ font-family: J; src: url('{FONT}/plus-jakarta-sans-latin-800-normal.woff2'); font-weight: 800; }}
@font-face {{ font-family: I; src: url('{FONT}/inter-latin-400-normal.woff2'); }}
</style></head><body style="margin:0;width:1200px;height:630px;overflow:hidden;background:linear-gradient(120deg,#0B1D51,#12307F 55%,#1F4FD8);color:#fff;font-family:I,sans-serif;position:relative">
<div style="position:absolute;width:900px;height:900px;border:1px solid rgba(255,255,255,.1);border-radius:50%;right:-300px;top:-150px"></div>
<div style="position:absolute;width:1200px;height:1200px;border:1px solid rgba(255,255,255,.08);border-radius:50%;right:-450px;top:-300px"></div>
<div style="position:absolute;left:80px;top:80px;display:flex;align-items:center;gap:18px;font:800 54px J">{mark_svg('#FFFFFF', 80)}Jamra</div>
<div style="position:absolute;left:80px;top:220px;width:820px;font:800 58px/1.12 J">Did fires really increase — or did our satellites get sharper eyes?</div>
<div style="position:absolute;left:80px;top:480px;font-size:26px;color:#DBEAFE">20+ years of NASA MODIS + VIIRS fire data in one fair calendar · Data: NASA FIRMS</div>
</body></html>"""
    render("og-image.png", og, 1200, 630)


if __name__ == "__main__":
    main()
