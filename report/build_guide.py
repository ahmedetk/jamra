"""Build the Arabic user guide (RTL, A4): report/Jamra_User_Guide_AR.html -> .pdf (Edge headless).

Since Design v3 the website is only the working tool. Everything that explains it (how it works, the
validation results, the limits and the full usage guide) lives in this guide.
All numbers are read from web/public/data/model_report.json, meta.json and the area files.
Screenshots: scripts/guide_shots.py (headless, cropped by section) plus real-browser shots for the map
(shots/calendar_top.jpg, shots/live.png) and the phone view (shots/mobile_*.png).
Usage: python report/build_guide.py
Written with the help of an SI coding assistant (Claude Code); text reviewed by Team Astro Byte.
"""
import json
import shutil
import subprocess
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
REP = ROOT / "report"
SHOTS = REP / "shots"
IMG = REP / "img"
WEB = ROOT / "web" / "public" / "data"
ICONS = ROOT / "web" / "public" / "icons"
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
SITE = "https://ahmedetk.github.io/jamra/"
SHOT_FILES = {  # key: (file in shots/, max width)
    "home": ("g_home.png", 1280), "cal_top": ("calendar_top.jpg", 1280), "cal_chart": ("g_cal_chart.png", 1280),
    "harm": ("g_harm.png", 1280), "cal_main": ("g_cal_main.png", 1280), "cal_detail": ("g_cal_detail.png", 1280),
    "anomaly": ("g_anomaly.png", 1280), "alerts": ("g_alerts.png", 1280), "live": ("live.png", 1280),
    "about": ("g_about.png", 1280), "mobile_home": ("mobile_home.png", 520), "mobile_detail": ("mobile_detail.png", 520),
}


def prep_images():
    IMG.mkdir(exist_ok=True)
    for old in IMG.glob("*.jpg"):
        old.unlink()
    out = {}
    for key, (name, max_w) in SHOT_FILES.items():
        src = SHOTS / name
        if not src.exists():
            print("missing screenshot", name); continue
        im = Image.open(src).convert("RGB")
        if im.width > max_w:
            im = im.resize((max_w, int(im.height * max_w / im.width)), Image.LANCZOS)
        im.save(IMG / f"{key}.jpg", quality=86)
        out[key] = f"{key}.jpg"
    shutil.copy(ICONS / "wordmark-dark.png", IMG / "wordmark.png")
    shutil.copy(ROOT / "web" / "public" / "img" / "earth-blue-marble.webp", IMG / "earth.webp")
    return out


def pct(x):
    return f"{round(x * 100)}%"


def main():
    R = json.loads((WEB / "model_report.json").read_text(encoding="utf-8"))
    meta = json.loads((WEB / "meta.json").read_text(encoding="utf-8"))
    evia = json.loads((WEB / "areas" / "evia.json").read_text(encoding="utf-8"))
    V = R["validation"]
    ch = R["chosen_model"]
    tc = V["test_countries"]
    cc = V["confusion_countries"]["harmonized"]
    cr = V["confusion_countries"]["raw_modis"]
    sp, sg = V["small_regions"]["presets"], V["small_regions"]["grid_1deg"]
    meth = "local" if V["decision"]["adopt_local_factor"] else "baseline"
    u = R["uncertainty"]
    k = R["viirs_vs_modis_ratio"]
    kjn = R["noaa20_to_snpp"]["global"]
    lam = R["lambda"]
    lam_area = R.get("lambda_area")
    cal_years = R["calibration"]["years"]
    ca = R["colour_agreement"]
    i07 = (2007 - 2003) * 12 + 7
    ev_v = round(evia["harm"][i07])
    ev_lo, ev_hi = round(evia["lo"][i07]), round(evia["hi"][i07])
    others = sorted(evia["harm"][(y - 2003) * 12 + 7] for y in range(2003, 2026) if y != 2007)
    n = len(others)
    ev_med = (others[n // 2] if n % 2 else (others[n // 2 - 1] + others[n // 2]) / 2)
    ev_x = round(ev_v / ev_med, 1)
    img = prep_images()
    through = meta["data_through"]
    labels = {a["id"]: a["label"] for a in meta["areas"]}

    def fig(key, cap, cls=""):
        if key not in img:
            return ""
        return f'<figure class="{cls}"><img src="img/{img[key]}" alt=""><figcaption>{cap}</figcaption></figure>'

    def callouts(items, start=1):
        rows = "".join(f'<tr><td class="n">{i}</td><td class="nm">{nm}</td><td>{what}</td></tr>'
                       for i, (nm, what) in enumerate(items, start))
        return f'<table class="co"><thead><tr><th>#</th><th>العنصر</th><th>ماذا يفعل</th></tr></thead><tbody>{rows}</tbody></table>'

    verdict = {
        "M0": "يُظهر المشكلة فقط: أعداد عصر VIIRS أعلى بكثير.",
        "M1": "بسيطة، لكنها تتجاهل اختلاف الدول.",
        "M2": "بسيطة وعادلة لكل دولة.",
        "M3": "تضيف المواسم، وتعتمد على قيمة الدولة حين تكون حرائق الشهر قليلة.",
        "M4": "منحنى مرن؛ قد ينحرف عند القيم الكبيرة جدًا.",
        "M5": "تطابق التوزيعات؛ تحتاج سنوات كثيرة.",
    }
    method_rows = "".join(
        f'<tr class="{"chosen" if m == ch else ""}"><td class="en">{m}</td><td class="en">{R["model_labels"][m]}</td>'
        f'<td>{R["cv"][m]["monthly"]["mae"]:.0f}</td><td>{pct(R["cv"][m]["monthly"]["mdape"])}</td><td>{pct(tc[m]["mdape"])}</td><td>{verdict[m]}{" ✓ المختارة" if m == ch else ""}</td></tr>'
        for m in ["M0", "M1", "M2", "M3", "M4", "M5"])
    per = sp["per_region"]
    preset_rows = "".join(
        f'<tr><td class="en">{labels.get(a, a)}</td><td>{pct(per[a]["baseline"]["mdape"])}</td><td>{pct(per[a]["local"]["mdape"])}</td><td>{per[a]["actual_total"]:,}</td></tr>'
        for a in sorted(per, key=lambda a: per[a]["local"]["mdape"]))

    html = f"""<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8">
<title>دليل استخدام جمرة · jamra User Guide (Arabic)</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Arabic:wght@400;600;700&display=swap" rel="stylesheet">
<style>
@page {{ size: A4; margin: 16mm 14mm 18mm; }}
* {{ box-sizing: border-box; }}
body {{ font-family: "IBM Plex Sans Arabic", "Segoe UI", Tahoma, sans-serif; color: #111827; font-size: 11.5pt; line-height: 1.75; margin: 0; }}
h1 {{ font-size: 26pt; margin: 0 0 6mm; }}
h2 {{ font-size: 17pt; color: #111827; border-bottom: 3px solid #E8833A; padding-bottom: 2mm; margin: 0 0 4mm; }}
h3 {{ font-size: 13pt; margin: 5mm 0 2mm; }}
section {{ page-break-before: always; }} section.cover {{ page-break-before: auto; }}
.cover {{ height: 255mm; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; }}
.cover .s {{ font-size: 15pt; color: #4B5563; }}
.en {{ direction: ltr; unicode-bidi: isolate; font-family: "Segoe UI", Arial, sans-serif; }}
figure {{ margin: 3mm 0; page-break-inside: avoid; }} figure img {{ width: 100%; border: 1px solid #E5E7EB; border-radius: 4px; }}
figure.phone {{ width: 60mm; display: inline-block; margin-left: 6mm; vertical-align: top; }}
figcaption {{ font-size: 9.5pt; color: #4B5563; }}
table {{ width: 100%; border-collapse: collapse; font-size: 10pt; margin: 2mm 0 4mm; page-break-inside: auto; }}
th, td {{ border: 1px solid #E5E7EB; padding: 1.6mm 2mm; vertical-align: top; text-align: right; }}
th {{ background: #F7F7F5; }} tr {{ page-break-inside: avoid; }}
tr.chosen td {{ background: #FCE7D6; font-weight: 600; }}
td.n {{ width: 8mm; text-align: center; font-weight: 700; color: #111827; background: #E8833A; }}
td.nm {{ width: 36mm; font-weight: 600; }}
.box {{ background: #F7F7F5; border-right: 4px solid #111827; padding: 3mm 4mm; margin: 3mm 0; }}
.kpis {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 3mm; }}
.kpi {{ border: 1px solid #E5E7EB; border-radius: 6px; padding: 3mm; }} .kpi b {{ display: block; font-size: 16pt; color: #111827; }}
.small {{ font-size: 9.5pt; color: #4B5563; }}
.formula {{ direction: ltr; text-align: center; font-family: "Cambria Math", "Segoe UI", serif; font-size: 14pt; margin: 3mm 0; }}
ol li, ul li {{ margin-bottom: 1.5mm; }}
.map {{ display: grid; grid-template-columns: repeat(5, 1fr); gap: 2mm; text-align: center; }}
.map div {{ border: 2px solid #111827; border-radius: 6px; padding: 2mm; font-weight: 600; }}
.map div.h {{ background: #111827; color: #fff; }}
</style></head><body>

<section class="cover">
  <img src="img/earth.webp" alt="" style="width:64mm;height:64mm;margin:0 auto 8mm">
  <img src="img/wordmark.png" alt="jamra" style="width:70mm;margin:0 auto 4mm">
  <p class="s">تقويم موحَّد لنشاط الحرائق من قمرَي <span class="en">MODIS</span> و<span class="en">VIIRS</span> مع إنذار مبكر مباشر</p>
  <h1 style="margin-top:10mm">دليل استخدام جمرة</h1>
  <p>الطريقة · نتائج التحقق · الحدود · شرح كل صفحة</p>
  <p class="s">فريق <span class="en">Astro Byte</span> · <span class="en">NASA Space Apps Challenge 2026</span></p>
  <p>شهد فرّاج · أحمد اتكيدك · آية سلمان · أحمد الأخرس · تالا يوسف</p>
  <p class="small">مبني لتحدّي <span class="en">NASA Space Apps Challenge 2026</span> · ليس منتجًا رسميًا لناسا · ليس خدمة طوارئ · صورة الأرض: <span class="en">NASA GIBS / Blue Marble</span></p>
  <p class="small">الموقع: <span class="en">{SITE}</span> · البيانات حتى <span class="en">{through}</span> · كل الأرقام في هذا الدليل محسوبة من بياناتنا</p>
</section>

<section>
  <h2>1. ما هي جمرة؟</h2>
  <h3>المشكلة: «قفزة وهمية» في عدد الحرائق</h3>
  <p>ترصد الأقمار الصناعية الحرائق على شكل «بؤر حرارية» (<span class="en">hotspots</span>)، أي بكسلات ساخنة في صور القمر. منذ عام 2000 يرصدها جهاز <span class="en">MODIS</span> بدقة 1 كم. وفي 2012 انضم جهاز أدقّ هو <span class="en">VIIRS</span> بدقة 375 م، فصار يرى حرائق أصغر وبؤرًا أكثر للحريق نفسه.</p>
  <p>في دولنا الثماني سجّل <span class="en">VIIRS</span> نحو <b>{k:.1f} أضعاف</b> البؤر التي سجّلها <span class="en">MODIS</span> في الأشهر نفسها. لذلك إذا وصلنا السجلَّين كما هما يظهر ارتفاع كبير بعد 2012 لم يحدث على الأرض: سببه دقة الجهاز الجديد، لا زيادة الحرائق.</p>
  <h3>الحل</h3>
  <p>جمرة «تُوائم» السجل القديم: تحوّل أعداد <span class="en">MODIS</span> قبل 2012 إلى ما يعادلها بمقياس <span class="en">VIIRS</span>، فيصبح لدينا سجل واحد عادل من 2003 حتى اليوم. ثم تقارن كل شهر بالمعتاد له في السنوات الأخرى، وتتابع بيانات ناسا الجديدة كل 3 ساعات لتنبّه إذا كان الشهر الحالي غير عادي.</p>
  {fig("harm", "صفحة التقويم، الرسم السنوي بوضع «Harmonized» (اليونان): القفزة الوهمية بعد 2012 اختفت. الأعمدة المخطَّطة قبل 2012 مقدَّرة من MODIS.")}
  <div class="box">جمرة ليست خدمة طوارئ: بيانات الأقمار تصل بتأخير ساعات. في الطوارئ اتصل برقم الطوارئ المحلي (112 في أوروبا وتركيا).</div>
</section>

<section>
  <h2>2. لمن صُمِّمت جمرة؟</h2>
  <table><thead><tr><th>المستخدم</th><th>ماذا يستفيد</th></tr></thead><tbody>
  <tr><td>مديرو الطوارئ وفرق الإنذار المبكر</td><td>يعرفون فورًا إن كان هذا الشهر أعلى من المعتاد في منطقتهم (صفحة <b>Alerts</b> وبطاقة «Early warning now» في التقويم).</td></tr>
  <tr><td>فرق الإطفاء</td><td>يرون أحدث البؤر على الخريطة وفي جدول من واجهة ناسا <span class="en">FIRMS</span> مباشرة (صفحة <b>Live Data</b>).</td></tr>
  <tr><td>مديرو الأراضي والغابات</td><td>يعرفون متى يبدأ موسم الحرائق ومتى يبلغ ذروته، وأي السنوات كانت الأسوأ، على مقياس واحد عادل.</td></tr>
  <tr><td>العلماء والباحثون</td><td>سجل متّسق من 2003 حتى اليوم مع نطاق الخطأ، وتنزيل <span class="en">CSV</span>، وطريقة مفتوحة ونتائج اختبار مستقل (هذا الدليل).</td></tr>
  </tbody></table>
  <p><b>مستفيدون غير مباشرين:</b> المجالس القروية والبلديات والمزارعون، عبر السلطات المحلية والدفاع المدني الذين يستخدمون جمرة.</p>

  <h2 style="margin-top:8mm">3. خريطة الموقع</h2>
  <p>الموقع أداة عمل فقط، من خمس صفحات. شريط التنقل الأبيض نفسه في أعلى كل صفحة، والصفحة الحالية تحتها خط برتقالي. الضغط على شعار <span class="en">jamra</span> يعيدك إلى الرئيسية. المنطقة والفترة والشهر المختارة تنتقل معك بين الصفحات عبر الرابط.</p>
  <div class="map">
    <div class="h">Home<br><span class="en">/jamra/</span></div><div>Calendar<br><span class="en">/calendar/</span></div><div>Alerts<br><span class="en">/alerts/</span></div><div>Live Data<br><span class="en">/live/</span></div><div>About<br><span class="en">/about/</span></div>
  </div>
  <p class="small">صفحات الشرح القديمة (<span class="en">How It Works</span> و<span class="en">Validation</span> و<span class="en">Limits</span> و<span class="en">Credits</span>) أُزيلت من الموقع ونُقل محتواها إلى هذا الدليل؛ روابطها القديمة تفتح صفحة <span class="en">About</span> تلقائيًا مع الإبقاء على خياراتك. يمكن تثبيت الموقع على الهاتف كتطبيق (<span class="en">PWA</span>) ويعمل دون إنترنت من آخر نسخة محفوظة.</p>
</section>

<section>
  <h2>4. صفحة بصفحة</h2>
  <h3>4.1 الرئيسية (<span class="en">Home</span>)</h3>
  <p>كرة أرضية حقيقية (صور <span class="en">NASA Blue Marble</span>) في فضاء حقيقي، عليها نقاط برتقالية صغيرة هي بؤر آخر 7 أيام من ناسا. عنوان واحد وزرّان كبيران.</p>
  {fig("home", "الصفحة الرئيسية على الكمبيوتر مع أرقام العناصر.")}
  {callouts([
    ("شريط التنقل", "Home · Calendar · Alerts · Live Data، ورابط صغير About."),
    ("شارة الحالة", "«Live · updated …» أو «Delayed» أو «Outdated»: مدى حداثة بيانات ناسا."),
    ("الكرة الأرضية", "اسحبها بالفأرة أو بالإصبع لتدويرها؛ تتوقف عند اللمس وتعود للدوران البطيء بعد 5 ثوانٍ تقريبًا."),
    ("Open the Calendar", "يفتح صفحة التقويم."),
    ("Try Evia 2007", "يفتح التقويم على إيفيا وشهر آب 2007 مع التفاصيل: مثال قيمة مقدَّرة من MODIS ونطاق خطئها."),
    ("شريحة البيانات المباشرة", "عدد البؤر في آخر 7 أيام · Data: NASA FIRMS."),
  ])}
  {fig("mobile_home", "الرئيسية على هاتف بعرض 390 بكسل.", "phone")}
</section>

<section>
  <h3>4.2 التقويم (<span class="en">Calendar</span>)</h3>
  <p>تاريخ الحرائق لأي منطقة: أي الأشهر والسنوات أكثر نشاطًا، ومقارنة كل شهر بالمعتاد.</p>
  {fig("cal_top", "أعلى صفحة التقويم: اختيار المنطقة والخريطة (عند التقريب تتحول الخريطة من صورة الأرض إلى خريطة تفاصيل فاتحة).")}
  {callouts([
    ("Fire areas", "مناطق جاهزة مشهورة بالحرائق (إيفيا، أتيكا، وسط البرتغال…)."),
    ("Countries", "الدول الثماني في منطقة التغطية."),
    ("Draw", "ارسم مضلّعًا أو دائرة على الخريطة لأي منطقة تهمّك."),
    ("Lat / Lon", "أدخل نقطة ونصف قطر، أو حدود مربع."),
    ("الخريطة", "المنطقة المختارة بخط برتقالي وأحدث البؤر؛ تطير الخريطة إلى المنطقة في نحو 3 ثوانٍ."),
    ("Recent hotspots", "بؤر آخر 24 ساعة (أفتح لونًا) أو 7 أيام أو إخفاؤها."),
    ("بطاقة المنطقة", "معامل التحويل للمنطقة ونطاق الخطأ لشهر واحد."),
  ])}
  {fig("cal_chart", "الرسم السنوي (رقم 8) بوضع Raw: MODIS حتى 2011 ثم VIIRS، فتظهر القفزة الوهمية.")}
  {callouts([("Raw / Harmonized", "يبدّل الرسم السنوي بين السجل الخام والسجل المُواءَم بمقياس VIIRS.")], start=8)}
</section>

<section>
  {fig("cal_main", "وسط صفحة التقويم: الفترة، البطاقات، التقويم وأزرار التنزيل.")}
  {callouts([
    ("From / To", "السنوات التي يُحسب منها «المعتاد»."),
    ("Hide gas flares / industry", "يحذف خلايا فيها حرارة ثابتة طوال السنة تقريبًا (شعلات غاز، مصانع)."),
    ("البطاقات", "شهر الذروة، الآن مقابل المعتاد، أنشط سنة، الإنذار المبكر الآن، إجمالي الرصد."),
    ("Compared with usual", "يلوّن الخلايا: أزرق رمادي أقل من المعتاد، رمادي عادي، برتقالي أعلى؛ مع رموز ▲ ▼ ونص في المفتاح."),
    ("Weeks", "52 أسبوعًا بدل 12 شهرًا (للدول ومناطق الحرائق)."),
    ("Colours", "لوحة الألوان (Viridis، Cividis، YlOrRd)، كلها مناسبة لعمى الألوان."),
    ("التقويم", "صفوف = سنوات، أعمدة = أشهر. الخلايا المخطَّطة مقدَّرة من MODIS، والمصمتة مرصودة من VIIRS."),
    ("CSV / PNG", "جدول القيم الشهرية مع المصدر ونطاق الخطأ، أو صورة للتقويم."),
    ("Summary PNG / PDF", "صفحة ملخص واحدة: المنطقة، الفترة، الشهر مقابل الوسيط، تقويم صغير، المصدر، والاعتراف ببيانات FIRMS."),
  ], start=9)}
</section>

<section>
  {fig("cal_detail", "تفاصيل الشهر (رقم 18): إيفيا، آب 2007، مع وسم «estimated from MODIS · ±44%».")}
  <p><b>تفاصيل الشهر (18):</b> اضغط أي خلية لترى جملة واضحة، والقيمة ووسم مصدرها (<span class="en">observed · VIIRS</span> أو <span class="en">estimated from MODIS · ±X%</span>)، ونطاق الخطأ، والقيمة الخام، والمعتاد (الوسيط) و«النصف الأوسط» من السنوات، والرتبة المئوية، ورسمًا لنفس الشهر في كل السنوات. يمكن التنقل بين الخلايا بأسهم لوحة المفاتيح والضغط على <span class="en">Enter</span>.</p>
  <div class="box">مثال حقيقي: آب 2007 في إيفيا ≈ <b>{ev_v:,}</b> بؤرة (من {ev_lo:,} إلى {ev_hi:,})، أي نحو <b>{ev_x}</b> ضعف آب المعتاد ({ev_med:,.0f}). القيمة <b>مقدَّرة من MODIS بمقياس VIIRS</b> بنطاق خطأ ±{round(u["small_regions_rel"] * 100)}%.</div>
  {fig("mobile_detail", "التفاصيل على الهاتف.", "phone")}
</section>

<section>
  <h3>4.3 التنبيهات (<span class="en">Alerts</span>)</h3>
  <p>هل هذا الشهر غير عادي الآن؟ بطاقة كبيرة لكل منطقة.</p>
  {fig("alerts", "صفحة التنبيهات.")}
  {callouts([
    ("حالة البيانات", "آخر تحديث ناجح؛ وتظهر «Delayed» أو «Partial month» أو «Last update failed» عند الحاجة."),
    ("بطاقات التنبيه", "المنطقة، الفترة (مثلًا 1–13 Nov، منذ بداية الشهر)، القيمة مقابل المعتاد والنسبة، المستوى، وقت التحديث وحالة البيانات."),
    ("ملاحظة المقياس", f"أعداد NOAA-20 مضروبة في {kjn:.2f} لتطابق مقياس S-NPP (توقف S-NPP في 2 Nov 2026)."),
    ("الخلاصات", "alerts.json و RSS و status.json لربط أنظمة أخرى."),
  ])}
  <p class="small">المستويات: <span class="en">Normal</span>، <span class="en">Elevated</span> (≥ المئين 75)، <span class="en">High</span> (≥ 90)، <span class="en">Extreme</span> (≥ 97.5)، مقارنةً بالأيام نفسها في السنوات السابقة. إذا كانت البيانات أقدم من 30 ساعة يظهر «Outdated» بدل أي مستوى.</p>

  <h3>4.4 البيانات المباشرة (<span class="en">Live Data</span>)</h3>
  {fig("live", "صفحة البيانات المباشرة: أحدث البؤر على الخريطة وفي الجدول.")}
  {callouts([
    ("اختيار المنطقة", "نفس طرق الاختيار في التقويم."),
    ("الخريطة", "البؤر الجديدة؛ مرّر المؤشر فوق نقطة لترى الوقت وقوة الإشعاع FRP."),
    ("Last", "الفترة: من آخر 24 ساعة حتى 7 أيام."),
    ("Get data from NASA FIRMS", "يجلب كشوفات NOAA-20 من واجهة ناسا ويعرض وقت الجلب."),
    ("Download CSV", "يحفظ النتائج لاستخدامها في أنظمة أخرى."),
    ("الجدول", "التاريخ والوقت والقمر والثقة وFRP والإحداثيات؛ اضغط العناوين للترتيب."),
  ])}
</section>

<section>
  <h3>4.5 عن المشروع (<span class="en">About</span>)</h3>
  {fig("about", "صفحة About.")}
  {callouts([
    ("الفريق", "الأعضاء الخمسة وأدوارهم."),
    ("الاعتراف ببيانات FIRMS", "النص الذي تطلبه ناسا حرفيًا، ثم مصادر الصور والخرائط والمراجع والإفصاح عن الذكاء الفائق."),
    ("GitHub", "الكود مفتوح المصدر (MIT)."),
  ])}
  <p class="small">في الصفحة أيضًا: «Built for the NASA Space Apps Challenge 2026» و«Not an official NASA product» و«Not an emergency service».</p>
</section>

<section>
  <h2>5. كيف تعمل الطريقة (بشكل مبسّط)</h2>
  <h3>القمران</h3>
  <p><span class="en">MODIS</span> على القمر <span class="en">Aqua</span> و<span class="en">VIIRS</span> على القمر <span class="en">S-NPP</span> يمرّان فوقنا في الوقت نفسه تقريبًا (نحو 1:30 ظهرًا و1:30 ليلًا)، فيريان الحرائق نفسها. بكسل <span class="en">MODIS</span> بعرض 1 كم يقابل نحو 7 بكسلات من <span class="en">VIIRS</span> (375 م)، لذلك يعدّ <span class="en">VIIRS</span> بؤرًا أكثر للحريق نفسه.</p>
  <h3>الخطوة 1: سنوات التداخل</h3>
  <p>من 2012 يعمل الجهازان معًا. استخدمنا {len(cal_years)} سنة تداخل مستقرة ({cal_years[0]}–{cal_years[-1]}{" دون 2021" if 2021 not in cal_years else ""}) واستبعدنا الأشهر التي تعطّل فيها أحد القمرين. قاعدة اختيار السنوات: نسبة <span class="en">VIIRS</span> إلى <span class="en">MODIS</span> في السنة قريبة (±15%) من نسبة السنة الوسيطة.</p>
  <h3>الخطوة 2: معامل التحويل لكل دولة وشهر</h3>
  <p>لكل دولة ولكل شهر من السنة نحسب: كم بؤرة يرى <span class="en">VIIRS</span> مقابل كل بؤرة يراها <span class="en">MODIS</span>. حين تكون حرائق ذلك الشهر قليلة يصبح الرقم غير مستقر، فنسحبه نحو قيمة الدولة كلها («انكماش»):</p>
  <p class="formula">k = (V + λ · k<sub>country</sub>) / (M + λ)</p>
  <p>حيث <span class="en">V</span> و<span class="en">M</span> مجموع بؤر <span class="en">VIIRS</span> و<span class="en">MODIS</span> في ذلك الشهر عبر سنوات التداخل، و<span class="en">λ = {lam:g}</span> اخترناه بالتحقق المتقاطع.</p>
  <h3>الخطوة 3: السجل القديم على المقياس الجديد</h3>
  <p>نضرب أعداد <span class="en">MODIS</span> قبل 2012 في المعامل، فتصبح «بؤرًا معادِلة لـ <span class="en">VIIRS</span>». هذه القيم <b>مقدَّرة</b>، ولها نطاق خطأ: ±{round(u["monthly_rel"] * 100)}% لشهر الدولة، ±{round(u["annual_rel"] * 100)}% لسنة الدولة، ±{round(u["small_regions_rel"] * 100)}% لشهر في منطقة صغيرة.</p>
  <h3>الخطوة 4: المقارنة بالمعتاد</h3>
  <p>«المعتاد» لشهر ما هو <b>الوسيط</b> لنفس الشهر في السنوات الأخرى من الفترة المختارة. ثم نحسب الرتبة المئوية ونصنّف الشهر: أقل بكثير، أقل، عادي، أعلى، أعلى بكثير (مع حماية من الأعداد الصغيرة جدًا).</p>
  <h3>المعامل المحلي للمناطق الصغيرة</h3>
  <p>المنطقة الصغيرة (منطقة حريق جاهزة أو مرسومة) تأخذ معاملها من بؤرها هي في سنوات التداخل، مسحوبًا نحو معامل الدولة بالطريقة نفسها{f" (λ = {lam_area:g})" if lam_area else ""}: كلما قلّت بؤرها اعتمدت أكثر على الدولة.</p>
  {fig("anomaly", "التقويم بوضع «Compared with usual»: رموز ونص بجانب كل لون، لا نعتمد على اللون وحده.")}
</section>

<section>
  <h3>مقارنة ست طرق</h3>
  <table><thead><tr><th>الرمز</th><th>الطريقة</th><th>خطأ شهري (MAE)</th><th>الخطأ المعتاد %</th><th>سنوات الاختبار %</th><th>الحكم</th></tr></thead><tbody>
  {method_rows}
  <tr><td>—</td><td>VIIRS فقط</td><td>—</td><td>—</td><td>—</td><td>صادقة لكنها ترمي 2003–2011، تسع سنوات من التاريخ (ومنها اليونان 2007).</td></tr>
  </tbody></table>
  <p class="small">الخطأ الشهري والخطأ المعتاد: تحقق متقاطع بترك سنة واحدة في كل مرة على سنوات المعايرة. اخترنا <span class="en">{ch}</span> لأنها أبسط طريقة خطؤها الشهري (MAE) ضمن 5% من الأفضل، والاختيار تم على سنوات التطوير فقط. للأمانة: الطريقتان <span class="en">M4</span> و<span class="en">M5</span> أقل في «الخطأ المعتاد %» لكن خطأهما بالأعداد (MAE) أكبر في الأشهر الكبيرة، وهي الأهم للإنذار.</p>
  <h3>مسار البيانات</h3>
  <ul>
    <li><b>التاريخ</b> (2003 حتى الشهر الماضي): ملفات أرشيف ناسا <span class="en">FIRMS</span> السنوية وواجهة <span class="en">FIRMS</span>، يُعاد بناؤه تلقائيًا كل شهر.</li>
    <li><b>الأيام الأخيرة:</b> واجهة <span class="en">FIRMS</span> كل 3 ساعات (<span class="en">GitHub Actions</span>). إذا فشل التحديث تبقى آخر بيانات سليمة وتظهر حالة واضحة.</li>
    <li><b>لماذا لا نجلب 20 سنة عند كل ضغطة؟</b> واجهة ناسا تسمح بنحو 5,000 معاملة كل 10 دقائق وكل يوم مطلوب يُحسب؛ 20 سنة نحو 8,700 يوم لكل قمر.</li>
    <li><b>S-NPP ← NOAA-20:</b> أوقفت ناسا بيانات <span class="en">S-NPP</span> في 2 تشرين الثاني 2026. <span class="en">NOAA-20</span> يحمل جهاز <span class="en">VIIRS</span> نفسه؛ قِسنا العلاقة في 2018–2025 فوجدنا معاملًا <b>{kjn:.2f}</b> نضرب به أعداده لتبقى على مقياس سجلّنا.</li>
  </ul>
</section>

<section>
  <h2>6. نتائج التحقق</h2>
  <p><b>تصميم الاختبار:</b> سنوات التطوير ({V["dev_years"][0]}–{V["dev_years"][-1]}{" دون 2021" if 2021 not in V["dev_years"] else ""}) لبناء النموذج واختيار إعداداته، وسنوات الاختبار ({"، ".join(map(str, V["test_years"]))}) محجوزة لم تُلمس أثناء التطوير. كل نتيجة في هذا القسم من سنوات الاختبار فقط.</p>
  <div class="kpis">
    <div class="kpi"><b>{pct(tc["M0"]["mdape"])} ← {pct(tc[ch]["mdape"])}</b>الخطأ المعتاد لشهر الدولة: MODIS الخام ← بعد المواءمة</div>
    <div class="kpi"><b>{pct(tc[ch]["annual"]["mdape"])}</b>الخطأ المعتاد لمجموع سنة الدولة (الخام: {pct(tc["M0"]["annual"]["mdape"])})</div>
    <div class="kpi"><b>{cc["hits"]} من {cc["hits"] + cc["misses"]}</b>الأشهر عالية النشاط التي اكتُشفت (نسبة {pct(cc["hit_rate"])})، مع {cc["false_alarms"]} إنذارًا خاطئًا</div>
    <div class="kpi"><b>{pct(sg[meth]["mdape"])}</b>الخطأ المعتاد لشهر في {sg["regions"]} منطقة بحجم 1°، و{pct(sp[meth]["mdape"])} في مناطق الحرائق التسع</div>
  </div>
  <h3>الأشهر عالية النشاط (الدول)</h3>
  <p class="small">الشهر «عالي النشاط» إذا كان «أعلى» أو «أعلى بكثير» من المعتاد (الرتبة المئوية ≥ 75) حسب بيانات <span class="en">VIIRS</span> الحقيقية.</p>
  <table><thead><tr><th>السجل</th><th>اكتُشف (إصابات)</th><th>فات</th><th>إنذار خاطئ</th><th>نسبة الاكتشاف</th></tr></thead><tbody>
  <tr><td>MODIS الخام</td><td>{cr["hits"]}</td><td>{cr["misses"]}</td><td>{cr["false_alarms"]}</td><td>{pct(cr["hit_rate"])}</td></tr>
  <tr class="chosen"><td>بعد المواءمة ({ch})</td><td>{cc["hits"]}</td><td>{cc["misses"]}</td><td>{cc["false_alarms"]}</td><td>{pct(cc["hit_rate"])}</td></tr>
  </tbody></table>
  <h3>المناطق الصغيرة: المعامل المحلي مقابل معامل الدولة</h3>
  <table><thead><tr><th>المناطق</th><th>معامل الدولة (MAE)</th><th>المعامل المحلي (MAE)</th><th>الاكتشاف (دولة / محلي)</th></tr></thead><tbody>
  <tr><td>مناطق الحرائق ({sp["regions"]})</td><td>{sp["baseline"]["mae"]:.1f}</td><td>{sp["local"]["mae"]:.1f}</td><td>{sp["baseline"]["confusion"]["hits"]} / {sp["local"]["confusion"]["hits"]}</td></tr>
  <tr><td>مناطق 1° ({sg["regions"]})</td><td>{sg["baseline"]["mae"]:.2f}</td><td>{sg["local"]["mae"]:.2f}</td><td>{sg["baseline"]["confusion"]["hits"]} / {sg["local"]["confusion"]["hits"]}</td></tr>
  </tbody></table>
  <p><b>القرار:</b> {"اعتُمد المعامل المحلي لأنه خفّض خطأ المناطق الصغيرة في سنوات الاختبار؛ التحسّن صغير لكنه ثابت." if meth == "local" else "لم يُعتمد المعامل المحلي لأنه لم يتفوّق في سنوات الاختبار، فتستخدم المناطق الصغيرة معامل الدولة."}</p>
  <h3>مناطق الحرائق واحدة واحدة</h3>
  <table><thead><tr><th>المنطقة</th><th>الخطأ المعتاد (دولة)</th><th>الخطأ المعتاد (محلي)</th><th>بؤر VIIRS الفعلية</th></tr></thead><tbody>{preset_rows}</tbody></table>
  <h3>اختبارات أخرى</h3>
  <ul>
    <li><b>ألوان التقويم:</b> اللون نفسه من MODIS المُواءَم ومن VIIRS الحقيقي في {ca["same_colour_pct"]:.0f}% من أشهر الدول (MODIS الخام: {ca["without_harmonization_pct"]:.0f}%).</li>
    <li><b>اختبار FRP:</b> فكرة أن مجموع قوة الإشعاع أكثر ثباتًا من عدد البؤر لم تؤيدها بياناتنا (تذبذب {R["frp_test"]["pooled_cv_frp_ratio"]:.2f} مقابل {R["frp_test"]["pooled_cv_count_ratio"]:.2f})، لذلك يعتمد التقويم على عدد البؤر.</li>
    <li><b>ثبات النسبة عبر السنين:</b> نتحقق كل سنة من نسبة VIIRS إلى MODIS لأن مدارات الأقمار القديمة تنجرف.</li>
  </ul>
</section>

<section>
  <h2>7. الحدود</h2>
  <div class="kpis">
    <div class="kpi"><b>±{round(u["monthly_rel"] * 100)}%</b>نطاق الخطأ لشهر الدولة (قبل 2012)</div>
    <div class="kpi"><b>±{round(u["annual_rel"] * 100)}%</b>نطاق الخطأ لمجموع سنة الدولة</div>
    <div class="kpi"><b>±{round(u["small_regions_rel"] * 100)}%</b>نطاق الخطأ لشهر في منطقة صغيرة</div>
    <div class="kpi"><b>×{kjn:.2f}</b>معامل NOAA-20 ← S-NPP للبيانات المباشرة</div>
  </div>
  <ul>
    <li><b>البؤرة ليست حريقًا</b> وليست مساحة محروقة. الحريق الكبير يصنع بؤرًا كثيرة.</li>
    <li><b>الغيوم والدخان تخفي الحرائق.</b> الحرائق الصغيرة أو القصيرة تفوت، وتفوت MODIS أكثر من VIIRS.</li>
    <li><b>قيم ما قبل 2012 تقديرات</b> من MODIS بمقياس VIIRS مع نطاق خطأ؛ المناطق الصغيرة أوسع نطاقًا.</li>
    <li><b>الأعطال وانجراف المدارات:</b> الأقمار القديمة تنجرف؛ نتحقق من النسبة كل سنة.</li>
    <li><b>توقف S-NPP في 2 تشرين الثاني 2026:</b> البيانات المباشرة من NOAA-20 مع معامل مقيس.</li>
    <li><b>البيانات شبه الآنية والقياسية تختلف قليلًا:</b> الأشهر الأخيرة تستخدم البيانات شبه الآنية حتى تحلّ محلها بيانات ناسا القياسية.</li>
    <li><b>ليست كل بؤرة حريق غابة:</b> حرق زراعي، شعلات غاز، صناعة، وفي مناطق النزاع انفجارات أو مبانٍ تحترق. فلتر المصادر الثابتة قد يخطئ.</li>
    <li><b>التغطية:</b> البرتغال، إسبانيا، اليونان، تركيا، قبرص، لبنان، الأردن، فلسطين.</li>
    <li><b>التأخير ساعات: ليست خدمة طوارئ.</b></li>
  </ul>
</section>

<section>
  <h2>8. سيناريوهات استخدام</h2>
  <h3>مسار العرض: إيفيا 2007</h3>
  <ol>
    <li>افتح صفحة <b>Calendar</b> (اليونان). في الرسم السنوي اضغط <b>Raw</b>: قفزة كبيرة بعد 2012.</li>
    <li>اضغط <b>Harmonized</b>: القفزة الوهمية تختفي.</li>
    <li>اختر <b>Evia (Greece)</b> من Fire areas، ثم اضغط خلية <b>آب 2007</b> (أو زر «Try Evia 2007» في الرئيسية).</li>
    <li>في التفاصيل: ≈ {ev_v:,} بؤرة، نحو {ev_x} ضعف آب المعتاد؛ قارنها بآب في السنوات الأخرى في الرسم.</li>
    <li>لاحظ الوسم <b>estimated from MODIS · ±{round(u["small_regions_rel"] * 100)}%</b>.</li>
    <li>نتيجة الاختبار المستقل (الشريحة 6): الخطأ الشهري {pct(tc["M0"]["mdape"])} ← {pct(tc[ch]["mdape"])}، واكتشاف {cc["hits"]} من {cc["hits"] + cc["misses"]} شهرًا عالي النشاط.</li>
  </ol>
  <h3>مدير طوارئ: هل هذا الشهر غير عادي؟</h3>
  <ol><li>افتح <b>Alerts</b>.</li><li>تأكد أن الحالة «Data up to date» ولا يوجد «Partial month».</li><li>اقرأ بطاقة منطقتك: الفترة، القيمة مقابل المعتاد، والمستوى.</li><li>اضغط البطاقة لفتح التقويم على المنطقة نفسها.</li></ol>
  <h3>مدير غابات: مقارنة المواسم</h3>
  <ol><li>في <b>Calendar</b> اختر منطقة أو ارسمها.</li><li>اختر «Compared with usual» لرؤية الأشهر الأعلى (▲) والأدنى (▼).</li><li>اقرأ بطاقة «Fire season start» أسفل التقويم: بداية الموسم المعتادة والاتجاه وهل هو ذو دلالة.</li><li>نزّل «Summary PDF» لإرفاقه بتقرير.</li></ol>
  <h3>فريق إطفاء: البيانات المباشرة</h3>
  <ol><li>افتح <b>Live Data</b> واختر المنطقة.</li><li>اختر الفترة واضغط «Get data from NASA FIRMS».</li><li>رتّب الجدول حسب الوقت أو FRP وانظر المواقع على الخريطة.</li><li>نزّل CSV عند الحاجة.</li></ol>
  <h3>باحث: تنزيل البيانات</h3>
  <ol><li>في <b>Calendar</b> اختر المنطقة والفترة.</li><li>اضغط «CSV»: كل شهر مع قيمته المُواءَمة ومصدره (مرصود/مقدَّر) ونطاق الخطأ والأعداد الخام لكل قمر.</li><li>راجع القسمين 5 و6 من هذا الدليل لفهم الطريقة ودقتها.</li></ol>
</section>

<section>
  <h2>9. الفريق وتوزيع العمل</h2>
  <table><thead><tr><th>العضو</th><th>الدور</th><th>يقدّم</th></tr></thead><tbody>
  <tr><td>شهد فرّاج</td><td>المشكلة والمستخدمون: من يحتاج جمرة ولماذا، ووصف المشروع في Space Apps.</td><td>الشريحتان 1–2</td></tr>
  <tr><td>أحمد اتكيدك</td><td>بيانات ناسا والنظام المباشر: أرشيف FIRMS وواجهته، GitHub Pages والتحديث كل 3 ساعات، صفحتا Alerts وLive Data (تحوّل S-NPP ← NOAA-20).</td><td>الشريحة 3</td></tr>
  <tr><td>آية سلمان</td><td>العلم: طريقة المواءمة والمعامل المحلي، والاختبار المستقل ونتائج المناطق الصغيرة.</td><td>الشريحتان 4 و6</td></tr>
  <tr><td>أحمد الأخرس</td><td>صفحة Calendar: اختيار المنطقة، التقويم، التفاصيل، وسوم عدم اليقين، التنزيلات، ومسار عرض إيفيا 2007 واختبار الهاتف ولوحة المفاتيح.</td><td>الشريحة 5</td></tr>
  <tr><td>تالا يوسف</td><td>تجربة المستخدم والتصميم والتواصل: التنقل، إمكانية الوصول، صفحة About، مراجعة الدليل، تصميم الشرائح، الأثر والخطوات القادمة.</td><td>الشريحة 7</td></tr>
  </tbody></table>
  <p><b>عمل مشترك:</b> اختيار الفكرة والطريقة، اختبار الموقع مع مستخدمين حقيقيين، والتدرّب على العرض.</p>

  <h2 style="margin-top:8mm">10. مسرد المصطلحات</h2>
  <table><thead><tr><th>بالعربية</th><th>بالإنجليزية</th><th>المعنى</th></tr></thead><tbody>
  <tr><td>بؤرة حرارية</td><td class="en">Hotspot</td><td>بكسل ساخن في صورة القمر الصناعي، غالبًا حريق.</td></tr>
  <tr><td>مواءمة</td><td class="en">Harmonization</td><td>تحويل أعداد MODIS إلى ما يعادلها بمقياس VIIRS.</td></tr>
  <tr><td>مقارنة بالمعتاد</td><td class="en">Anomaly</td><td>كم يختلف الشهر عن الوسيط لنفس الشهر في السنوات الأخرى.</td></tr>
  <tr><td>الوسيط</td><td class="en">Median</td><td>القيمة الوسطى: نصف السنوات أعلى منها ونصفها أدنى.</td></tr>
  <tr><td>الرتبة المئوية</td><td class="en">Percentile rank</td><td>«أعلى من 90% من السنوات» تعني أن سنة واحدة من كل عشر كانت أعلى.</td></tr>
  <tr><td>قوة الإشعاع الحراري</td><td class="en">FRP</td><td>الحرارة التي يطلقها الحريق بالميغاواط.</td></tr>
  <tr><td>نطاق الخطأ</td><td class="en">Uncertainty</td><td>المدى المتوقع للقيمة الحقيقية حول التقدير.</td></tr>
  <tr><td>سنوات الاختبار</td><td class="en">Test years</td><td>سنوات محجوزة لم تُستخدم في بناء النموذج، لقياس دقته بعدل.</td></tr>
  <tr><td>إنذار خاطئ</td><td class="en">False alarm</td><td>قال النموذج «أعلى من المعتاد» ولم يكن كذلك.</td></tr>
  <tr><td>شبه آني</td><td class="en">Near real time (NRT)</td><td>بيانات تصل خلال ساعات من مرور القمر.</td></tr>
  </tbody></table>
</section>

<section>
  <h2>11. المصادر والمراجع والإفصاح</h2>
  <p class="en" style="text-align:left">We acknowledge the use of data and/or imagery from NASA's Fire Information for Resource Management System (FIRMS) (https://earthdata.nasa.gov/firms), part of NASA's Land, Atmosphere Near real-time Capability for Earth observations (LANCE) (https://earthdata.nasa.gov/lance) and NASA's Earth Science Data and Information System (ESDIS).</p>
  <h3>المراجع</h3>
  <ul class="en" style="text-align:left;direction:ltr">
    <li>Giglio, L., Schroeder, W., &amp; Justice, C. O. (2016). The collection 6 MODIS active fire detection algorithm and fire products. Remote Sensing of Environment, 178, 31–41.</li>
    <li>Schroeder, W., Oliva, P., Giglio, L., &amp; Csiszar, I. A. (2014). The New VIIRS 375 m active fire detection data product. Remote Sensing of Environment, 143, 85–96.</li>
    <li>Davies, D. K., Ilavajhala, S., Wong, M. M., &amp; Justice, C. O. (2009). Fire Information for Resource Management System. IEEE TGRS, 47(1), 72–79.</li>
    <li>NASA Earthdata (2026). Transitioning from Suomi NPP VIIRS &amp; OMPS: What FIRMS Users Need to Know.</li>
    <li>Hoffleit, D., &amp; Warren, W. H. (1991). The Bright Star Catalogue, 5th Revised Ed. (via NASA HEASARC).</li>
  </ul>
  <h3>الصور والبرمجيات والخرائط</h3>
  <p>صورة الأرض: <span class="en">NASA GIBS / Blue Marble</span> · النجوم: <span class="en">Yale Bright Star Catalogue (NASA HEASARC)</span> · <span class="en">three.js (MIT)</span> · <span class="en">MapLibre GL JS (BSD-3)</span> · <span class="en">OpenFreeMap</span> · <span class="en">© OpenStreetMap contributors</span> · خط <span class="en">Inter (SIL OFL)</span> · لوحات Viridis و Cividis و ColorBrewer. لا نستخدم شعارات ناسا، وناسا لا تتبنّى هذا المشروع.</p>
  <h3>الإفصاح عن استخدام الذكاء الفائق (<span class="en">SI</span>)</h3>
  <div class="box">استخدمنا مساعد برمجة بالذكاء الفائق (<span class="en">Claude Code</span> من <span class="en">Anthropic</span>) لكتابة كود معالجة البيانات والموقع والنظام المباشر والشرائح وهذا الدليل، وفق تصميمنا وقراراتنا. الفريق اختار الطريقة، وتحقق من النتائج مقابل بيانات ناسا FIRMS، وتأكد من كل مرجع، وكتب العرض وتدرّب عليه.</div>
  <p class="small">الكود مفتوح المصدر (MIT): <span class="en">https://github.com/ahmedetk/jamra</span></p>
</section>
</body></html>"""
    out_html = REP / "Jamra_User_Guide_AR.html"
    out_html.write_text(html, encoding="utf-8")
    pdf = REP / "Jamra_User_Guide_AR.pdf"
    subprocess.run([EDGE, "--headless=new", "--disable-gpu", "--no-first-run", f"--user-data-dir={REP / '.edge-profile'}",
                    "--no-pdf-header-footer", "--virtual-time-budget=20000", f"--print-to-pdf={pdf}", out_html.as_uri()],
                   check=False, capture_output=True, timeout=180)
    print("wrote", out_html.name, pdf.name, pdf.stat().st_size if pdf.exists() else "missing")
    numbers = {"k_global": round(k, 1), "test_err_raw": pct(tc["M0"]["mdape"]), "test_err_harm": pct(tc[ch]["mdape"]),
               "test_err_year": pct(tc[ch]["annual"]["mdape"]), "hits": cc["hits"], "high_months": cc["hits"] + cc["misses"],
               "false_alarms": cc["false_alarms"], "small_grid_err": pct(sg[meth]["mdape"]), "small_preset_err": pct(sp[meth]["mdape"]),
               "k_jn": round(kjn, 2), "evia_2007_08": ev_v, "local_adopted": meth == "local"}
    (REP / "numbers_used.json").write_text(json.dumps(numbers, indent=1, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
