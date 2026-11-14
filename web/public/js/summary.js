// One-page summary (PNG and PDF) for the selected area and period, drawn on a canvas.
// The PDF is a single A4 page holding the summary image (JPEG), written without any library.
// Written with the help of an SI coding assistant (Claude Code).
import { downloadBlob, MONTHS, MONTHS_LONG, fmtInt } from './util.js';
import { baseline, percentileRank, category } from './stats.js';
import { ramp, CAT_COLOR, logScale } from './colors.js';
import { CAT_TEXT } from './calendar.js';

const W = 1240, H = 1754; // A4 at 150 dpi
const INK = '#1F2328', INK2 = '#2B2F36', MUTED = '#5C626B', EMBER = '#A8501C';
const ACK = "We acknowledge the use of data and/or imagery from NASA's Fire Information for Resource Management System (FIRMS) (https://earthdata.nasa.gov/firms), part of NASA's Land, Atmosphere Near real-time Capability for Earth observations (LANCE) (https://earthdata.nasa.gov/lance) and NASA's Earth Science Data and Information System (ESDIS).";

function wrap(ctx, text, x, y, maxW, lh) {
  const words = text.split(' ');
  let line = '';
  for (const w of words) {
    const t = line ? `${line} ${w}` : w;
    if (ctx.measureText(t).width > maxW && line) { ctx.fillText(line, x, y); y += lh; line = w; } else line = t;
  }
  if (line) { ctx.fillText(line, x, y); y += lh; }
  return y;
}

export function drawSummary(c) {
  const { area, meta, state, years, unc, val, srcOf, winYears } = c;
  const cv = document.createElement('canvas');
  cv.width = W; cv.height = H;
  const ctx = cv.getContext('2d');
  const F = (s, b = false) => `${b ? '700 ' : ''}${s}px "Segoe UI", Arial, sans-serif`;
  ctx.fillStyle = '#ffffff'; ctx.fillRect(0, 0, W, H);
  ctx.fillStyle = EMBER; ctx.fillRect(0, 0, W, 14);
  let y = 90;
  ctx.fillStyle = INK; ctx.font = F(44, true); ctx.fillText(`${meta.product.name} · Burning activity summary`, 70, y);
  y += 60; ctx.font = F(32, true); ctx.fillText(area.label, 70, y);
  y += 44; ctx.font = F(24); ctx.fillStyle = INK2;
  ctx.fillText(`Period: ${state.from}–${state.to} · Unit: VIIRS-equivalent hotspots (satellite fire pixels), not fires`, 70, y);

  // selected month vs historical median
  const [sy, sm] = state.sel || [state.to, 7];
  const v = val(sy, sm);
  const others = winYears().filter((yy) => yy !== sy).map((yy) => val(yy, sm));
  const b = baseline(others), pr = percentileRank(v, others), cat = category(v, others, meta.anomaly);
  const src = srcOf(sy, sm);
  y += 70; ctx.fillStyle = '#F3F4F6'; ctx.fillRect(60, y - 44, W - 120, 250);
  ctx.fillStyle = INK; ctx.font = F(28, true); ctx.fillText(`${MONTHS_LONG[sm]} ${sy} compared with the historical median`, 85, y);
  y += 58; ctx.font = F(26);
  const diff = b && b.median > 0 && v !== null ? Math.round(((v - b.median) / b.median) * 100) : null;
  const cells = [
    ['Value', v === null ? 'data gap' : `${src === 'M' ? '≈ ' : ''}${fmtInt(v)}`],
    ['Typical (median)', b ? fmtInt(b.median) : '–'],
    ['Difference', diff === null ? '–' : `${diff >= 0 ? '+' : ''}${diff}%`],
    ['Category', cat ? CAT_TEXT[cat] : '–'],
  ];
  cells.forEach(([k, t], i) => {
    const x = 85 + i * 275;
    ctx.fillStyle = MUTED; ctx.font = F(20); ctx.fillText(k, x, y);
    ctx.fillStyle = i === 3 && cat ? (cat.includes('higher') ? '#A8501C' : cat.includes('lower') ? '#3E5C76' : INK) : INK;
    ctx.font = F(i === 3 ? 22 : 38, true); ctx.fillText(t, x, y + 46);
  });
  y += 110; ctx.fillStyle = INK2; ctx.font = F(21);
  const srcText = src === 'M' ? `Source: estimated from MODIS on the VIIRS scale (±${Math.round(unc * 100)}% typical error).`
    : src === 'J' ? 'Source: VIIRS NOAA-20, converted to the S-NPP scale.' : 'Source: observed by VIIRS (S-NPP).';
  ctx.fillText(`${srcText}${pr !== null ? ` Higher than ${Math.round(pr)}% of ${MONTHS_LONG[sm]}s in ${state.from}–${state.to}.` : ''}`, 85, y);

  // period totals
  const wy = winYears();
  const tot = wy.map((yy) => [yy, MONTHS.reduce((a, _, m) => a + (val(yy, m) || 0), 0)]);
  const top = tot.reduce((a, t) => (t[1] > a[1] ? t : a), [null, -1]);
  y += 70; ctx.fillStyle = INK; ctx.font = F(26, true); ctx.fillText('Period overview', 70, y);
  y += 42; ctx.font = F(22); ctx.fillStyle = INK2;
  ctx.fillText(`Total ${state.from}–${state.to}: ${fmtInt(tot.reduce((a, t) => a + t[1], 0))} hotspots · most active year: ${top[0]} (${fmtInt(top[1])})`, 70, y);

  // small calendar
  y += 50;
  const cw = 80, chh = Math.min(30, Math.floor(620 / years.length)), x0 = 150;
  const all = []; years.forEach((yy) => MONTHS.forEach((_, m) => { const t = val(yy, m); if (t !== null) all.push(t); }));
  const sc = logScale(Math.max(...all, 1));
  ctx.font = F(17); ctx.fillStyle = MUTED;
  MONTHS.forEach((mn, m) => ctx.fillText(mn, x0 + m * cw + 22, y));
  y += 12;
  years.forEach((yy, r) => {
    ctx.fillStyle = MUTED; ctx.font = F(16); ctx.fillText(String(yy), 80, y + r * chh + chh - 8);
    MONTHS.forEach((_, m) => {
      const t = val(yy, m);
      if (t === undefined) return; // future month
      ctx.fillStyle = t === null ? '#e5e5e5' : state.mode === 'anomaly'
        ? (CAT_COLOR[category(t, wy.filter((q) => q !== yy).map((q) => val(q, m)), meta.anomaly)] || '#f7f7f7') : ramp(state.palette, sc(t));
      ctx.fillRect(x0 + m * cw + 1, y + r * chh + 1, cw - 2, chh - 2);
      if (srcOf(yy, m) === 'M' && t !== null) { // hatch: estimated from MODIS
        ctx.strokeStyle = 'rgba(255,255,255,.55)'; ctx.lineWidth = 1.5;
        for (let d = -chh; d < cw; d += 8) { ctx.beginPath(); ctx.moveTo(x0 + m * cw + d, y + r * chh + chh); ctx.lineTo(x0 + m * cw + d + chh, y + r * chh); ctx.stroke(); }
      }
      if (yy === sy && m === sm) { ctx.strokeStyle = EMBER; ctx.lineWidth = 4; ctx.strokeRect(x0 + m * cw + 1, y + r * chh + 1, cw - 2, chh - 2); }
    });
  });
  y += years.length * chh + 34;
  ctx.fillStyle = INK2; ctx.font = F(18);
  ctx.fillText(`Colours: ${state.mode === 'anomaly' ? 'compared with the usual (blue lower, red higher)' : 'hotspots per month, log scale'}. Hatched = estimated from MODIS on the VIIRS scale; solid = observed by VIIRS.`, 70, y);

  // footer
  y = H - 210; ctx.fillStyle = MUTED; ctx.font = F(17);
  y = wrap(ctx, ACK, 70, y, W - 140, 24);
  y += 10; ctx.fillText(`Generated ${new Date().toISOString().replace('T', ' ').slice(0, 16)} UTC · ${location.origin}${location.pathname}${location.search}`, 70, y);
  ctx.fillText('Not an emergency service. Hotspots are satellite fire pixels, not fires or burned area.', 70, y + 28);
  return cv;
}

function pdfFromJpeg(jpegBytes, w, h) {
  // A4 = 595 x 842 pt; one image covering the page
  const enc = new TextEncoder();
  const parts = [], offsets = [];
  let len = 0;
  const push = (x) => { const b = typeof x === 'string' ? enc.encode(x) : x; parts.push(b); len += b.length; };
  push('%PDF-1.4\n%\xE2\xE3\xCF\xD3\n');
  const obj = (n, body) => { offsets[n] = len; push(`${n} 0 obj\n`); body(); push('\nendobj\n'); };
  obj(1, () => push('<< /Type /Catalog /Pages 2 0 R >>'));
  obj(2, () => push('<< /Type /Pages /Kids [3 0 R] /Count 1 >>'));
  obj(3, () => push('<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /XObject << /Im0 4 0 R >> >> /Contents 5 0 R >>'));
  obj(4, () => { push(`<< /Type /XObject /Subtype /Image /Width ${w} /Height ${h} /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode /Length ${jpegBytes.length} >>\nstream\n`); push(jpegBytes); push('\nendstream'); });
  const content = 'q 595 0 0 842 0 0 cm /Im0 Do Q';
  obj(5, () => push(`<< /Length ${content.length} >>\nstream\n${content}\nendstream`));
  const xref = len;
  let x = 'xref\n0 6\n0000000000 65535 f \n';
  for (let i = 1; i <= 5; i++) x += `${String(offsets[i]).padStart(10, '0')} 00000 n \n`;
  push(x + `trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n${xref}\n%%EOF\n`);
  return new Blob(parts, { type: 'application/pdf' });
}

export async function downloadSummary(kind, c) {
  if (!c.area) return;
  const cv = drawSummary(c);
  const name = `jamra_summary_${c.area.id}_${c.state.from}-${c.state.to}`;
  if (kind === 'png') {
    cv.toBlob((b) => downloadBlob(`${name}.png`, b, 'image/png'));
    return;
  }
  const jpeg = await new Promise((res) => cv.toBlob(res, 'image/jpeg', 0.92));
  const bytes = new Uint8Array(await jpeg.arrayBuffer());
  downloadBlob(`${name}.pdf`, pdfFromJpeg(bytes, W, H), 'application/pdf');
}
