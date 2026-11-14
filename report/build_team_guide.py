"""Short team guide in everyday Arabic (for Team Astro Byte only, not for the judges).

Every number is read from the pipeline outputs (web/public/data/model_report.json, meta.json, areas/evia.json).
Screenshots: report/shots/g_*.png from scripts/guide_shots.mjs (numbered markers from web/public/data/guide.json).
Usage: python report/build_team_guide.py  ->  report/Jamra_Guide_Team_AR.html and .pdf
Written with the help of an AI coding assistant (Claude Code by Anthropic).
"""
import json
import subprocess
from pathlib import Path

from PIL import Image

REP = Path(__file__).resolve().parent
ROOT = REP.parent
WEB = ROOT / "web" / "public" / "data"
SHOTS = REP / "shots"
IMG = REP / "img_team"
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
SITE = "https://ahmedetk.github.io/jamra/"
SHOT_FILES = {"home": "g_home.png", "cal_top": "g_cal_top.png", "cal_chart": "g_cal_chart.png", "cal_main": "g_cal_main.png",
              "cal_detail": "g_cal_detail.png", "alerts": "g_alerts.png", "live": "g_live.png", "validation": "g_validation.png",
              "about": "g_about.png"}


def pct(x):
    return f"{round(x * 100)}%"


def prep_images():
    IMG.mkdir(exist_ok=True)
    out = {}
    for key, name in SHOT_FILES.items():
        src = SHOTS / name
        if not src.exists():
            print("missing screenshot", name)
            continue
        im = Image.open(src).convert("RGB")
        if im.width > 1200:
            im = im.resize((1200, int(im.height * 1200 / im.width)), Image.LANCZOS)
        im.save(IMG / f"{key}.jpg", quality=84)
        out[key] = f"img_team/{key}.jpg"
    return out


def main():
    R = json.loads((WEB / "model_report.json").read_text(encoding="utf-8"))
    meta = json.loads((WEB / "meta.json").read_text(encoding="utf-8"))
    evia = json.loads((WEB / "areas" / "evia.json").read_text(encoding="utf-8"))
    V, ch = R["validation"], R["chosen_model"]
    tc, cc, cr = V["test_countries"], V["confusion_countries"]["harmonized"], V["confusion_countries"]["raw_modis"]
    sp, sg = V["small_regions"]["presets"], V["small_regions"]["grid_1deg"]
    meth = "local" if V["decision"]["adopt_local_factor"] else "baseline"
    u, fr = R["uncertainty"], R["frp_test"]
    k, kjn = R["viirs_vs_modis_ratio"], R["noaa20_to_snpp"]["global"]
    ca = R["colour_agreement"]
    i07 = (2007 - 2003) * 12 + 7
    ev_v, ev_lo, ev_hi = round(evia["harm"][i07]), round(evia["lo"][i07]), round(evia["hi"][i07])
    others = sorted(evia["harm"][(y - 2003) * 12 + 7] for y in range(2003, 2026) if y != 2007)
    n = len(others)
    ev_med = others[n // 2] if n % 2 else (others[n // 2 - 1] + others[n // 2]) / 2
    ev_x = round(ev_v / ev_med, 1)
    ty = f"{V['test_years'][0]}–{V['test_years'][-1]}"
    img = prep_images()

    def shot(key, cap):
        return f'<figure><img src="{img[key]}" alt=""><figcaption>{cap}</figcaption></figure>' if key in img else ""

    def keys(rows):
        return '<ol class="keys">' + "".join(f"<li><b>{a}</b> {b}</li>" for a, b in rows) + "</ol>"

    html = f"""<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8">
<title>جمرة: دليل الفريق</title>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Arabic:wght@400;600;700&display=swap" rel="stylesheet">
<style>
@page {{ size: A4; margin: 14mm 14mm 16mm; }}
* {{ box-sizing: border-box; }}
body {{ font-family: "IBM Plex Sans Arabic", "Segoe UI", Tahoma, sans-serif; color: #2B2B2B; font-size: 12pt; line-height: 1.7; margin: 0; background: #fff; }}
h1 {{ font-size: 24pt; margin: 0 0 2mm; }}
h2 {{ font-size: 16pt; margin: 7mm 0 2mm; padding-bottom: 1mm; border-bottom: 2px solid #F4511E; }}
h3 {{ font-size: 13pt; margin: 5mm 0 1mm; }}
p {{ margin: 0 0 2.5mm; }}
.en {{ direction: ltr; unicode-bidi: isolate; font-family: "Segoe UI", Arial, sans-serif; }}
.sub {{ color: #6B6A66; margin-bottom: 4mm; }}
figure {{ margin: 3mm 0; break-inside: avoid; }}
figure img {{ width: 100%; border: 1px solid #E4E1DA; border-radius: 4px; display: block; }}
figcaption {{ font-size: 10pt; color: #6B6A66; margin-top: 1mm; }}
.keys {{ margin: 2mm 0 3mm; padding-inline-start: 7mm; }}
.keys li {{ margin-bottom: 1.2mm; }}
.keys li::marker {{ font-weight: 700; color: #D9430F; }}
ul {{ margin: 1mm 0 3mm; padding-inline-start: 6mm; }}
li {{ margin-bottom: 1mm; }}
.box {{ background: #F7F6F2; border-right: 4px solid #F4511E; padding: 3mm 4mm; margin: 3mm 0; border-radius: 4px; }}
table {{ width: 100%; border-collapse: collapse; margin: 2mm 0 4mm; font-size: 11pt; }}
th, td {{ border-bottom: 1px solid #E4E1DA; padding: 1.8mm 2mm; text-align: right; vertical-align: top; }}
th {{ background: #F7F6F2; }}
td.num {{ font-weight: 700; white-space: nowrap; }}
.page {{ break-before: page; }}
.qa b {{ display: block; margin-top: 2.5mm; }}
</style></head><body>

<h1>جمرة: دليل الفريق</h1>
<p class="sub">دليل قصير إلنا كفريق Astro Byte، عشان نفهم الموقع ونعرضه. مش للحكام. الموقع: <span class="en">{SITE}</span></p>

<h2>1. شو بيعمل الموقع؟</h2>
<p>ناسا عندها قمرين بيشوفوا الحرائق: القديم <span class="en">MODIS</span> (من 2003) والجديد <span class="en">VIIRS</span> (من 2012). الجديد أحدّ نظر، فبيلقط بؤر أكتر بحوالي <b>{k:.1f}×</b>.</p>
<p>إذا حطّينا الأرقام ورا بعض بيطلع كأن الحرائق زادت فجأة سنة 2012، وهاد غلط. جمرة بتحوّل أرقام <span class="en">MODIS</span> القديمة لمقياس <span class="en">VIIRS</span>، فبيصير عنا سجل واحد عادل من 2003 لليوم.</p>
<p>وفوق هيك بتقارن كل شهر مع المعتاد لنفس الشهر، وبتجيب بيانات ناسا الجديدة كل 3 ساعات، عشان نعرف إذا الشهر الحالي غير عادي.</p>

<h2>2. الصفحات</h2>
<ul>
<li><b>Home:</b> الواجهة. فيها جملة وحدة، وزرّين، وشارة البيانات المباشرة، ورقمين بيقولوا إنه الطريقة شغالة.</li>
<li><b>Calendar:</b> أهم صفحة. بتختار منطقة وفترة، وبتشوف رسم السنين، والتقويم (سنين × شهور)، وتفاصيل أي شهر، والتنزيلات.</li>
<li><b>Alerts:</b> بطاقة لكل منطقة: هل الشهر هاد أعلى من المعتاد؟ ومعها حالة البيانات (محدّثة، متأخرة، أو في مشكلة).</li>
<li><b>Live Data:</b> آخر البؤر من ناسا على الخريطة وبجدول، وفيك تنزّلها <span class="en">CSV</span>.</li>
<li><b>Validation:</b> الدليل إنه الطريقة شغالة: أرقام الاختبار، والرسوم، والطريقة بـ 3 خطوات، والحدود.</li>
<li><b>About:</b> الفريق، والمصادر، والمراجع، وإفصاح الذكاء الاصطناعي.</li>
</ul>

<h2 class="page">3. الأزرار، صفحة صفحة</h2>
<p>الأرقام بالصور هي نفس الأرقام بالقوائم.</p>

<h3>Home</h3>
{shot("home", "الصفحة الرئيسية")}
{keys([("القائمة:", "اكبس هون عشان تروح لأي صفحة."),
       ("شارة Live:", "بتورجيك إذا بيانات ناسا محدّثة. اكبسها بتفتح Alerts."),
       ("الكرة الأرضية:", "اسحبها بإيدك عشان تلفّ، والنقاط البرتقالية هي بؤر آخر 7 أيام."),
       ("Open the Calendar:", "اكبس هون عشان تفتح التقويم."),
       ("See Live Alerts:", "اكبس هون عشان تشوف التنبيهات."),
       ("سطر البيانات المباشرة:", "كم بؤرة صار في آخر 7 أيام.")])}

<h3 class="page">Calendar: فوق</h3>
{shot("cal_top", "اختيار المنطقة والخريطة")}
{keys([("Example: Evia, August 2007:", "اكبس هون عشان يفتحلك المثال الجاهز للعرض."),
       ("Fire areas:", "اكبس هون عشان تختار منطقة حرائق مشهورة (إيفيا، رودس…)."),
       ("Countries:", "اكبس هون عشان تختار دولة من الثمانية."),
       ("Draw:", "اكبس هون عشان ترسم منطقة على الخريطة (شكل أو دائرة)."),
       ("Coordinates:", "اكبس هون عشان تكتب خط الطول والعرض ونصف القطر."),
       ("معلومات المنطقة:", "اسمها، ومعامل التحويل، ونسبة الخطأ."),
       ("الخريطة:", "قرّب وبعّد، والخط البرتقالي هو المنطقة المختارة."),
       ("Back to globe:", "اكبس هون عشان ترجع الخريطة كرة."),
       ("24 h / 7 days / Off:", "اكبس هون عشان تختار أي بؤر مباشرة تبيّن على الخريطة.")])}

<h3 class="page">Calendar: الرسم والتقويم</h3>
{shot("cal_chart", "رسم السنين")}
{keys([("Raw / Harmonized:", "اكبس Raw بتشوف القفزة الوهمية سنة 2012، واكبس Harmonized بتختفي. هاي أهم لقطة بالعرض.")])}
{shot("cal_main", "البطاقات والتقويم والتنزيلات")}
{keys([("From / To:", "اختار من أي سنة لأي سنة (لحد 2026)."),
       ("فلتر الغاز والصناعة:", "بيشيل البؤر الثابتة (مصانع، شعلات غاز). طفّيه وشغّله وشوف الرقم كيف بيتغيّر."),
       ("البطاقات:", "شهر الذروة، الآن مقابل المعتاد، أنشط سنة، الإنذار المبكر، ومجموع الكشوفات."),
       ("Hotspots / Anomaly:", "اكبس Anomaly عشان تشوف كل شهر أعلى ولا أقل من المعتاد (برتقالي أعلى، أزرق أقل)."),
       ("Months / Weeks:", "اكبس Weeks عشان تشوف 52 أسبوع بدل 12 شهر."),
       ("الألوان:", "اختار لوحة ألوان. الافتراضية مريحة لعمى الألوان، وفي كمان Viridis وCividis وYlOrRd."),
       ("التقويم:", "كل مربع شهر. اكبس على أي مربع عشان تفتح تفاصيله. المربعات المخططة يعني «مقدّرة من MODIS»."),
       ("Download CSV:", "اكبس هون عشان تنزّل الأرقام كجدول."),
       ("Summary PDF:", "اكبس هون عشان تنزّل ملخص صفحة وحدة (وفي كمان PNG).")])}

<h3 class="page">Calendar: تفاصيل الشهر</h3>
{shot("cal_detail", "تفاصيل الشهر")}
{keys([("تفاصيل الشهر:", "الرقم، ومقارنته مع الوسيط (المعتاد)، ومع نفس الشهر بالسنين التانية، و«estimated from MODIS ±%» إذا الشهر قبل 2012.")])}

<h3>Alerts</h3>
{shot("alerts", "صفحة التنبيهات")}
{keys([("حالة البيانات:", "آخر تحديث من ناسا: أخضر يعني تمام، برتقالي غامق يعني متأخر، أحمر يعني في مشكلة."),
       ("البطاقات:", "منطقة بكل بطاقة، ومستواها: عادي، مرتفع، عالي، أو شديد. اكبس عليها بتفتح التقويم."),
       ("ملاحظة المقياس:", "بتشرح إنه كل الأرقام على مقياس VIIRS."),
       ("مصادر البيانات:", "من وين إجت البيانات.")])}

<h3 class="page">Live Data</h3>
{shot("live", "صفحة البيانات المباشرة")}
{keys([("اختيار المنطقة:", "نفس طرق التقويم."),
       ("الخريطة:", "البؤر الجديدة برتقالي غامق، والأقدم أفتح."),
       ("الفترة:", "اختار آخر يوم أو آخر كم يوم."),
       ("Show latest NASA FIRMS data:", "اكبس هون عشان تجيب آخر البيانات."),
       ("Download CSV:", "اكبس هون عشان تنزّل البؤر كجدول."),
       ("الجدول:", "كل بؤرة: الوقت، والمكان، وقوة النار (FRP).")])}

<h3 class="page">Validation</h3>
{shot("validation", "أعلى صفحة التحقق")}
{keys([("الأرقام الأساسية:", "خلاصة الاختبار على سنين ما شافها النموذج."),
       ("الأشهر العالية:", "كم شهر عالي لقطنا، وكم فاتنا، وكم إنذار غلط."),
       ("المناطق الصغيرة:", "المعامل المحلي مقابل معامل الدولة."),
       ("مناطق الحرائق:", "النتيجة لكل منطقة لحالها.")])}
<p>تحت فيه كمان: الخطأ لكل طريقة، والمتوقع مقابل الفعلي، وثبات النسبة عبر السنين، والخطأ لكل دولة، ومقارنة الطرق، والحدود.</p>

<h3>About</h3>
{shot("about", "صفحة من نحن")}
{keys([("الفريق:", "الخمسة وأدوارهم."),
       ("شكر ناسا FIRMS:", "النص الرسمي اللي لازم يكون موجود."),
       ("GitHub:", "اكبس هون عشان تفتح الكود.")])}

<h2 class="page">4. كيف بتشتغل البيانات (ببساطة)</h2>
<ul>
<li><b>من وين؟</b> كل البيانات من <span class="en">NASA FIRMS</span>: الأرشيف السنوي للتاريخ، والـ <span class="en">API</span> للأيام الأخيرة.</li>
<li><b>ليش منحوّل MODIS لـ VIIRS؟</b> لأنه VIIRS هو القمر الحالي والجاي، والبيانات المباشرة كلها VIIRS. فمنحط القديم على مقياس الجديد، بدل ما نخرّب الجديد.</li>
<li><b>كيف منحوّل؟</b> بسنين التداخل (من 2012) القمرين شافوا نفس الحرائق. منحسب لكل دولة ولكل شهر: كم بؤرة VIIRS مقابل كل بؤرة MODIS. المناطق الصغيرة إلها معامل لحالها، بس بيقرب من معامل الدولة إذا بؤرها قليلة.</li>
<li><b>شو يعني «estimated from MODIS ±%»؟</b> يعني الرقم قبل 2012 مش مقاس بـ VIIRS، هو تقدير من MODIS. والـ ± هو هامش الخطأ المعتاد: حوالي <b>±{round(u['monthly_rel'] * 100)}%</b> لشهر بدولة، و<b>±{round(u['small_regions_rel'] * 100)}%</b> لمنطقة صغيرة. وهاي المربعات بتطلع مخططة بالتقويم.</li>
<li><b>كل قديش بيتحدّث؟</b> كل 3 ساعات بيجيب بيانات ناسا الجديدة لحاله (<span class="en">GitHub Actions</span>)، وكل شهر بيعيد بناء الأرشيف كله.</li>
<li><b>S-NPP وقف؟</b> القمر S-NPP وقف بـ 2 نوفمبر 2026، فالبيانات المباشرة صارت من NOAA-20 (نفس الجهاز)، ومنضربها بـ <b>×{kjn:.2f}</b> عشان تضل على نفس المقياس.</li>
</ul>

<h2>5. أرقام لازم نحفظها</h2>
<table>
<tr><th>الرقم</th><th>شو معناه</th></tr>
<tr><td class="num">{k:.1f}×</td><td>VIIRS بيلقط بؤر أكتر من MODIS بهالقد (بسنين التداخل).</td></tr>
<tr><td class="num">{pct(tc['M0']['mdape'])} ← {pct(tc[ch]['mdape'])}</td><td>الخطأ الشهري قبل التحويل وبعده (سنين الاختبار {ty}).</td></tr>
<tr><td class="num">{pct(tc[ch]['annual']['mdape'])}</td><td>الخطأ على مجموع السنة لدولة.</td></tr>
<tr><td class="num">{cc['hits']} من {cc['hits'] + cc['misses']}</td><td>الأشهر العالية اللي لقطناها (MODIS الخام لقط {cr['hits']} بس)، مع {cc['false_alarms']} إنذار غلط.</td></tr>
<tr><td class="num">{pct(sg[meth]['mdape'])} / {pct(sp[meth]['mdape'])}</td><td>الخطأ بالمناطق الصغيرة: مربعات 1° / مناطق الحرائق التسعة.</td></tr>
<tr><td class="num">{ca['same_colour_pct']:.0f}%</td><td>نسبة الأشهر اللي لونها بالتقويم نفس لون VIIRS الحقيقي (بدون تحويل: {ca['without_harmonization_pct']:.0f}%).</td></tr>
<tr><td class="num">±{round(u['monthly_rel'] * 100)}% / ±{round(u['annual_rel'] * 100)}%</td><td>هامش الخطأ لشهر / لسنة.</td></tr>
<tr><td class="num">×{kjn:.2f}</td><td>معامل NOAA-20 ← S-NPP للبيانات المباشرة.</td></tr>
<tr><td class="num">{fr['pooled_cv_frp_ratio']:.2f} مقابل {fr['pooled_cv_count_ratio']:.2f}</td><td>اختبار FRP: نسبة FRP أقل ثباتًا من العدد، فاستخدمنا العدد.</td></tr>
<tr><td class="num">{ev_v:,} ({ev_x}×)</td><td>إيفيا آب 2007: عدد البؤر المقدّر (بين {ev_lo:,} و{ev_hi:,}) وقديش أكبر من وسيط آب.</td></tr>
<tr><td class="num">8 دول · من 2003</td><td>البرتغال، إسبانيا، اليونان، تركيا، قبرص، لبنان، الأردن، فلسطين.</td></tr>
</table>

<h2 class="page">6. خطوات العرض (دقيقتين)</h2>
<ol>
<li><b>Home</b>: «هاي جمرة: 20 سنة من بيانات حرائق ناسا بسجل واحد عادل». <span class="en">{SITE}</span></li>
<li>اكبس <b>Open the Calendar</b>.</li>
<li>بالرسم اكبس <b>Raw</b>: «شوفوا القفزة سنة 2012، هاي مش حرائق، هاي قمر أحدّ». بعدها <b>Harmonized</b>: «اختفت».</li>
<li>اكبس <b>Example: Evia, August 2007</b>.</li>
<li>بتفاصيل الشهر: «{ev_x}× أكتر من آب العادي، ومكتوب estimated from MODIS مع هامش الخطأ».</li>
<li>افتح <b>Validation</b>: «اختبرناها على سنين مخفية: الخطأ نزل من {pct(tc['M0']['mdape'])} لـ {pct(tc[ch]['mdape'])}، ولقطنا {cc['hits']} من {cc['hits'] + cc['misses']} شهر عالي».</li>
<li>افتح <b>Alerts</b>: «كل بطاقة بتقول إذا الشهر الحالي أعلى من المعتاد، ومعها حالة البيانات».</li>
<li>افتح <b>Live Data</b> ← اكبس <b>Show latest NASA FIRMS data</b> ← <b>Download CSV</b>: «وهاي البيانات المباشرة من ناسا كل 3 ساعات».</li>
</ol>
<div class="box">نصيحة: افتحوا الموقع قبل العرض بدقيقة عشان يتحمّل ويتخزّن. ولو النت ضعيف، الموقع بيفتح من آخر نسخة محفوظة.</div>

<h2>7. أسئلة متوقعة من الحكام</h2>
<div class="qa">
<b>ليش ما استخدمتوا VIIRS بس؟</b>
<p>لأنه VIIRS بلش 2012، فبنخسر 9 سنين، منها حرائق اليونان 2007.</p>
<b>ليش حوّلتوا القديم للجديد مش العكس؟</b>
<p>لأنه البيانات المباشرة كلها VIIRS، فلازم التاريخ يكون على نفس مقياسها عشان نقارن «الآن» مع «المعتاد».</p>
<b>كيف بتعرفوا إنها شغالة؟</b>
<p>خبّينا سنين {ty} وما استخدمناها وإحنا نبني النموذج، وبعدين اختبرنا عليها: الخطأ نزل من {pct(tc['M0']['mdape'])} لـ {pct(tc[ch]['mdape'])}، ولقطنا {cc['hits']} من {cc['hits'] + cc['misses']} شهر عالي.</p>
<b>ليش بلّشتوا من 2003؟</b>
<p>لأنا استخدمنا MODIS على القمر Aqua بس: أول سنة كاملة إله 2003، وبيمرق بنفس وقت VIIRS بعد الضهر، فبيشوفوا نفس الحرائق بنفس الساعة.</p>
<b>والنسبة بين القمرين ثابتة؟</b>
<p>فحصناها سنة بسنة، واستخدمنا بس سنين التداخل الثابتة للمعايرة (رسم «Is the VIIRS / MODIS ratio stable over time?» بصفحة Validation).</p>
<b>ليش عدد البؤر مش FRP؟</b>
<p>اختبرناها: نسبة FRP بين القمرين أقل ثباتًا ({fr['pooled_cv_frp_ratio']:.2f} مقابل {fr['pooled_cv_count_ratio']:.2f})، فضلّينا على العدد.</p>
<b>والمناطق الصغيرة؟</b>
<p>إلها معامل لحالها بيقرب من معامل الدولة إذا البؤر قليلة، وهامش الخطأ فيها أكبر (±{round(u['small_regions_rel'] * 100)}%)، ومكتوب هيك على الموقع.</p>
<b>كل بؤرة يعني حريق غابة؟</b>
<p>لأ. في حرق زراعي، وشعلات غاز، ومصانع. عنا فلتر بيشيل المصادر الثابتة، ومكتوب بالحدود.</p>
<b>منطقة برّا الدول الثمانية؟</b>
<p>بتطلع رسالة واضحة إنه التاريخ المعدّل بس للدول الثمانية، وبرّاها في بيانات مباشرة بس، مع رابط لأقرب منطقة.</p>
<b>هل هي خدمة طوارئ؟</b>
<p>لأ. بيانات الأقمار بتتأخر ساعات. هي أداة للإنذار المبكر والتخطيط.</p>
<b>استخدمتوا ذكاء اصطناعي؟</b>
<p>آه، ومكتوب بصفحة About: الكود كُتب بمساعد برمجة (Claude Code من Anthropic) بتوجيه من أحمد اتكيدك، اللي صمّم الموقع، وجهّز واجهة ناسا وGitHub Actions والنشر، واختبر كل إصدار. والفريق اختار الطريقة العلمية وتحقق من كل النتائج.</p>
<b>الألوان مناسبة لعمى الألوان؟</b>
<p>آه. اللوحة الافتراضية بتتدرّج بالفتاحة، وفي Viridis وCividis، والمقارنة دايمًا معها كلمة مكتوبة مش بس لون.</p>
</div>
</body></html>"""
    out_html = REP / "Jamra_Guide_Team_AR.html"
    out_html.write_text(html, encoding="utf-8")
    pdf = REP / "Jamra_Guide_Team_AR.pdf"
    subprocess.run([EDGE, "--headless=new", "--disable-gpu", "--no-first-run", f"--user-data-dir={REP / '.edge-profile'}",
                    "--no-pdf-header-footer", "--virtual-time-budget=20000", f"--print-to-pdf={pdf}", out_html.as_uri()],
                   check=False, capture_output=True, timeout=180)
    print("wrote", out_html.name, pdf.name, pdf.stat().st_size if pdf.exists() else "missing")


if __name__ == "__main__":
    main()
