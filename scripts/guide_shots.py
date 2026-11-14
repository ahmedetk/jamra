"""Screenshots for the Arabic user guide (Edge headless), cropped by real section positions.

Each page is loaded twice at the same window size: once to read the section positions that the app
writes in ?guide=1 / ?rects=1 mode (body[data-rects]), once for the screenshot. Crops are saved in
report/shots/. The map tiles and the phone view are taken in a real browser (see report/build_guide.py).
Usage: python scripts/guide_shots.py [base_url]     (default: local preview server on port 8765)
Written with the help of an SI coding assistant (Claude Code).
"""
import html
import json
import re
import subprocess
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "report" / "shots"
PROFILE = ROOT / "report" / ".edge-profile-shots"
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
FLAGS = ["--headless=new", "--enable-webgl", "--ignore-gpu-blocklist", "--use-gl=angle", "--use-angle=swiftshader-webgl",
         "--enable-unsafe-swiftshader", "--hide-scrollbars", "--no-first-run", f"--user-data-dir={PROFILE}"]


def edge(args, timeout=150):
    try:
        return subprocess.run([EDGE, *FLAGS, *args], capture_output=True, timeout=timeout, text=True, encoding="utf-8", errors="replace")
    except subprocess.TimeoutExpired:
        subprocess.run(["powershell", "-NoProfile", "-Command",
                        "Get-CimInstance Win32_Process -Filter \"Name='msedge.exe'\" | ? { $_.CommandLine -like '*edge-profile-shots*' } | % { Stop-Process -Id $_.ProcessId -Force -EA SilentlyContinue }"],
                       capture_output=True)
        return None


def shot(name, url, w, h, crops):
    """crops: {out_name: (start_selector, end_selector or None, pad_top, pad_bottom)}"""
    r = edge([f"--window-size={w},{h}", "--virtual-time-budget=30000", "--dump-dom", url])
    rects = {}
    if r and r.stdout:
        m = re.search(r'data-rects="([^"]*)"', r.stdout)
        if m:
            rects = json.loads(html.unescape(m.group(1)))
    png = OUT / f"{name}.png"
    png.unlink(missing_ok=True)
    edge([f"--window-size={w},{h}", "--virtual-time-budget=30000", f"--screenshot={png}", url])
    if not png.exists():
        print(name, "screenshot failed"); return
    im = Image.open(png).convert("RGB")
    for out, (a, b, pt, pb) in crops.items():
        if a not in rects:
            print(" ", out, "missing", a, "in", list(rects)); continue
        top = max(0, rects[a][0] - pt)
        bottom = min(im.height, (rects[b][1] if b and b in rects else rects[a][1]) + pb)
        im.crop((0, top, w, bottom)).save(OUT / f"{out}.png")
        print(" ", out, (top, bottom))
    print(name, "ok", im.size)


def main():
    base = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8765/"
    OUT.mkdir(parents=True, exist_ok=True)
    shot("home", f"{base}?guide=1", 1280, 1300, {"g_home": ("#hero", "#tools", 0, 0)})
    shot("calendar", f"{base}calendar/?area=evia&from=2003&to=2025&month=2007-08&mode=abs&detail=1&guide=1", 1280, 4600, {
        "g_cal_chart": ("#yearly", None, 0, 0),
        "g_cal_main": ("#kpis", ".cal-card", 0, 24),
        "g_cal_detail": ("#detail", None, 8, 8),
    })
    shot("calendar_harm", f"{base}calendar/?area=greece&from=2003&to=2025&hero=harm&rects=1", 1280, 2000, {"g_harm": ("#yearly", None, 0, 0)})
    shot("anomaly", f"{base}calendar/?area=greece&from=2003&to=2025&month=2007-08&mode=anomaly&rects=1", 1280, 3400, {"g_anomaly": (".cal-card", None, 8, 8)})
    shot("alerts", f"{base}alerts/?guide=1", 1280, 1900, {"g_alerts": (".page-head", "#alerts", 0, 0)})
    shot("about", f"{base}about/?guide=1", 1280, 2600, {"g_about": (".page-head", "#about", 0, 0)})


if __name__ == "__main__":
    main()
