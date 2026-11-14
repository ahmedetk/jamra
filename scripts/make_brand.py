"""Make the Jamra brand files (rendered with Edge headless, real Inter font).

Logo: the wordmark IS the logo, lowercase "jamra" in Inter SemiBold; the dot of the j is the ember
(a solid calm-orange circle #E8833A crossed by one thin dark orbit arc). Flat: no gradients, no glow.
Files (web/public/icons/):
  wordmark-dark.png / wordmark-dark.svg    dark ink (#111827), for light backgrounds
  wordmark-white.png / wordmark-white.svg  white ink, for dark backgrounds
  favicon-16.png, favicon-32.png, apple-touch-icon.png (180), icon-192.png, icon-512.png,
  icon-maskable-512.png                    just the j with the ember dot on a white rounded square
  og-image.png                             1200x630 share image (real star sky + Blue Marble Earth)
Usage: python scripts/make_brand.py
Written with the help of an SI coding assistant (Claude Code).
"""
import base64
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_pages import logo, j_icon  # noqa: E402

PUB = ROOT / "web" / "public"
ICONS = PUB / "icons"
TMP = ROOT / "report" / ".brand"
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
FONTS = PUB / "fonts"
FONT_CSS = "".join(
    f"@font-face{{font-family:Inter;font-weight:{w};src:url('{(FONTS / f'inter-latin-{w}-normal.woff2').as_uri()}') format('woff2')}}"
    for w in (400, 600, 700))


def embedded_face(weight):
    b64 = base64.b64encode((FONTS / f"inter-latin-{weight}-normal.woff2").read_bytes()).decode()
    return f"<style>@font-face{{font-family:Inter;font-weight:{weight};src:url(data:font/woff2;base64,{b64}) format('woff2')}}</style>"


def render(name, body, w, h, bg="transparent"):
    TMP.mkdir(parents=True, exist_ok=True)
    f = TMP / f"{name}.html"
    f.write_text(f"<html><head><style>{FONT_CSS} html,body{{margin:0;width:{w}px;height:{h}px;overflow:hidden;background:{bg}}}</style></head>"
                 f"<body>{body}<script>document.fonts.ready.then(()=>document.body.dataset.ok=1)</script></body></html>", encoding="utf-8")
    subprocess.run([EDGE, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run", "--allow-file-access-from-files",
                    f"--user-data-dir={ROOT / 'report' / '.edge-profile'}", f"--window-size={w},{h}", "--virtual-time-budget=4000",
                    "--default-background-color=00000000", f"--screenshot={ICONS / name}", f.as_uri()],
                   capture_output=True, check=False, timeout=120)
    print(name, (ICONS / name).stat().st_size if (ICONS / name).exists() else "missing")


def main():
    ICONS.mkdir(parents=True, exist_ok=True)
    for old in ("icon.svg", "logo-on-blue.svg", "logo-on-white.svg", "logo-navy-256.png", "logo-white-256.png"):
        (ICONS / old).unlink(missing_ok=True)
    # scalable wordmarks with the font embedded (for the team: slides, posters, documents)
    for nm, ink in (("wordmark-dark.svg", "#111827"), ("wordmark-white.svg", "#FFFFFF")):
        svg = logo(ink=ink, height=108, font_face=embedded_face(600)).replace('<svg class="wordmark"', '<svg xmlns="http://www.w3.org/2000/svg"', 1)
        (ICONS / nm).write_text(svg, encoding="utf-8")
    # raster wordmarks (transparent)
    for nm, ink in (("wordmark-dark.png", "#111827"), ("wordmark-white.png", "#FFFFFF")):
        render(nm, logo(ink=ink, height=240), 618, 240)
    # app icons: just the j with the ember dot
    for nm, size, kw in (("favicon-16.png", 16, {"pad": 0.04, "radius": 0.18, "bold": 9}), ("favicon-32.png", 32, {"pad": 0.07, "bold": 5}),
                         ("apple-touch-icon.png", 180, {"radius": 0}), ("icon-192.png", 192, {}), ("icon-512.png", 512, {}),
                         ("icon-maskable-512.png", 512, {"radius": 0, "pad": 0.27})):
        render(nm, j_icon(size=size, **kw), size, size)
    # share image: real star sky, Blue Marble Earth, white wordmark and the headline
    stars = (PUB / "img" / "space-stars.webp").as_uri()
    earth = (PUB / "img" / "earth-blue-marble.png").as_uri()
    og = f"""<div style="position:relative;width:1200px;height:630px;background:#03050A url('{stars}') center/cover;font-family:Inter;color:#fff">
<img src="{earth}" style="position:absolute;right:-150px;top:15px;width:600px;height:600px">
<div style="position:absolute;left:80px;top:78px">{logo(ink='#FFFFFF', height=92)}</div>
<div style="position:absolute;left:84px;top:250px;width:640px;font:700 58px/1.12 Inter;letter-spacing:-.02em">20 years of NASA fire data. One fair calendar.</div>
<div style="position:absolute;left:84px;top:500px;font:400 24px Inter;color:#D1D5DB">MODIS + VIIRS · live early warning · Data: NASA FIRMS</div>
</div>"""
    render("og-image.png", og, 1200, 630, bg="#03050A")


if __name__ == "__main__":
    main()
