"""Make the Jamra brand files (rendered with Edge headless, real Inter font).

Logo: the wordmark IS the logo, lowercase "jamra" in Playfair Display Bold; the dot of the j is the ember
(a vivid orange circle #F4511E with one thin orbit arc and a small spark). Flat: no gradients, no glow.
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
    for w in (400, 600, 700)) + "".join(
    f"@font-face{{font-family:'Playfair Display';font-weight:{w};src:url('{(FONTS / f'playfair-display-latin-{w}-normal.woff2').as_uri()}') format('woff2')}}"
    for w in (700,))


def embedded_face(weight):
    b64 = base64.b64encode((FONTS / f"playfair-display-latin-{weight}-normal.woff2").read_bytes()).decode()
    return f"<style>@font-face{{font-family:'Playfair Display';font-weight:{weight};src:url(data:font/woff2;base64,{b64}) format('woff2')}}</style>"


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
    for nm, ink in (("wordmark-dark.svg", "#2B2B2B"), ("wordmark-white.svg", "#FFFFFF")):
        svg = logo(ink=ink, height=116, font_face=embedded_face(700)).replace('<svg class="wordmark"', '<svg xmlns="http://www.w3.org/2000/svg"', 1)
        (ICONS / nm).write_text(svg, encoding="utf-8")
    # raster wordmarks (transparent)
    for nm, ink in (("wordmark-dark.png", "#2B2B2B"), ("wordmark-white.png", "#FFFFFF")):
        render(nm, logo(ink=ink, height=240), 592, 240)
    # app icons: just the j with the ember dot
    for nm, size, kw in (("favicon-16.png", 16, {"pad": 0.03, "bold": 9, "sparks": False}), ("favicon-32.png", 32, {"pad": 0.06, "bold": 5, "sparks": False}),
                         ("apple-touch-icon.png", 180, {"radius": 0}), ("icon-192.png", 192, {}), ("icon-512.png", 512, {}),
                         ("icon-maskable-512.png", 512, {"radius": 0, "pad": 0.26})):
        render(nm, j_icon(size=size, **kw), size, size)
    # share image: warm palette, the light half globe rising from the bottom right, wordmark and the headline
    earth = (PUB / "img" / "earth-light.png").as_uri()
    wm = (ICONS / "wordmark-dark.png").as_uri()
    og = f"""<div style="position:relative;width:1200px;height:630px;overflow:hidden;background:linear-gradient(180deg,#F7F6F2,#EFEEE9);font-family:Inter;color:#2B2B2B">
<img src="{earth}" style="position:absolute;right:-230px;bottom:-470px;width:960px;height:960px">
<img src="{wm}" style="position:absolute;left:80px;top:70px;height:96px">
<div style="position:absolute;left:84px;top:230px;width:600px;font:700 62px/1.06 'Playfair Display';letter-spacing:-.01em">20 years of NASA fire data. One fair calendar.</div>
<div style="position:absolute;left:84px;top:520px;font:500 22px Inter;color:#6B6A66;letter-spacing:.03em">MODIS + VIIRS · live early warning · Data: NASA FIRMS</div>
<div style="position:absolute;left:84px;top:500px;width:64px;height:3px;background:#F4511E"></div>
</div>"""
    render("og-image.png", og, 1200, 630, bg="#EFEEE9")


if __name__ == "__main__":
    main()
