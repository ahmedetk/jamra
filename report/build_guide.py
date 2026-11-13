"""Build the Arabic user guide (RTL, A4): report/Jamra_User_Guide_AR.html -> .pdf (Edge headless).

All numbers are read from web/public/data/model_report.json and the area files.
Screenshots come from scripts/guide_shots.sh (numbered callouts, ?guide=1).
Usage: python report/build_guide.py
Written with the help of an SI coding assistant (Claude Code); text reviewed by Team Astro Byte.
"""
import json
import subprocess
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
REP = ROOT / "report"
SHOTS = REP / "shots"
IMG = REP / "img"
WEB = ROOT / "web" / "public" / "data"
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
SITE = "https://ahmedetk.github.io/jamra/"


def autocrop(src, dst, top=0, bottom=None, max_w=1280):
    im = Image.open(src).convert("RGB")
    w, h = im.size
    if bottom is None:  # cut just below the dark footer band
        bottom = h
        for y in range(h - 1, 0, -1):
            r, g, b = im.getpixel((5, y))
            if r < 40 and g < 50 and b < 80:
                bottom = y + 1
                break
    im = im.crop((0, top, w, min(bottom, h)))
    if im.width > max_w:
        im = im.resize((max_w, int(im.height * max_w / im.width)))
    im.save(dst, quality=85)
    return dst.name


def prep_images():
    IMG.mkdir(exist_ok=True)
    out = {}
    out["home"] = autocrop(SHOTS / "home.png", IMG / "home.jpg")
    out["cal_top"] = autocrop(SHOTS / "calendar_top.jpg", IMG / "cal_top.jpg", bottom=420)
    out["cal_main"] = autocrop(SHOTS / "calendar.png", IMG / "cal_main.jpg", top=650, bottom=2150)
    out["cal_detail"] = autocrop(SHOTS / "calendar.png", IMG / "cal_detail.jpg", top=2150, bottom=3330)
    for k in ("alerts", "live", "how", "validation", "limits", "credits", "anomaly"):
        out[k] = autocrop(SHOTS / f"{k}.png", IMG / f"{k}.jpg")
    out["mobile_detail"] = autocrop(SHOTS / "mobile_detail.png", IMG / "mobile_detail.jpg", bottom=10**6)
    out["home_harm"] = autocrop(SHOTS / "home_harm.png", IMG / "home_harm.jpg", top=0, bottom=980)
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
    i07 = (2007 - 2003) * 12 + 7
    ev_v = round(evia["harm"][i07])
    ev_lo, ev_hi = round(evia["lo"][i07]), round(evia["hi"][i07])
    others = sorted(evia["harm"][(y - 2003) * 12 + 7] for y in range(2003, 2026) if y != 2007)
    n = len(others)
    ev_med = (others[n // 2] if n % 2 else (others[n // 2 - 1] + others[n // 2]) / 2)
    ev_x = round(ev_v / ev_med, 1)
    img = prep_images()
    through = meta["data_through"]

    def fig(key, cap):
        return f'<figure><img src="img/{img[key]}" alt=""><figcaption>{cap}</figcaption></figure>'

    def callouts(items):
        rows = "".join(f'<tr><td class="n">{i}</td><td class="nm">{nm}</td><td>{what}</td><td>{why}</td></tr>'
                       for i, (nm, what, why) in enumerate(items, 1))
        return f'<table class="co"><thead><tr><th>#</th><th>الاسم</th><th>ماذا يفعل</th><th>لماذا هو موجود</th></tr></thead><tbody>{rows}</tbody></table>'

    html = f"""<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8">
<title>دليل استخدام جمرة · Jamra User Guide (Arabic)</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Arabic:wght@400;600;700&display=swap" rel="stylesheet">
<style>
@page {{ size: A4; margin: 16mm 14mm 18mm; }}
* {{ box-sizing: border-box; }}
body {{ font-family: "IBM Plex Sans Arabic", "Segoe UI", Tahoma, sans-serif; color: #111827; font-size: 11.5pt; line-height: 1.75; margin: 0; }}
h1 {{ font-size: 26pt; margin: 0 0 6mm; }} h2 {{ font-size: 17pt; color: #111827; border-bottom: 3px solid #E2631C; padding-bottom: 2mm; margin: 0 0 4mm; }}
h3 {{ font-size: 13pt; margin: 5mm 0 2mm; }}
section {{ page-break-before: always; }} section.cover {{ page-break-before: auto; }}
.cover {{ height: 255mm; display: flex; flex-direction: column; justify-content: center; text-align: center; }}
.cover .t {{ font-size: 40pt; font-weight: 700; color: #E2631C; }} .cover .s {{ font-size: 15pt; }}
.en {{ direction: ltr; unicode-bidi: isolate; font-family: "Segoe UI", Arial, sans-serif; }}
figure {{ margin: 3mm 0; page-break-inside: avoid; }} figure img {{ width: 100%; border: 1px solid #d9dee7; border-radius: 4px; }}
figcaption {{ font-size: 9.5pt; color: #5f6b80; }}
table {{ width: 100%; border-collapse: collapse; font-size: 10pt; margin: 2mm 0 4mm; page-break-inside: auto; }}
th, td {{ border: 1px solid #d9dee7; padding: 1.6mm 2mm; vertical-align: top; text-align: right; }}
th {{ background: #eef0f4; }} tr {{ page-break-inside: avoid; }}
td.n {{ width: 8mm; text-align: center; font-weight: 700; color: #fff; background: #E2631C; }}
td.nm {{ width: 32mm; font-weight: 600; }}
.box {{ background: #F8FAFC; border-right: 4px solid #E2631C; padding: 3mm 4mm; margin: 3mm 0; }}
.kpis {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 3mm; }}
.kpi {{ border: 1px solid #d9dee7; border-radius: 6px; padding: 3mm; }} .kpi b {{ display: block; font-size: 16pt; color: #E2631C; }}
.small {{ font-size: 9.5pt; color: #5f6b80; }}
ol li, ul li {{ margin-bottom: 1.5mm; }}
.map {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 2mm; text-align: center; }}
.map div {{ border: 2px solid #111827; border-radius: 6px; padding: 2mm; font-weight: 600; }}
.map div.h {{ background: #111827; color: #fff; }}
</style></head><body>

<section class="cover">
  <img src="img/earth.webp" alt="" style="width:62mm;height:62mm;margin:0 auto 6mm">
  <div class="t"><img src="img/logo.png" alt="" style="width:16mm;height:16mm;vertical-align:middle;margin-left:3mm">جمرة · <span class="en">Jamra</span></div>
  <p class="s">تقويم موحَّد لنشاط الحرائق من قمرَي <span class="en">MODIS</span> و<span class="en">VIIRS</span> مع إنذار مبكر مباشر</p>
  <h1 style="margin-top:10mm">دليل استخدام الموقع</h1>
  <p class="s">فريق <span class="en">Astro Byte</span> · <span class="en">NASA Space Apps Challenge 2026</span></p>
  <p>شهد فرّاج · أحمد اتكيدك · آية سلمان · أحمد الأخرس · تالا يوسف</p>
  <p class="small">صورة الأرض: <span class="en">NASA GIBS / Blue Marble</span> · مبني لتحدّي <span class="en">NASA Space Apps Challenge 2026</span> · ليس منتجًا رسميًا لناسا</p>
  <p class="small">الموقع: <span class="en">{SITE}</span> · البيانات حتى <span class="en">{through}</span> · جميع الأرقام في هذا الدليل محسوبة من بياناتنا</p>
</section>

<section>
  <h2>1. ما هي جمرة؟</h2>
  <h3>المشكلة: «قفزة وهمية» في عدد الحرائق</h3>
  <p>ترصد الأقمار الصناعية الحرائق على شكل «بؤر حرارية» (<span class="en">hotspots</span>)، أي بكسلات ساخنة في صور القمر. منذ عام 2000 يرصدها جهاز <span class="en">MODIS</span> بدقة 1 كم. وفي 2012 انضم جهاز أدقّ هو <span class="en">VIIRS</span> بدقة 375 م، فصار يرى حرائق أصغر وبؤرًا أكثر للحريق نفسه.</p>
  <p>في دولنا الثماني سجّل <span class="en">VIIRS</span> نحو <b>{k:.1f} أضعاف</b> البؤر التي سجّلها <span class="en">MODIS</span> في الأشهر نفسها. لذلك إذا وصلنا السجلَّين كما هما، يظهر ارتفاع كبير بعد 2012 لم يحدث فعلًا على الأرض: سببه دقة الجهاز الجديد، لا زيادة الحرائق.</p>
  <h3>الحل</h3>
  <p>جمرة «تُوائم» السجل القديم: تحوّل أعداد <span class="en">MODIS</span> قبل 2012 إلى ما يعادلها بمقياس <span class="en">VIIRS</span>، فيصبح لدينا سجل واحد عادل من 2003 حتى اليوم. ثم تقارن كل شهر بالمعتاد له في السنوات الأخرى، وتتابع بيانات ناسا الجديدة كل 3 ساعات لتنبّه إذا كان الشهر الحالي غير عادي.</p>
  {fig("home_harm", "الصفحة الرئيسية: الرسم البياني بوضع «المُواءَم» (Harmonized). الأعمدة المخطَّطة قبل 2012 مقدَّرة من MODIS.")}
  <div class="box">جمرة ليست خدمة طوارئ: بيانات الأقمار تصل بتأخير ساعات. في الطوارئ اتصل برقم الطوارئ المحلي.</div>
</section>

<section>
  <h2>2. لمن صُمِّمت جمرة؟</h2>
  <h3>المستخدمون الأساسيون</h3>
  <table><thead><tr><th>المستخدم</th><th>ماذا يستفيد</th></tr></thead><tbody>
  <tr><td>مديرو الطوارئ وفرق الإنذار المبكر</td><td>يعرفون فورًا إن كان هذا الشهر أعلى من المعتاد في منطقتهم (صفحة التنبيهات وبطاقة «الإنذار المبكر الآن»).</td></tr>
  <tr><td>فرق الإطفاء</td><td>يرون أحدث البؤر على الخريطة وفي جدول من واجهة ناسا <span class="en">FIRMS</span> مباشرة.</td></tr>
  <tr><td>مديرو الأراضي والغابات</td><td>يعرفون متى يبدأ موسم الحرائق ومتى يبلغ ذروته، وأي السنوات كانت الأسوأ، على مقياس واحد عادل.</td></tr>
  <tr><td>العلماء والباحثون</td><td>سجل متّسق من 2003 حتى اليوم مع نطاق الخطأ، وتنزيل البيانات بصيغة <span class="en">CSV</span>، وطريقة مفتوحة ونتائج اختبار مستقل.</td></tr>
  </tbody></table>
  <h3>المستفيدون غير المباشرين</h3>
  <p>المجالس القروية والبلديات والمزارعون يستفيدون عبر السلطات المحلية والدفاع المدني الذين يستخدمون جمرة: إنذار أبكر، وتخطيط أفضل لموسم الحرائق.</p>
  <h2 style="margin-top:8mm">3. خريطة الموقع</h2>
  <p>الموقع ثماني صفحات، لكل صفحة رابط مستقل. شريط التنقل نفسه في أعلى كل صفحة، والصفحة الحالية مميَّزة. الضغط على شعار جمرة يعيدك إلى الرئيسية. المنطقة والفترة والشهر المختارة تنتقل معك بين الصفحات عبر الرابط.</p>
  <div class="map">
    <div class="h">الرئيسية<br><span class="en">/jamra/</span></div><div>التقويم<br><span class="en">/calendar/</span></div><div>التنبيهات<br><span class="en">/alerts/</span></div><div>البيانات المباشرة<br><span class="en">/live/</span></div>
    <div>كيف تعمل<br><span class="en">/how-it-works/</span></div><div>التحقق<br><span class="en">/validation/</span></div><div>الحدود<br><span class="en">/limits/</span></div><div>المصادر والفريق<br><span class="en">/credits/</span></div>
  </div>
  <p class="small">الروابط القديمة من الموقع ذي الصفحة الواحدة (مثل <span class="en">#calendar</span>) تُحوَّل تلقائيًا إلى الصفحة الجديدة مع إبقاء خياراتك. ويمكن تثبيت الموقع على الهاتف كتطبيق (<span class="en">PWA</span>) ويعمل دون إنترنت من آخر نسخة محفوظة.</p>
</section>

<section>
  <h2>4. صفحة بصفحة</h2>
  <h3>4.1 الرئيسية (<span class="en">Home</span>)</h3>
  <p><b>الهدف:</b> فهم المشكلة في ثوانٍ ورؤية الحل. <b>لمن:</b> كل زائر جديد ولجان التحكيم.</p>
  {fig("home", "الصفحة الرئيسية مع أرقام الأزرار.")}
  {callouts([
    ("شريط التنقل", "ينقلك بين الصفحات الثماني.", "لكل جزء من العمل صفحة واضحة برابط خاص."),
    ("شارة الحالة", "تُظهر «مباشر · حُدِّث قبل …» أو «متأخر» أو «قديم».", "حتى تعرف فورًا مدى حداثة بيانات ناسا."),
    ("اختيار المنطقة", "يغيّر المنطقة المعروضة في الرسم.", "لترى القفزة الوهمية في دولتك أو منطقتك."),
    ("زر «خام» (Raw)", "يعرض السجل كما هو: MODIS حتى 2011 ثم VIIRS.", "ليُظهر القفزة الوهمية بعد 2012."),
    ("زر «مُواءَم» (Harmonized)", "يعرض السجل بعد التحويل إلى مقياس VIIRS.", "ليُظهر أن القفزة تختفي بعد المواءمة."),
    ("الرسم السنوي", "عدد البؤر لكل سنة؛ مرّر المؤشر لترى الرقم.", "صورة سريعة لأعوام الحرائق الكبرى."),
    ("«جرّب مثال إيفيا 2007»", "يفتح التقويم على إيفيا وشهر آب 2007 مع التفاصيل.", "مثال جاهز يوضح قيمة مقدَّرة من MODIS مع نطاق خطئها."),
  ])}
</section>

<section>
  <h3>4.2 التقويم (<span class="en">Calendar</span>)</h3>
  <p><b>الهدف:</b> تاريخ الحرائق لأي منطقة: أي الأشهر والسنوات أكثر نشاطًا، ومقارنة كل شهر بالمعتاد. <b>لمن:</b> الجميع، وخاصة مديري الأراضي والعلماء.</p>
  {fig("cal_top", "أعلى صفحة التقويم: اختيار المنطقة والخريطة.")}
  {callouts([
    ("مناطق الحرائق", "مناطق جاهزة مشهورة بالحرائق (إيفيا، أتيكا، وسط البرتغال…).", "للبدء بسرعة دون رسم."),
    ("الدول", "الدول الثماني في منطقة التغطية.", "للمقارنة على مستوى الدولة."),
    ("الرسم (Draw)", "ارسم مضلّعًا أو دائرة على الخريطة.", "لدراسة أي منطقة تهمّك بالضبط."),
    ("خط العرض/الطول", "أدخل نقطة ونصف قطر، أو حدود مربع.", "عندما تعرف الإحداثيات من خريطة أخرى."),
    ("الخريطة", "تُظهر المنطقة المختارة وأحدث البؤر.", "لترى المكان والسياق."),
    ("البؤر الأخيرة", "عرض بؤر آخر 24 ساعة أو 7 أيام أو إخفاؤها.", "لمتابعة النشاط الحالي على الخريطة."),
    ("بطاقة المنطقة", "تُظهر معامل التحويل للمنطقة ونطاق الخطأ ومصدره.", "الشفافية: كيف قُدِّرت قيم ما قبل 2012 هنا."),
  ])}
</section>

<section>
  {fig("cal_main", "وسط صفحة التقويم: الفترة، البطاقات، التقويم وأزرار التنزيل.")}
  {callouts([
    ("الفترة (من/إلى)", "تحدد السنوات التي يُحسب منها «المعتاد».", "لتقارن مع فترة تختارها."),
    ("إخفاء الشعلات والصناعة", "يحذف خلايا فيها حرارة ثابتة طوال السنة تقريبًا.", "حتى لا تُحسب شعلات الغاز والمصانع كحرائق؛ يمكن إيقافه."),
    ("البطاقات", "شهر الذروة، الآن مقابل المعتاد، أنشط سنة، الإنذار المبكر الآن، إجمالي الرصد.", "أهم الأرقام بنظرة واحدة."),
    ("«مقارنةً بالمعتاد»", "يلوّن الخلايا: أزرق أقل من المعتاد، أحمر أعلى، مع رموز ▲ و▼ ونص.", "لرؤية الأشهر غير العادية؛ لا نعتمد على اللون وحده."),
    ("أسابيع", "يعرض 52 أسبوعًا بدل 12 شهرًا (للدول ومناطق الحرائق).", "لتفاصيل أدق لبداية الموسم."),
    ("الألوان", "يغيّر لوحة الألوان (Viridis، Cividis، YlOrRd).", "لوحات مناسبة لعمى الألوان."),
    ("التقويم", "صفوف = سنوات، أعمدة = أشهر. الخلايا المخطَّطة مقدَّرة من MODIS، والمصمتة مرصودة من VIIRS.", "قلب الموقع: تاريخ المنطقة كاملًا."),
    ("تنزيل CSV", "جدول القيم الشهرية مع المصدر ونطاق الخطأ.", "للباحثين وللتحليل في Excel."),
    ("تنزيل PNG", "صورة للتقويم.", "للعروض والتقارير."),
    ("ملخص PNG", "صفحة ملخص واحدة كصورة.", "لمشاركتها بسرعة."),
    ("ملخص PDF", "صفحة ملخص A4: المنطقة، الفترة، مقارنة الشهر بالوسيط، تقويم صغير، المصدر، الاعتراف ببيانات FIRMS.", "لغرف العمليات والتقارير الرسمية."),
  ])}
  <p class="small">الأرقام 8 إلى 18 في الصورة أعلاه بالترتيب نفسه.</p>
</section>

<section>
  {fig("cal_detail", "تفاصيل الشهر (رقم 19): إيفيا، آب 2007.")}
  <p><b>تفاصيل الشهر (19):</b> اضغط أي خلية لترى جملة واضحة، والقيمة ومصدرها، ونطاق الخطأ، والقيمة الخام، والمعتاد (الوسيط) ونطاق «النصف الأوسط»، والرتبة المئوية، ورسمًا لنفس الشهر في كل السنوات مع خط الوسيط. يمكن التنقل بين الخلايا بأسهم لوحة المفاتيح والضغط على <span class="en">Enter</span>.</p>
  <div class="box">مثال حقيقي من بياناتنا: آب 2007 في إيفيا ≈ <b>{ev_v:,}</b> بؤرة (من {ev_lo:,} إلى {ev_hi:,})، أي نحو <b>{ev_x}</b> ضعف آب المعتاد ({ev_med:,.0f}). القيمة <b>مقدَّرة من MODIS بمقياس VIIRS</b> بنطاق خطأ ±{round(u["small_regions_rel"] * 100)}%.</div>
  {fig("mobile_detail", "نفس التفاصيل على شاشة هاتف بعرض 390 بكسل.")}
</section>

<section>
  <h3>4.3 التنبيهات (<span class="en">Alerts</span>)</h3>
  <p><b>الهدف:</b> هل هذا الشهر غير عادي الآن؟ <b>لمن:</b> مديرو الطوارئ وفرق الإنذار المبكر.</p>
  {fig("alerts", "صفحة التنبيهات.")}
  {callouts([
    ("حالة البيانات", "آخر تحديث ناجح ومصدره؛ وتظهر رسائل «متأخر» أو «بيانات جزئية» أو «فشل آخر تحديث» عند الحاجة.", "حتى لا تثق بمستوى «عادي» على بيانات قديمة أو ناقصة."),
    ("ملاحظة المقياس", "توضّح أن الأعداد من NOAA-20 مضروبة في {kjn:.2f} لتطابق مقياس S-NPP.", "لأن S-NPP توقف في 2 تشرين الثاني 2026."),
    ("بطاقات التنبيه", "لكل منطقة: الفترة (مثلًا 1–13 تشرين الثاني، منذ بداية الشهر)، القيمة مقابل المعتاد والنسبة والمستوى، وقت التحديث، والمصدر.", "قرار سريع: عادي، مرتفع، عالٍ، أو شديد."),
    ("الخلاصات العامة", "روابط alerts.json و RSS و status.json.", "لربط أنظمة أخرى بتنبيهات جمرة."),
  ])}
  <p class="small">المستويات: عادي (<span class="en">Normal</span>)، مرتفع (≥ المئين 75)، عالٍ (≥ 90)، شديد (≥ 97.5)، مقارنةً بنفس الأيام في السنوات السابقة. إذا كانت البيانات أقدم من 30 ساعة يظهر «قديم» بدل أي مستوى.</p>
</section>

<section>
  <h3>4.4 البيانات المباشرة (<span class="en">Live Data</span>)</h3>
  <p><b>الهدف:</b> أحدث البؤر لمنطقة مختارة. <b>لمن:</b> فرق الإطفاء والطوارئ.</p>
  {fig("live", "صفحة البيانات المباشرة.")}
  {callouts([
    ("اختيار المنطقة", "نفس طرق الاختيار في التقويم.", "لتحديد مكان البحث."),
    ("الخريطة", "تُظهر البؤر الجديدة.", "لرؤية مواقع البؤر."),
    ("الفترة", "آخر 24 ساعة حتى 7 أيام.", "ضمن حدود واجهة ناسا."),
    ("«اجلب من NASA FIRMS»", "يجلب الكشوفات من NOAA-20 ويعرض وقت الجلب بالتوقيت العالمي.", "بيانات حديثة عند الطلب."),
    ("تنزيل CSV", "يحفظ النتائج.", "لاستخدامها في أنظمة أخرى."),
    ("الجدول", "التاريخ والوقت والقمر والثقة وقوة الإشعاع FRP والإحداثيات؛ اضغط العناوين للترتيب.", "تفاصيل كل بؤرة."),
  ])}
  <p class="small">ملاحظة: هذه كشوفات <span class="en">NOAA-20</span> الخام (غير محوّلة).</p>
</section>

<section>
  <h3>4.5 كيف تعمل (<span class="en">How It Works</span>)</h3>
  <p>صفحة علمية تشرح الطريقة: سنوات التداخل، معامل التحويل، ووضع السجل القديم على المقياس الجديد، مع جدول يقارن ست طرق.</p>
  {fig("how", "صفحة «كيف تعمل».")}
  {callouts([
    ("الخطوات الثلاث", "سنوات التداخل ← معامل التحويل ← السجل القديم بالمقياس الجديد.", "شرح الطريقة للعلماء."),
    ("مقارنة الطرق", "أخطاء الطرق M0 إلى M5 والطريقة المختارة.", "لماذا اخترنا هذه الطريقة."),
    ("مسار البيانات", "من أين تأتي البيانات ومتى تتحدث.", "الشفافية حول التحديث التلقائي."),
  ])}
  <h3>4.6 التحقق (<span class="en">Validation</span>)</h3>
  <p>نتائج الاختبار المستقل على سنوات لم تُستخدم أبدًا في بناء النموذج (التفاصيل في القسم 7).</p>
  {callouts([
    ("كيف اختبرنا", "تقسيم السنوات إلى سنوات تطوير وسنوات اختبار.", "اختبار عادل ومستقل."),
    ("أرقام الاختبار", "الخطأ للدول وللمجاميع السنوية والمناطق الصغيرة.", "ملخص الدقة."),
    ("الأشهر عالية النشاط", "كم شهرًا اكتشفنا وكم فاتنا وكم إنذارًا خاطئًا.", "مهم للإنذار المبكر."),
    ("المناطق الصغيرة", "المعامل المحلي مقابل معامل الدولة.", "قاعدة القرار بشفافية."),
    ("مناطق الحرائق", "الخطأ لكل منطقة على حدة.", "أين يصعب التقدير."),
    ("المتوقَّع مقابل الفعلي", "كل نقطة شهر لدولة في سنة مخفية.", "رؤية الدقة بصريًا."),
    ("ثبات النسبة", "نسبة VIIRS إلى MODIS لكل سنة.", "لكشف انجراف مدارات الأقمار القديمة."),
  ])}
</section>

<section>
  {fig("validation", "صفحة التحقق.")}
</section>

<section>
  <h3>4.7 الحدود (<span class="en">Limits</span>)</h3>
  {fig("limits", "صفحة الحدود.")}
  {callouts([
    ("أرقام عدم اليقين", "نطاق الخطأ لشهر الدولة وسنتها وللمناطق الصغيرة، ومعامل NOAA-20.", "حتى يعرف المستخدم مدى الثقة بكل رقم."),
    ("قائمة الحدود", "البؤر ليست حرائق، الغيوم تخفي الحرائق، انجراف المدارات، تغيّر الأقمار، وليست خدمة طوارئ.", "الصدق حول ما لا تستطيع البيانات قوله."),
  ])}
  <h3>4.8 المصادر والفريق (<span class="en">Credits</span>)</h3>
  {fig("credits", "صفحة المصادر والفريق.")}
  {callouts([
    ("الاعتراف ببيانات FIRMS", "النص الذي تطلبه ناسا حرفيًا.", "شرط استخدام البيانات."),
    ("الإفصاح عن الذكاء الفائق (SI)", "كيف استخدمنا مساعد البرمجة.", "شرط مسابقة Space Apps."),
    ("رابط GitHub", "الكود مفتوح المصدر (MIT).", "لمن يريد التحقق أو إعادة الاستخدام."),
    ("الفريق", "الأعضاء الخمسة وتوزيع العمل.", "من فعل ماذا."),
  ])}
</section>

<section>
  <h2>5. سيناريوهات استخدام حقيقية</h2>
  <h3>مدير طوارئ: هل هذا الشهر غير عادي؟</h3>
  <ol><li>افتح صفحة <b>التنبيهات</b>.</li><li>تأكد من شارة الحالة «مباشر» وعدم وجود «بيانات جزئية».</li><li>اقرأ بطاقة منطقتك: الفترة، القيمة مقابل المعتاد، والمستوى.</li><li>اضغط البطاقة لفتح التقويم على المنطقة نفسها ومقارنة الأشهر السابقة.</li></ol>
  <h3>مدير غابات: مقارنة مواسم الحرائق</h3>
  <ol><li>افتح <b>التقويم</b> واختر منطقة أو ارسمها.</li><li>اختر «مقارنةً بالمعتاد» لرؤية الأشهر الأعلى (▲) والأدنى (▼).</li><li>اقرأ قسم «هل يبدأ الموسم أبكر؟» أسفل التقويم: يذكر الاتجاه وهل هو ذو دلالة إحصائية.</li><li>نزّل «ملخص PDF» لإرفاقه بتقرير.</li></ol>
  <h3>فريق إطفاء: البيانات المباشرة</h3>
  <ol><li>افتح <b>البيانات المباشرة</b> واختر المنطقة.</li><li>اختر الفترة (مثلًا آخر 24 ساعة) واضغط «اجلب من NASA FIRMS».</li><li>رتّب الجدول حسب الوقت أو قوة الإشعاع FRP، وانظر المواقع على الخريطة.</li><li>نزّل CSV عند الحاجة.</li></ol>
  <h3>باحث: تنزيل البيانات</h3>
  <ol><li>في <b>التقويم</b> اختر المنطقة والفترة.</li><li>اضغط «تنزيل CSV»: كل شهر مع قيمته المُواءَمة ومصدره (مرصود/مقدَّر) ونطاق الخطأ والأعداد الخام لكل قمر.</li><li>راجع صفحتَي «كيف تعمل» و«التحقق» لفهم الطريقة ودقتها.</li></ol>
  <h3>مثال إيفيا 2007</h3>
  <ol><li>في <b>الرئيسية</b> اعرض الرسم «خام» ثم «مُواءَم».</li><li>اضغط «جرّب مثال إيفيا 2007».</li><li>يفتح التقويم على آب 2007 مع التفاصيل: ≈ {ev_v:,} بؤرة، مقدَّرة من MODIS بمقياس VIIRS (±{round(u["small_regions_rel"] * 100)}%).</li><li>قارنها بآب في السنوات الأخرى في الرسم، ثم افتح صفحة <b>التحقق</b> لنتيجة الاختبار المستقل.</li></ol>
</section>

<section>
  <h2>6. كيف تعمل البيانات (بشكل مبسّط)</h2>
  <h3>قيم مرصودة وقيم مقدَّرة</h3>
  <p>من 2012 فصاعدًا القيم <b>مرصودة</b> مباشرة من <span class="en">VIIRS</span> (خلايا مصمتة). قبل 2012 القيم <b>مقدَّرة من MODIS بمقياس VIIRS</b> (خلايا مخطَّطة وعلامة ≈) ومعها نطاق خطأ: نحو ±{round(u["monthly_rel"] * 100)}% لشهر الدولة، و±{round(u["annual_rel"] * 100)}% لمجموع سنة الدولة، و±{round(u["small_regions_rel"] * 100)}% لشهر في منطقة صغيرة. هذه الأرقام هي الخطأ المعتاد في سنوات الاختبار المستقل.</p>
  {fig("anomaly", "التقويم بوضع «مقارنةً بالمعتاد»: نص ورموز بجانب كل لون.")}
  <h3>التحديث كل 3 ساعات</h3>
  <p>كل 3 ساعات يجلب الموقع تلقائيًا أحدث كشوفات <span class="en">NOAA-20</span> من واجهة ناسا <span class="en">FIRMS</span> ويحسب مستوى الإنذار لكل منطقة. وكل شهر يُعاد بناء الأرشيف التاريخي من ملفات ناسا. إذا فشل التحديث تبقى آخر بيانات سليمة وتظهر حالة واضحة.</p>
  <h3>تحوّل S-NPP إلى NOAA-20</h3>
  <p>أوقفت ناسا بيانات قمر <span class="en">S-NPP</span> في 2 تشرين الثاني 2026. قمر <span class="en">NOAA-20</span> يحمل جهاز <span class="en">VIIRS</span> نفسه وفي المدار نفسه تقريبًا. قِسنا العلاقة بينهما في بيانات 2018–2025 فوجدنا معاملًا قدره <b>{kjn:.2f}</b>، ونضرب به أعداد <span class="en">NOAA-20</span> لتبقى على مقياس سجلّنا.</p>
</section>

<section>
  <h2>7. نتائج التحقق والحدود</h2>
  <p><b>تصميم الاختبار:</b> سنوات التطوير ({V["dev_years"][0]}–{V["dev_years"][-1]} دون 2021) لبناء النموذج واختيار إعداداته، وسنوات الاختبار ({"، ".join(map(str, V["test_years"]))}) محجوزة ولم تُلمس أثناء التطوير. النموذج المختار: <span class="en">{ch}</span> (نسبة لكل دولة وشهر مع «انكماش» نحو قيمة الدولة).</p>
  <div class="kpis">
    <div class="kpi"><b>{pct(tc["M0"]["mdape"])} ← {pct(tc[ch]["mdape"])}</b>الخطأ المعتاد لشهر الدولة في سنوات الاختبار: MODIS الخام ← بعد المواءمة</div>
    <div class="kpi"><b>{pct(tc[ch]["annual"]["mdape"])}</b>الخطأ المعتاد لمجموع سنة الدولة (الخام: {pct(tc["M0"]["annual"]["mdape"])})</div>
    <div class="kpi"><b>{cc["hits"]} من {cc["hits"] + cc["misses"]}</b>الأشهر عالية النشاط التي اكتُشفت (نسبة الاكتشاف {pct(cc["hit_rate"])})، مع {cc["false_alarms"]} إنذارًا خاطئًا؛ MODIS الخام اكتشف {cr["hits"]} فقط</div>
    <div class="kpi"><b>{pct(sg[meth]["mdape"])}</b>الخطأ المعتاد لشهر في {sg["regions"]} منطقة بحجم 1°، و{pct(sp[meth]["mdape"])} في مناطق الحرائق التسع</div>
  </div>
  <h3>المعامل المحلي للمناطق الصغيرة</h3>
  <table><thead><tr><th>المناطق</th><th>معامل الدولة: الخطأ (MAE)</th><th>المعامل المحلي: الخطأ (MAE)</th><th>الاكتشاف (دولة / محلي)</th></tr></thead><tbody>
  <tr><td>مناطق الحرائق ({sp["regions"]})</td><td>{sp["baseline"]["mae"]:.1f}</td><td>{sp["local"]["mae"]:.1f}</td><td>{sp["baseline"]["confusion"]["hits"]} / {sp["local"]["confusion"]["hits"]}</td></tr>
  <tr><td>مناطق 1° ({sg["regions"]})</td><td>{sg["baseline"]["mae"]:.2f}</td><td>{sg["local"]["mae"]:.2f}</td><td>{sg["baseline"]["confusion"]["hits"]} / {sg["local"]["confusion"]["hits"]}</td></tr>
  </tbody></table>
  <p><b>القرار:</b> {"اعتُمد المعامل المحلي لأنه خفّض خطأ المناطق الصغيرة في سنوات الاختبار؛ والتحسّن صغير لكنه ثابت." if meth == "local" else "لم يُعتمد المعامل المحلي لأنه لم يتفوّق في سنوات الاختبار، فتستخدم المناطق الصغيرة معامل الدولة."}</p>
  <h3>اختبار FRP</h3>
  <p>اختبرنا فكرة أن مجموع قوة الإشعاع (<span class="en">FRP</span>) أكثر ثباتًا بين القمرين من عدد البؤر: لم تؤيدها بياناتنا (تذبذب النسبة {R["frp_test"]["pooled_cv_frp_ratio"]:.2f} مقابل {R["frp_test"]["pooled_cv_count_ratio"]:.2f} للأعداد)، لذلك يعتمد التقويم على عدد البؤر.</p>
  <h3>الحدود</h3>
  <ul><li>البؤرة ليست حريقًا وليست مساحة محروقة.</li><li>الغيوم والدخان تخفي الحرائق، والحرائق الصغيرة تفوت MODIS أكثر.</li><li>المناطق الصغيرة أقل دقة لأن عدد البؤر فيها قليل.</li><li>انجراف مدارات الأقمار القديمة، وتغيّر الأقمار (S-NPP ← NOAA-20).</li><li>بعض البؤر من الزراعة أو الصناعة، وفي مناطق النزاع من انفجارات أو مبانٍ تحترق.</li><li>التأخير ساعات: ليست خدمة طوارئ.</li></ul>
</section>

<section>
  <h2>8. الفريق وتوزيع العمل</h2>
  <table><thead><tr><th>العضو</th><th>يقود ويملك (في الموقع)</th><th>يقدّم</th></tr></thead><tbody>
  <tr><td>شهد فرّاج</td><td>بحث المشكلة والمستخدمين: من يحتاج جمرة ولماذا. قصة الصفحة الرئيسية والمستخدمين المستهدفين. كتابة وصف المشروع في Space Apps.</td><td>الشريحتان 1–2</td></tr>
  <tr><td>أحمد اتكيدك</td><td>بيانات ناسا والنظام المباشر: أرشيف FIRMS وواجهته، مفتاح MAP_KEY، GitHub Pages والتحديث كل 3 ساعات. صفحات التنبيهات والبيانات المباشرة والحدود (تحوّل S-NPP ← NOAA-20).</td><td>الشريحة 3</td></tr>
  <tr><td>آية سلمان</td><td>العلم: طريقة المواءمة والمعامل المحلي (كيف تعمل)، والاختبار المستقل ونتائج المناطق الصغيرة (التحقق).</td><td>الشريحتان 4 و6</td></tr>
  <tr><td>أحمد الأخرس</td><td>صفحة التقويم: اختيار المنطقة، التقويم، تفاصيل الشهر، علامات عدم اليقين، التنزيلات. مسار عرض إيفيا 2007، العرض المباشر، واختبار الهاتف ولوحة المفاتيح.</td><td>الشريحة 5</td></tr>
  <tr><td>تالا يوسف</td><td>تجربة المستخدم والتواصل: التنقل بين الصفحات ومراجعة التصميم، إمكانية الوصول، صفحة المصادر والفريق، مراجعة الدليل العربي، تصميم الشرائح، الأثر والخطوات القادمة، وختام العرض.</td><td>الشريحة 7</td></tr>
  </tbody></table>
  <p><b>عمل مشترك:</b> اختيار الفكرة والطريقة، اختبار الموقع مع مستخدمين حقيقيين، والتدرّب على العرض.</p>

  <h2 style="margin-top:8mm">9. مسرد المصطلحات</h2>
  <table><thead><tr><th>بالعربية</th><th>بالإنجليزية</th><th>المعنى</th></tr></thead><tbody>
  <tr><td>بؤرة حرارية</td><td class="en">Hotspot</td><td>بكسل ساخن في صورة القمر الصناعي، غالبًا حريق.</td></tr>
  <tr><td>مواءمة</td><td class="en">Harmonization</td><td>تحويل أعداد MODIS إلى ما يعادلها بمقياس VIIRS.</td></tr>
  <tr><td>شذوذ / مقارنة بالمعتاد</td><td class="en">Anomaly</td><td>كم يختلف الشهر عن الوسيط لنفس الشهر في السنوات الأخرى.</td></tr>
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
  <h2>10. المصادر والمراجع والإفصاح</h2>
  <p class="en" style="text-align:left">We acknowledge the use of data and/or imagery from NASA's Fire Information for Resource Management System (FIRMS) (https://earthdata.nasa.gov/firms), part of NASA's Land, Atmosphere Near real-time Capability for Earth observations (LANCE) (https://earthdata.nasa.gov/lance) and NASA's Earth Science Data and Information System (ESDIS).</p>
  <h3>المراجع</h3>
  <ul class="en" style="text-align:left;direction:ltr">
    <li>Giglio, L., Schroeder, W., &amp; Justice, C. O. (2016). The collection 6 MODIS active fire detection algorithm and fire products. Remote Sensing of Environment, 178, 31–41.</li>
    <li>Schroeder, W., Oliva, P., Giglio, L., &amp; Csiszar, I. A. (2014). The New VIIRS 375 m active fire detection data product. Remote Sensing of Environment, 143, 85–96.</li>
    <li>Davies, D. K., Ilavajhala, S., Wong, M. M., &amp; Justice, C. O. (2009). Fire Information for Resource Management System. IEEE TGRS, 47(1), 72–79.</li>
    <li>NASA Earthdata (2026). Transitioning from Suomi NPP VIIRS &amp; OMPS: What FIRMS Users Need to Know.</li>
  </ul>
  <h3>البرمجيات والخرائط</h3>
  <p>MapLibre GL JS (BSD-3) · OpenFreeMap · © OpenStreetMap contributors · لوحات الألوان Viridis و Cividis و ColorBrewer. لا نستخدم شعارات ناسا، وناسا لا تتبنّى هذا المشروع.</p>
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
                   check=False, capture_output=True)
    print("wrote", out_html.name, pdf.name, pdf.stat().st_size if pdf.exists() else "missing")
    numbers = {"k_global": round(k, 1), "test_err_raw": pct(tc["M0"]["mdape"]), "test_err_harm": pct(tc[ch]["mdape"]),
               "test_err_year": pct(tc[ch]["annual"]["mdape"]), "hits": cc["hits"], "high_months": cc["hits"] + cc["misses"],
               "false_alarms": cc["false_alarms"], "small_grid_err": pct(sg[meth]["mdape"]), "small_preset_err": pct(sp[meth]["mdape"]),
               "k_jn": round(kjn, 2), "evia_2007_08": ev_v, "local_adopted": meth == "local"}
    (REP / "numbers_used.json").write_text(json.dumps(numbers, indent=1, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
