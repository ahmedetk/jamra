"""Build slides/AstroByte_Slides.pptx (7 slides, 16:9, editable, speaker notes).

Every number comes from data/processed/slide_numbers.json (made by
scripts/story_numbers.py from the pipeline outputs). Run scripts/check_numbers.py after.
Usage: python slides/build_slides.py --url https://<site>
Written with the help of an SI coding assistant (Claude Code), following Team Astro Byte's story.
"""
import argparse
import io
import json
from pathlib import Path

import qrcode
from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION, XL_LABEL_POSITION
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.util import Inches, Pt, Emu

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web" / "public" / "data"
N = json.loads((ROOT / "data" / "processed" / "slide_numbers.json").read_text(encoding="utf-8"))

NAVY = RGBColor(0x11, 0x18, 0x27)   # charcoal
INK2 = RGBColor(0x3D, 0x4A, 0x63)
MUTED = RGBColor(0x5F, 0x6B, 0x80)
EMBER = RGBColor(0xFF, 0x7A, 0x33)  # soft orange
BG = RGBColor(0xFF, 0xFF, 0xFF)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
GREY = RGBColor(0xAD, 0xB5, 0xBD)
BLUE = RGBColor(0x1F, 0x4F, 0xD8)
LINE = RGBColor(0xD9, 0xDE, 0xE7)
FONT = "Arial"
SOURCE = "Data: NASA FIRMS (MODIS C6.1 Aqua, VIIRS 375 m S-NPP / NOAA-20), standard processing 2003–2025. Analysis: Jamra."
used = {}  # numbers that appear on slides -> checked by scripts/check_numbers.py


def u(key, text):
    used[key] = text
    return text


def fmt(n):
    return f"{n:,}"


def tb(slide, x, y, w, h, text, size=18, bold=False, color=NAVY, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, font=FONT):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = Inches(0.04)
    lines = text if isinstance(text, list) else [text]
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        runs = line if isinstance(line, list) else [(line, {})]
        for r_text, style in runs:
            r = p.add_run()
            r.text = r_text
            r.font.name = font
            r.font.size = Pt(style.get("size", size))
            r.font.bold = style.get("bold", bold)
            r.font.color.rgb = style.get("color", color)
    return box


def rect(slide, x, y, w, h, fill, line=None, shape=MSO_SHAPE.RECTANGLE, radius=None):
    s = slide.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
    s.fill.solid()
    s.fill.fore_color.rgb = fill
    if line is None:
        s.line.fill.background()
    else:
        s.line.color.rgb = line
        s.line.width = Pt(1)
    if radius is not None and shape == MSO_SHAPE.ROUNDED_RECTANGLE:
        s.adjustments[0] = radius
    s.shadow.inherit = False
    return s


def base(prs, n, headline, notes, speaker, source=True):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    s.background.fill.solid()
    s.background.fill.fore_color.rgb = BG
    rect(s, 0, 0, 13.333, 0.1, NAVY)
    logo = ROOT / 'web' / 'public' / 'icons' / 'logo-navy-256.png'
    if logo.exists() and n != 1:
        s.shapes.add_picture(str(logo), Inches(12.45), Inches(0.28), width=Inches(0.42))
    tb(s, 0.55, 0.32, 12.2 if n == 1 else 11.6, 1.25, headline, size=28 if len(headline) < 105 else 23, bold=True)
    tb(s, 0.55, 7.05, 8.5, 0.3, "Team Astro Byte · NASA Space Apps Challenge 2026 · Harmonization of MODIS and VIIRS Hot Spots", size=9, color=MUTED)
    tb(s, 12.3, 7.05, 0.5, 0.3, str(n), size=10, color=MUTED, align=PP_ALIGN.RIGHT)
    if source:
        tb(s, 0.55, 6.78, 12.2, 0.3, SOURCE, size=9, color=MUTED)
    s.notes_slide.notes_text_frame.text = f"Speaker: {speaker}\n\n{notes}"
    return s


def yearly(area_id):
    a = json.loads((WEB / "areas" / f"{area_id}.json").read_text(encoding="utf-8"))
    y0 = int(a["start"][:4])
    out = []
    for y in range(2003, 2026):
        i = (y - y0) * 12
        raw = sum(v for v in (a["series"]["A"] if y < 2012 else a["series"]["N"])[i:i + 12] if v is not None)
        harm = sum(v for v in a["harm"][i:i + 12] if v is not None)
        out.append((y, raw, round(harm)))
    return out, a


def style_chart(chart, legend=True, size=11):
    chart.font.name = FONT
    chart.font.size = Pt(size)
    chart.font.color.rgb = INK2
    chart.has_legend = legend
    if legend:
        chart.legend.position = XL_LEGEND_POSITION.TOP
        chart.legend.include_in_layout = False
        chart.legend.font.size = Pt(size)


def jump_chart(slide, x, y, w, h, area_id="greece", size=11):
    rows, _ = yearly(area_id)
    cd = CategoryChartData()
    cd.categories = [str(r[0]) for r in rows]
    cd.add_series("Harmonized (VIIRS-equivalent)", [r[2] for r in rows])
    cd.add_series("Raw (MODIS until 2011, then VIIRS)", [r[1] for r in rows])
    gf = slide.shapes.add_chart(XL_CHART_TYPE.LINE_MARKERS, Inches(x), Inches(y), Inches(w), Inches(h), cd)
    ch = gf.chart
    style_chart(ch, size=size)
    colors = [NAVY, EMBER]
    for s, c in zip(ch.series, colors):
        s.format.line.color.rgb = c
        s.format.line.width = Pt(3 if c == NAVY else 2.5)
        s.marker.format.fill.solid()
        s.marker.format.fill.fore_color.rgb = c
        s.marker.format.line.color.rgb = c
        s.smooth = False
    ch.series[0].format.line.width = Pt(4.5)
    va = ch.value_axis
    va.has_major_gridlines = True
    va.major_gridlines.format.line.color.rgb = LINE
    va.tick_labels.font.size = Pt(size - 1)
    ch.category_axis.tick_labels.font.size = Pt(size - 1)
    return ch


def qr_png(url):
    img = qrcode.make(url, border=1)
    bio = io.BytesIO()
    img.save(bio)
    bio.seek(0)
    return bio


def build(url, out_path, screenshot=None):
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    gj, pj = N["greece_jump"], N["portugal_jump"]
    st = N["stories"]
    g07, g21, g23 = st["greece_2007_08"], st["greece_2021_08"], st["greece_2023_08"]

    # ------------------------------------------------------------------ 1 title
    s = base(prs, 1, "Jamra: one fair fire record from two satellites, with live early warning",
             speaker="Shahd Farraj", source=False, notes=(
                 "Hello, we are Team Astro Byte and this is Jamra, which means ember in Arabic. "
                 "Satellites have watched fires for more than twenty years, but the record is split between an older sensor, MODIS, "
                 "and a sharper one, VIIRS. If you simply join them, in Greece the "
                 f"number of hotspots jumps about {gj['raw_ratio']} times after 2012. In our harmonized record the fake jump is gone, "
                 "and the real disasters, like 2007, 2021 and 2023, stand out. In the next minutes we show how we built it, "
                 "how well it works, and how it warns people live."))
    # dark title slide with the real Earth (NASA Blue Marble via GIBS)
    s.background.fill.solid(); s.background.fill.fore_color.rgb = RGBColor(0x07, 0x0A, 0x12)
    for shp in list(s.shapes):
        if shp.has_text_frame and shp.text_frame.text.startswith("Jamra: one fair"):
            for para in shp.text_frame.paragraphs:
                for r in para.runs: r.font.color.rgb = WHITE
        elif shp.has_text_frame and ("Team Astro Byte ·" in shp.text_frame.text or shp.text_frame.text.strip() == "1"):
            for para in shp.text_frame.paragraphs:
                for r in para.runs: r.font.color.rgb = RGBColor(0x94, 0xA3, 0xB8)
    earth = ROOT / "web" / "public" / "img" / "earth-blue-marble.png"
    if earth.exists():
        s.shapes.add_picture(str(earth), Inches(7.6), Inches(1.0), width=Inches(6.3))
        tb(s, 10.2, 7.05, 2.0, 0.3, "Imagery: NASA GIBS / Blue Marble", size=8, color=RGBColor(0x94, 0xA3, 0xB8))
    logo = ROOT / "web" / "public" / "icons" / "logo-white-256.png"
    if logo.exists():
        s.shapes.add_picture(str(logo), Inches(0.55), Inches(1.55), width=Inches(0.62))
    tb(s, 1.25, 1.6, 4, 0.6, "Jamra", size=28, bold=True, color=WHITE)
    LIGHT = RGBColor(0xCB, 0xD5, 0xE1)
    tb(s, 0.55, 2.4, 6.6, 0.5, "Challenge: Harmonization of MODIS and VIIRS Hot Spots", size=16, color=LIGHT)
    tb(s, 0.55, 2.95, 6.6, 1.6, [
        [("Team Astro Byte", {"bold": True, "size": 16, "color": WHITE})],
        [("Shahd Farraj · Ahmed Etkaidek · Aya Salman", {"size": 14, "color": LIGHT})],
        [("Ahmad Akhras · Tala Yousef", {"size": 14, "color": LIGHT})],
    ])
    tb(s, 0.55, 4.45, 6.6, 1.2, [
        [("Raw record: ", {"bold": True, "color": EMBER, "size": 15}), (u("g_raw", f"{gj['raw_ratio']}×") + " more hotspots after 2012 in Greece.", {"size": 15, "color": WHITE})],
        [("Harmonized: ", {"bold": True, "size": 15, "color": RGBColor(0x93, 0xC5, 0xFD)}), (u("g_harm", f"{gj['harm_ratio']}×") + ". The fake rise disappears.", {"size": 15, "color": WHITE})],
    ])
    tb(s, 0.55, 6.25, 7.0, 0.6, [[("Built for the NASA Space Apps Challenge 2026 · Local event by NOVA · Data: NASA FIRMS · Not an official NASA product", {"size": 10, "color": RGBColor(0x94, 0xA3, 0xB8)})]])

    # ------------------------------------------------------------------ 2 problem
    s = base(prs, 2, "Joining MODIS and VIIRS raw creates a fake rise in fires after 2012, and the old satellites are retiring",
             speaker="Shahd Farraj", notes=(
                 f"Here is the problem in one number. For the same fires, VIIRS records about {N['k_global']} times more hotspots than MODIS, "
                 "because its pixels are 375 metres wide instead of one kilometre. So anyone who joins the two records raw sees fires "
                 f"suddenly multiply after 2012: about {gj['raw_ratio']} times in Greece and {pj['raw_ratio']} times in Portugal. "
                 "That misleads the people who plan with fire history: emergency managers and early-warning teams, firefighting teams, "
                 "land and forest managers, and scientists. Through them, village councils, municipalities and farmers benefit too. "
                 "And it is urgent: MODIS is near the end of its life, and NASA stopped the S-NPP VIIRS data stream on 2 November 2026, "
                 "so a fair, continuous record is needed now."))
    rect(s, 0.55, 1.65, 4.6, 4.3, WHITE, line=LINE, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.06)
    tb(s, 0.75, 1.85, 4.2, 1.6, u("k_global", f"{N['k_global']}×"), size=88, bold=True, color=EMBER, align=PP_ALIGN.CENTER)
    tb(s, 0.75, 3.55, 4.2, 2.2, [
        [("more hotspots seen by VIIRS than MODIS for the same fires", {"size": 17, "bold": True})],
        [("VIIRS S-NPP ÷ MODIS Aqua, all hotspots, 8 countries, calibration years 2012–2025", {"size": 12, "color": MUTED})],
    ], align=PP_ALIGN.CENTER)
    # bars: raw jump
    cd = CategoryChartData()
    cd.categories = ["Greece", "Portugal"]
    cd.add_series("Raw: after 2012 ÷ before", [gj["raw_ratio"], pj["raw_ratio"]])
    cd.add_series("Harmonized: after ÷ before", [gj["harm_ratio"], pj["harm_ratio"]])
    gf = s.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(5.5), Inches(1.6), Inches(4.2), Inches(4.4), cd)
    ch = gf.chart
    style_chart(ch, size=11)
    ch.series[0].format.fill.solid(); ch.series[0].format.fill.fore_color.rgb = EMBER
    ch.series[1].format.fill.solid(); ch.series[1].format.fill.fore_color.rgb = NAVY
    pl = ch.plots[0]
    pl.has_data_labels = True
    pl.data_labels.number_format = '0.0"×"'
    pl.data_labels.number_format_is_linked = False
    pl.data_labels.position = XL_LABEL_POSITION.OUTSIDE_END
    pl.data_labels.font.size = Pt(12)
    ch.value_axis.visible = False
    ch.value_axis.has_major_gridlines = False
    u("p_raw", f"{pj['raw_ratio']}"); u("p_harm", f"{pj['harm_ratio']}")
    # users
    tb(s, 10.0, 1.6, 2.9, 0.4, "Who we serve", size=15, bold=True)
    tb(s, 10.0, 5.95, 3.0, 0.7, "Also benefit: village councils, municipalities, farmers (via local authorities)", size=10, color=MUTED)
    for i, who in enumerate(["Emergency managers & early warning", "Firefighting teams", "Land & forest managers", "Scientists & researchers"]):
        yy = 2.1 + i * 0.95
        c = rect(s, 10.0, yy, 0.62, 0.62, NAVY, shape=MSO_SHAPE.OVAL)
        c.text_frame.text = who[0]
        c.text_frame.paragraphs[0].alignment = PP_ALIGN.CENTER
        r = c.text_frame.paragraphs[0].runs[0]; r.font.size = Pt(16); r.font.bold = True; r.font.color.rgb = WHITE; r.font.name = FONT
        tb(s, 10.75, yy + 0.02, 2.4, 0.8, who, size=12.5)
    tb(s, 0.55, 6.15, 12.2, 0.5, "MODIS (2000–) is near end of life; NASA stopped S-NPP VIIRS data on 2 Nov 2026.", size=14, color=INK2)

    # ------------------------------------------------------------------ 3 sensors
    s = base(prs, 3, "Two eyes in the sky: MODIS 1 km since 2000, VIIRS 375 m since 2012, same afternoon orbit for Aqua and S-NPP, so we can compare them fairly",
             speaker="Ahmed Etkaidek", notes=(
                 "Let me introduce the two eyes. MODIS flies on Terra and Aqua and has watched since 2000 with pixels about one kilometre wide. "
                 "VIIRS, since 2012, sees 375 metre pixels, so about seven VIIRS pixels fit in one MODIS pixel and small fires are caught. "
                 "Aqua and S-NPP cross the equator at about 1:30 in the afternoon and night, so they look at the same fires at the same hour: "
                 "a fair pair for calibration. All data come from NASA FIRMS: standard yearly archives for history and the FIRMS API for live data. "
                 f"We checked the VIIRS to MODIS ratio year by year and used {N['n_cal_years']} stable overlap years; 2021 was an outlier and was left out. "
                 "Since S-NPP stopped, live data come from NOAA-20, the same instrument, converted with a measured factor of "
                 f"{N['k_jn']:.2f}."), source=True)
    # pixel illustration
    tb(s, 0.55, 1.75, 4.6, 0.4, "Same 1 km × 1 km patch of ground", size=14, bold=True)
    rect(s, 0.8, 2.25, 2.0, 2.0, RGBColor(0x7B, 0x8D, 0xB5))
    tb(s, 0.8, 4.3, 2.0, 0.6, "MODIS: 1 pixel (1 km)", size=12, align=PP_ALIGN.CENTER)
    side = 2.0 / 2.667
    for i in range(3):
        for j in range(3):
            w = min(side, 2.0 - i * side)
            h = min(side, 2.0 - j * side)
            if w > 0.02 and h > 0.02:
                rect(s, 3.1 + i * side, 2.25 + j * side, w - 0.03, h - 0.03, NAVY)
    tb(s, 3.0, 4.3, 2.3, 0.6, ["VIIRS: ~7 pixels (375 m)", [("pixel geometry, not a count", {"size": 9, "color": MUTED})]], size=12, align=PP_ALIGN.CENTER)
    tb(s, 0.55, 5.0, 4.8, 1.0, "Smaller pixels catch smaller fires, so VIIRS counts more hotspots.", size=13, color=INK2)
    # timeline
    tb(s, 5.8, 1.75, 7.0, 0.4, "Who watched when", size=14, bold=True)
    x0, x1, yr0, yr1 = 7.3, 12.8, 2000, 2027
    X = lambda yv: x0 + (yv - yr0) / (yr1 - yr0) * (x1 - x0)
    bars = [("MODIS Terra (~10:30)", 2000.0, 2026.9, GREY), ("MODIS Aqua (~13:30)", 2002.5, 2026.9, RGBColor(0x7B, 0x8D, 0xB5)),
            ("VIIRS S-NPP (~13:30)", 2012.05, 2026.84, NAVY), ("VIIRS NOAA-20", 2018.25, 2026.9, RGBColor(0x3B, 0x5B, 0xDB)),
            ("VIIRS NOAA-21", 2024.05, 2026.9, RGBColor(0x74, 0x8F, 0xFC))]
    rect(s, X(2012), 2.25, X(2026) - X(2012), 2.95, RGBColor(0xFD, 0xE4, 0xD6))
    tb(s, X(2012), 5.2, X(2026) - X(2012), 0.35, "overlap: our calibration lab", size=11, color=EMBER, align=PP_ALIGN.CENTER)
    for i, (name, a, b, col) in enumerate(bars):
        yy = 2.35 + i * 0.55
        tb(s, 5.8, yy - 0.04, 1.5, 0.45, name, size=10)
        rect(s, X(a), yy, X(b) - X(a), 0.34, col)
    tb(s, X(2026.84) - 1.2, 2.35 + 2 * 0.55 + 0.33, 2.0, 0.3, "stopped 2 Nov 2026", size=9, color=EMBER)
    for yv in (2000, 2006, 2012, 2018, 2024):
        tb(s, X(yv) - 0.3, 5.5, 0.6, 0.3, str(yv), size=10, color=MUTED, align=PP_ALIGN.CENTER)
    tb(s, 5.8, 5.9, 7.0, 0.7, [[("Calibration years: ", {"bold": True, "size": 12}),
                                (u("ncal", f"{N['n_cal_years']}") + " stable overlap years (2012–2025 without 2021).", {"size": 12})]])

    # ------------------------------------------------------------------ 4 method
    s = base(prs, 4, "We harmonize per area and per month, then compare each month with its usual, and watch live",
             speaker="Aya Salman", notes=(
                 "Our method has three steps. First, in the overlap years we count, for each country and calendar month, how many VIIRS hotspots appear per MODIS hotspot. "
                 "Second, we turn that into a conversion factor with shrinkage: when a month or a small drawn area has few fires, the factor leans on the broader country value, "
                 "so noise does not explode. For any area a user draws, Jamra computes that area's own factor and shows its uncertainty. "
                 "Third, every month is compared with the same month in other years: the median, the middle half, and a percentile rank. "
                 f"We compared six models with leave-one-year-out cross-validation and chose {N['chosen_model']}, the simplest within five percent of the best. "
                 "Behind it, the archive rebuilds monthly from NASA FIRMS, and the live job pulls the FIRMS API every three hours."))
    steps = [("1  Overlap years", "Count VIIRS and MODIS hotspots in the same country and month, 2012–2025."),
             ("2  Conversion factor", "k = (V + λ·k_country) / (M + λ)\nFew fires → lean on the country."),
             ("3  Compare with usual", "Each month vs the same month in other years: median, 25–75%, percentile.")]
    for i, (h, t) in enumerate(steps):
        xx = 0.55 + i * 4.2
        rect(s, xx, 1.75, 3.85, 2.55, WHITE, line=LINE, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.06)
        tb(s, xx + 0.2, 1.9, 3.5, 0.5, h, size=17, bold=True, color=EMBER if i == 1 else NAVY)
        tb(s, xx + 0.2, 2.5, 3.5, 1.7, t, size=14, color=INK2)
        if i < 2:
            a = s.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, Inches(xx + 3.88), Inches(2.85), Inches(0.28), Inches(0.35))
            a.fill.solid(); a.fill.fore_color.rgb = NAVY; a.line.fill.background()
    tb(s, 0.55, 4.45, 12.2, 0.4, [[("Chosen by cross-validation: ", {"bold": True, "size": 13}),
                                   (u("chosen", f"{N['chosen_model']}") + f" ({N['chosen_label'].lower()}), out of six models.", {"size": 13})]])
    # architecture
    arch = [("NASA FIRMS archive", "yearly files"), ("Monthly rebuild", "harmonize + baselines"), ("NASA FIRMS API", "every 3 hours"),
            ("Early-warning check", "month-to-date vs past"), ("Jamra web app", "calendar · alerts · CSV")]
    for i, (h, t) in enumerate(arch):
        xx = 0.55 + i * 2.5
        rect(s, xx, 5.05, 2.2, 1.05, NAVY if i in (0, 2) else WHITE, line=None if i in (0, 2) else NAVY, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.12)
        tb(s, xx + 0.08, 5.12, 2.05, 0.45, h, size=12, bold=True, color=WHITE if i in (0, 2) else NAVY, align=PP_ALIGN.CENTER)
        tb(s, xx + 0.08, 5.52, 2.05, 0.45, t, size=10.5, color=WHITE if i in (0, 2) else INK2, align=PP_ALIGN.CENTER)
        if i < 4:
            a = s.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, Inches(xx + 2.22), Inches(5.45), Inches(0.26), Inches(0.26))
            a.fill.solid(); a.fill.fore_color.rgb = EMBER; a.line.fill.background()

    # ------------------------------------------------------------------ 5 demo
    ev = st["evia_2007_08"]
    T = N["test"]
    s = base(prs, 5, "Pick any area, see its burning calendar, and know which values are observed and which are estimated",
             speaker="Ahmad Akhras", notes=(
                 "Live demo, six steps. "
                 f"1) Home ({url}?area=greece&hero=raw): the raw yearly chart for Greece jumps after 2012. "
                 "2) Press Harmonized: the fake jump disappears. "
                 f"3) Press 'Try the Evia 2007 example' ({url}calendar/?area=evia&from=2003&to=2025&month=2007-08&mode=abs&detail=1): the Calendar opens on Evia, August 2007, with the details open. "
                 f"4) The bars compare August in every year: about {fmt(ev['value'])} hotspots, {ev['times_typical']} times a typical August of {ev['typical']}. "
                 f"5) Point at the label: this value is estimated from MODIS on the VIIRS scale, plus or minus {N['unc_small_pct']} percent (range {fmt(ev['lo'])} to {fmt(ev['hi'])}); raw MODIS saw only {fmt(ev['raw'])}. "
                 f"6) End on the Validation page ({url}validation/): on held-out years the monthly error drops from {T['err_raw_pct']} to {T['err_harm_pct']} percent. "
                 f"Extra if time: Alerts ({url}alerts/) and Live Data ({url}live/?area=greece). "
                 "If Wi-Fi fails, the app works offline from cache; backup screenshots are in AstroByte_Backup.pptx."))
    a = json.loads((WEB / "areas" / "evia.json").read_text(encoding="utf-8"))
    vals = a["harm"]
    import math
    mx = math.log1p(max(v for v in vals if v is not None))
    vir = ["440154", "482878", "3e4989", "31688e", "26828e", "1f9e89", "35b779", "6ece58", "b5de2b", "fde725"]

    def col(v):
        t = math.log1p(v) / mx * (len(vir) - 1)
        i = min(int(t), len(vir) - 2)
        f = t - i
        c1 = [int(vir[i][k:k + 2], 16) for k in (0, 2, 4)]
        c2 = [int(vir[i + 1][k:k + 2], 16) for k in (0, 2, 4)]
        return RGBColor(*[round(c1[k] + (c2[k] - c1[k]) * f) for k in range(3)])
    gx, gy, cw, chh = 0.95, 1.95, 0.36, 0.175
    for m, name in enumerate("JFMAMJJASOND"):
        tb(s, gx + m * cw, gy - 0.28, cw, 0.25, name, size=8, color=MUTED, align=PP_ALIGN.CENTER)
    for r, yv in enumerate(range(2003, 2026)):
        if r % 2 == 0:
            tb(s, gx - 0.48, gy + r * chh - 0.05, 0.45, 0.22, str(yv), size=7, color=MUTED, align=PP_ALIGN.RIGHT)
        for m in range(12):
            v = vals[(yv - 2003) * 12 + m]
            cell = rect(s, gx + m * cw, gy + r * chh, cw - 0.02, chh - 0.02, col(v) if v is not None else LINE)
            if yv < 2012:  # estimated from MODIS: thin light border, like the hatch on the site
                cell.line.color.rgb = RGBColor(0xFF, 0xFF, 0xFF); cell.line.width = Pt(0.75)
            if yv == 2007 and m == 7:
                cell.line.color.rgb = EMBER; cell.line.width = Pt(2.5)
    tb(s, gx - 0.5, gy + 23 * chh + 0.05, 4.9, 0.5, "Evia (Greece), hotspots per month 2003–2025, VIIRS-equivalent, log colour scale. Rows before 2012 are estimated from MODIS.", size=8, color=MUTED)
    tb(s, 5.5, 1.75, 4.8, 1.5, [
        [(u("ev07", f"August 2007, Evia: ≈ {fmt(ev['value'])} hotspots"), {"bold": True, "size": 16})],
        [(u("ev07x", f"{ev['times_typical']}× a typical August"), {"size": 15}), (f" (usual {ev['typical']})", {"size": 13, "color": INK2})],
        [("Estimated from MODIS on the VIIRS scale, ±" + u("unc", f"{N['unc_small_pct']}%"), {"size": 13, "color": EMBER, "bold": True})],
    ])
    if screenshot and Path(screenshot).exists():
        s.shapes.add_picture(str(screenshot), Inches(5.5), Inches(3.3), width=Inches(4.7))
        tb(s, 5.5, 6.3, 4.7, 0.3, "The Jamra web app (installable on phones).", size=9, color=MUTED)
    # QR
    s.shapes.add_picture(qr_png(url), Inches(10.75), Inches(1.75), width=Inches(2.0))
    tb(s, 10.5, 3.8, 2.5, 0.9, ["Try it live", url.replace("https://", "")], size=11, align=PP_ALIGN.CENTER)
    feats = ["8 pages: Calendar, Alerts, Live Data, Validation…", "Presets, countries, polygon, circle, lat/lon", "Observed vs estimated, with ±",
             "Alerts every 3 h from NASA FIRMS", "CSV, PNG and one-page summary"]
    tb(s, 10.45, 4.75, 2.7, 2.0, [[("• " + f, {"size": 10.5})] for f in feats])

    # ------------------------------------------------------------------ 6 validation
    T = N["test"]
    s = base(prs, 6, f"Does it work? On held-out years, monthly error drops from {T['err_raw_pct']}% to {T['err_harm_pct']}% and {T['hits']} of {T['high_total']} high-fire months are caught",
             speaker="Aya Salman", notes=(
                 f"Does it work? We built the model only on {T['dev_years'][0]} to {T['dev_years'][-1]} and kept {T['test_years'][0]} to {T['test_years'][-1]} hidden as a final test. "
                 f"On those test years, raw MODIS is off by {T['err_raw_pct']} percent on a typical country-month; harmonized, {T['err_harm_pct']} percent, and {T['err_year_pct']} percent on a yearly total. "
                 f"For early warning, real VIIRS had {T['high_total']} higher-than-usual months: we caught {T['hits']}, with {T['false_alarms']} false alarms; raw MODIS caught only {T['raw_hits']}. "
                 f"Small areas are harder: typical error {T['small_preset_pct']} percent in the fire areas and {T['small_grid_pct']} percent in {T['grid_regions']} one-degree areas. "
                 + ("The local factor beat the country factor on the test years, by a small margin, so we adopted it. " if T["local_adopted"] else "The local factor did not beat the country factor, so we kept the country factor. ")
                 + "Limits: hotspots are not fires or burned area, clouds hide fires, and FRP was not more stable than counts in our test, so we use counts."))
    cd = CategoryChartData()
    order = ["M0", "M1", "M2", "M3", "M4", "M5"]
    labels = {"M0": "M0 raw MODIS", "M1": "M1 one ratio", "M2": "M2 per country", "M3": "M3 country×month", "M4": "M4 log-log", "M5": "M5 quantile"}
    cd.categories = [labels[m] for m in order]
    cd.add_series("Typical monthly error, test years (%)", [T["by_model_pct"][m] for m in order])
    gf = s.shapes.add_chart(XL_CHART_TYPE.BAR_CLUSTERED, Inches(0.55), Inches(1.75), Inches(6.2), Inches(4.3), cd)
    ch = gf.chart
    style_chart(ch, legend=False, size=12)
    ser = ch.series[0]
    for i, m in enumerate(order):
        pt = ser.points[i]
        pt.format.fill.solid()
        pt.format.fill.fore_color.rgb = EMBER if m == N["chosen_model"] else (GREY if m == "M0" else INK2)
    pl = ch.plots[0]
    pl.has_data_labels = True
    pl.data_labels.number_format = '0"%"'
    pl.data_labels.number_format_is_linked = False
    pl.data_labels.font.size = Pt(12)
    ch.value_axis.visible = False
    ch.value_axis.has_major_gridlines = False
    ch.category_axis.reverse_order = True
    tb(s, 0.55, 6.05, 6.3, 0.7, f"Model chosen on development years {T['dev_years'][0]}–{T['dev_years'][-1]}; scored on test years {', '.join(map(str, T['test_years']))}. Country-months with ≥10 VIIRS hotspots.", size=10, color=MUTED)
    kpis = [(u("err", f"{T['err_raw_pct']}% → {T['err_harm_pct']}%"), "typical monthly error on test years, raw → harmonized"),
            (u("hits", f"{T['hits']} of {T['high_total']}"), f"high-fire months caught · {T['false_alarms']} false alarms (raw MODIS: {T['raw_hits']})"),
            (u("small", f"{T['small_preset_pct']}%"), f"error in small fire areas ({T['small_grid_pct']}% in {T['grid_regions']} 1° areas) · local factor {'adopted' if T['local_adopted'] else 'not adopted'}")]
    for i, (big, small) in enumerate(kpis):
        yy = 1.75 + i * 1.05
        rect(s, 7.1, yy, 5.7, 0.92, WHITE, line=LINE, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.1)
        tb(s, 7.25, yy + 0.12, 2.3, 0.7, big, size=21, bold=True, color=EMBER if i == 0 else NAVY)
        tb(s, 9.6, yy + 0.12, 3.15, 0.8, small, size=11, color=INK2)
    tb(s, 7.1, 4.95, 5.7, 0.4, "Honest limits", size=15, bold=True)
    tb(s, 7.1, 5.35, 5.7, 1.4, [[("• Hotspots are not fires or burned area; clouds hide fires.", {"size": 12})],
                                [("• Small areas: few hotspots → wider error (shown as ±).", {"size": 12})],
                                [("• FRP was not more stable than counts, so we use counts.", {"size": 12})]])

    # ------------------------------------------------------------------ 7 impact
    s = base(prs, 7, "Impact and next steps: a fair 23-year fire calendar for any area, live warnings today, more regions tomorrow",
             speaker="Tala Yousef", source=False, notes=(
                 "Jamra gives emergency teams one fair record from 2003 to today, for any area they draw, with a live early-warning check every three hours "
                 "and open CSV downloads. It runs on free infrastructure and NASA open data, and it installs on a phone. "
                 "Next, we want more regions, an Arabic interface, Telegram and SMS alerts, and to test Terra plus Aqua, "
                 f"which showed a lower cross-validated error ({N['terra_aqua_mdape_pct']} versus {N['cv_aqua_mdape_pct']} percent) and could extend the record to 2001. "
                 "Each of us owned one part, shown here; together we chose the idea and the method, tested the site with real users, and rehearsed this pitch. "
                 "We used an SI coding assistant to write the code, following our design; we checked the numbers against NASA FIRMS. "
                 "Thank you, scan the code and try Jamra yourself."))
    team = [("Shahd Farraj", "Problem & users · slides 1–2"), ("Ahmed Etkaidek", "NASA data & live system · slide 3"),
            ("Aya Salman", "Science: method & validation · slides 4, 6"), ("Ahmad Akhras", "Calendar & live demo · slide 5"),
            ("Tala Yousef", "UX, impact & next steps · slide 7")]
    for i, (nme, role) in enumerate(team):
        xx = 0.55 + (i % 3) * 2.75
        yy = 1.75 + (i // 3) * 1.15
        rect(s, xx, yy, 2.55, 0.98, WHITE, line=LINE, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.1)
        tb(s, xx + 0.12, yy + 0.08, 2.35, 0.4, nme, size=13, bold=True)
        tb(s, xx + 0.12, yy + 0.46, 2.35, 0.5, role, size=10.5, color=INK2)
    tb(s, 0.55, 3.95, 8.2, 0.4, "Shared: idea and method, testing with real users, pitch rehearsal.", size=10.5, color=MUTED)
    tb(s, 0.55, 4.25, 8.2, 0.4, "Next steps", size=15, bold=True)
    road = [("More regions", "global coarse grid"), ("Arabic interface", "right-to-left"), ("Telegram + SMS", "alerts"), ("Terra + Aqua", u("ta", f"{N['terra_aqua_mdape_pct']}% vs {N['cv_aqua_mdape_pct']}% error") + ", to 2001")]
    for i, (h, t) in enumerate(road):
        xx = 0.55 + i * 2.06
        rect(s, xx, 4.65, 1.9, 0.95, NAVY, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.12)
        tb(s, xx + 0.06, 4.7, 1.78, 0.4, h, size=12, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
        tb(s, xx + 0.06, 5.08, 1.78, 0.45, t, size=10, color=WHITE, align=PP_ALIGN.CENTER)
    s.shapes.add_picture(qr_png(url), Inches(9.9), Inches(1.75), width=Inches(2.3))
    tb(s, 9.4, 4.1, 3.3, 0.7, ["Scan to try Jamra", url.replace("https://", "")], size=11, align=PP_ALIGN.CENTER)
    tb(s, 0.55, 5.85, 12.2, 0.9, [
        [("Data: NASA FIRMS (LANCE / ESDIS). We acknowledge the use of data from NASA's Fire Information for Resource Management System (FIRMS). NASA does not endorse this project.", {"size": 9, "color": MUTED})],
        [("SI disclosure: we used an SI coding assistant (Claude Code by Anthropic) to write the code for the pipeline, website, live system and slides, following our design and decisions. The team chose the method, checked results against NASA FIRMS data and verified every reference.", {"size": 9, "color": MUTED})],
    ])
    prs.save(out_path)
    (ROOT / "slides" / "numbers_used.json").write_text(json.dumps(used, indent=1, ensure_ascii=False), encoding="utf-8")
    return out_path


def build_backup(url, out_path, shots):
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    for title, img in shots:
        s = prs.slides.add_slide(prs.slide_layouts[6])
        tb(s, 0.5, 0.2, 12.3, 0.6, f"Backup (not part of the 7-slide submission): {title}", size=20, bold=True)
        if Path(img).exists():
            s.shapes.add_picture(str(img), Inches(0.5), Inches(0.9), height=Inches(6.3))
    prs.save(out_path)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="https://astrobyte-jamra.github.io/jamra/")
    ap.add_argument("--screenshot", default=str(ROOT / "slides" / "shots" / "app.png"))
    a = ap.parse_args()
    out = build(a.url, ROOT / "slides" / "AstroByte_Slides.pptx", a.screenshot)
    shots_dir = ROOT / "slides" / "shots"
    shots = [(p.stem.replace("_", " "), p) for p in sorted(shots_dir.glob("*.*")) if p.suffix.lower() in (".png", ".jpg")]
    if shots:
        build_backup(a.url, ROOT / "slides" / "AstroByte_Backup.pptx", shots)
    print("saved", out)
