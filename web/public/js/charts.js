// Hand-made SVG charts (no chart library: keeps the app small and offline-friendly).
// Written with the help of an SI coding assistant (Claude Code).
import { svg, fmt, fmtInt, MONTHS_LONG } from './util.js';
import { quantile } from './stats.js';

const INK = '#0B1D51', MUTED = '#475569', LINE = '#E2E8F0', EMBER = '#FF6A2B', BLUE = '#1F4FD8', GREY = '#94A3B8', SKY = '#3FA9F5';

export function niceTicks(max, count = 5) {
  if (!(max > 0)) return [0, 1];
  const step0 = max / count, mag = 10 ** Math.floor(Math.log10(step0));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((s) => s >= step0) || mag * 10;
  const ticks = [];
  for (let v = 0; v <= max + step * 0.001; v += step) ticks.push(+v.toFixed(10));
  if (ticks[ticks.length - 1] < max) ticks.push(ticks[ticks.length - 1] + step);
  return ticks;
}

function hatchDefs(id) {
  return svg('defs', {}, svg('pattern', { id, width: 6, height: 6, patternUnits: 'userSpaceOnUse', patternTransform: 'rotate(45)' },
    svg('rect', { width: 6, height: 6, fill: 'transparent' }), svg('line', { x1: 0, y1: 0, x2: 0, y2: 6, stroke: 'rgba(255,255,255,.55)', 'stroke-width': 2 })));
}

function attachTip(node, html, tip) {
  if (!tip) return;
  node.addEventListener('mousemove', (e) => tip.show(e.clientX, e.clientY, html));
  node.addEventListener('mouseleave', () => tip.hide());
}

/** Yearly totals: raw stitched record vs harmonized. */
export function heroChart(container, { years, raw, harm, modisAqua, viirs, modisConverted, mode, tip }) {
  container.innerHTML = '';
  const W = 900, H = 320, m = { t: 16, r: 16, b: 34, l: 56 };
  const iw = W - m.l - m.r, ih = H - m.t - m.b;
  const vals = mode === 'raw' ? raw : harm;
  const max = Math.max(1, ...vals.filter((v) => v !== null), ...(mode === 'raw' ? modisAqua : modisConverted).filter((v) => v !== null), ...viirs.filter((v) => v !== null));
  const ticks = niceTicks(max);
  const ymax = ticks[ticks.length - 1];
  const x = (i) => m.l + (i + 0.5) * (iw / years.length);
  const y = (v) => m.t + ih - (v / ymax) * ih;
  const bw = Math.max(4, (iw / years.length) * 0.68);
  const root = svg('svg', { viewBox: `0 0 ${W} ${H}`, role: 'img', 'aria-label': mode === 'raw' ? 'Raw stitched yearly hotspots' : 'Harmonized yearly hotspots' });
  root.append(hatchDefs('hero-hatch'));
  for (const t of ticks) {
    root.append(svg('line', { x1: m.l, x2: W - m.r, y1: y(t), y2: y(t), stroke: LINE }));
    root.append(svg('text', { x: m.l - 8, y: y(t) + 4, 'text-anchor': 'end', 'font-size': 12, fill: MUTED }, document.createTextNode(fmt(t))));
  }
  const iSwitch = years.indexOf(2012);
  if (iSwitch > 0) {
    const xs = m.l + iSwitch * (iw / years.length);
    root.append(svg('line', { x1: xs, x2: xs, y1: m.t, y2: m.t + ih, stroke: INK, 'stroke-dasharray': '4 4' }));
    root.append(svg('text', { x: xs + 6, y: m.t + 12, 'font-size': 12, fill: INK }, document.createTextNode('2012: VIIRS starts')));
  }
  years.forEach((yr, i) => {
    const v = vals[i];
    if (v === null || v === undefined) return;
    const isModisEra = yr < 2012;
    const fill = mode === 'raw' ? (isModisEra ? GREY : EMBER) : (isModisEra ? SKY : BLUE);
    const g = svg('g', {});
    g.append(svg('rect', { x: x(i) - bw / 2, y: y(v), width: bw, height: Math.max(0, y(0) - y(v)), fill, rx: 2 }));
    if (mode === 'harm' && isModisEra) g.append(svg('rect', { x: x(i) - bw / 2, y: y(v), width: bw, height: Math.max(0, y(0) - y(v)), fill: 'url(#hero-hatch)' }));
    const label = mode === 'raw'
      ? `${yr}: ${fmtInt(v)} hotspots (${isModisEra ? 'MODIS Aqua, raw' : 'VIIRS S-NPP, raw'})`
      : `${yr}: ${fmtInt(v)} VIIRS-equivalent hotspots${isModisEra ? ' (estimated from MODIS)' : ''}`;
    attachTip(g, label, tip);
    root.append(g);
    if (years.length <= 30 && (i % (years.length > 16 ? 2 : 1) === 0 || i === years.length - 1)) {
      root.append(svg('text', { x: x(i), y: H - 12, 'text-anchor': 'middle', 'font-size': 12, fill: MUTED }, document.createTextNode(String(yr))));
    }
  });
  // overlap lines: both sensors from 2012
  const line = (arr, color, dash, label) => {
    const pts = arr.map((v, i) => (v === null || years[i] < 2012 ? null : `${x(i)},${y(v)}`)).filter(Boolean);
    if (pts.length < 2) return;
    root.append(svg('polyline', { points: pts.join(' '), fill: 'none', stroke: color, 'stroke-width': 3, 'stroke-dasharray': dash || null }));
    const last = arr.map((v, i) => [v, i]).filter(([v, i]) => v !== null && years[i] >= 2012).pop();
    if (last) root.append(svg('text', { x: Math.min(x(last[1]) + 6, W - 4), y: y(last[0]) - 6, 'font-size': 12, fill: color, 'text-anchor': x(last[1]) > W - 120 ? 'end' : 'start' }, document.createTextNode(label)));
  };
  if (mode === 'raw') line(modisAqua, BLUE, '6 4', 'MODIS Aqua (same years)');
  else line(modisConverted, INK, '6 4', 'MODIS converted');
  container.append(root);
}

/** Bars for one calendar month across years, with median line and 25–75% band. */
export function monthBars(container, { years, values, selYear, month, src, lo, hi, tip, onPick }) {
  container.innerHTML = '';
  const W = 900, H = 260, m = { t: 14, r: 12, b: 30, l: 52 };
  const iw = W - m.l - m.r, ih = H - m.t - m.b;
  const others = values.filter((v, i) => years[i] !== selYear && v !== null);
  const med = quantile(others, 0.5), p25 = quantile(others, 0.25), p75 = quantile(others, 0.75);
  const max = Math.max(1, ...values.filter((v) => v !== null), ...hi.filter((v) => v !== null));
  const ticks = niceTicks(max), ymax = ticks[ticks.length - 1];
  const x = (i) => m.l + (i + 0.5) * (iw / years.length);
  const y = (v) => m.t + ih - (v / ymax) * ih;
  const bw = Math.max(3, (iw / years.length) * 0.7);
  const root = svg('svg', { viewBox: `0 0 ${W} ${H}`, role: 'img', 'aria-label': `${MONTHS_LONG[month - 1]} hotspots by year` });
  root.append(hatchDefs('bar-hatch'));
  for (const t of ticks) {
    root.append(svg('line', { x1: m.l, x2: W - m.r, y1: y(t), y2: y(t), stroke: LINE }));
    root.append(svg('text', { x: m.l - 6, y: y(t) + 4, 'text-anchor': 'end', 'font-size': 12, fill: MUTED }, document.createTextNode(fmt(t))));
  }
  if (p25 !== null) root.append(svg('rect', { x: m.l, width: iw, y: y(p75), height: Math.max(1, y(p25) - y(p75)), fill: 'rgba(31,79,216,.10)' }));
  years.forEach((yr, i) => {
    const v = values[i];
    if (v === null) {
      root.append(svg('text', { x: x(i), y: y(0) - 4, 'text-anchor': 'middle', 'font-size': 11, fill: MUTED }, document.createTextNode('gap')));
      return;
    }
    const sel = yr === selYear;
    const g = svg('g', { style: 'cursor:pointer' });
    g.append(svg('rect', { x: x(i) - bw / 2, y: y(v), width: bw, height: Math.max(0, y(0) - y(v)), fill: sel ? EMBER : (src[i] === 'M' ? SKY : BLUE), rx: 2 }));
    if (src[i] === 'M') g.append(svg('rect', { x: x(i) - bw / 2, y: y(v), width: bw, height: Math.max(0, y(0) - y(v)), fill: 'url(#bar-hatch)' }));
    if (lo[i] !== null && hi[i] !== null) g.append(svg('line', { x1: x(i), x2: x(i), y1: y(hi[i]), y2: y(lo[i]), stroke: INK, 'stroke-width': 1.5 }));
    attachTip(g, `${MONTHS_LONG[month - 1]} ${yr}: ${fmtInt(v)} hotspots${src[i] === 'M' ? ` (estimated from MODIS, ${fmtInt(lo[i])}–${fmtInt(hi[i])})` : src[i] === 'J' ? ' (from NOAA-20, converted)' : ''}`, tip);
    g.addEventListener('click', () => onPick && onPick(yr));
    root.append(g);
    if (i % (years.length > 16 ? 2 : 1) === 0) root.append(svg('text', { x: x(i), y: H - 10, 'text-anchor': 'middle', 'font-size': 11, fill: MUTED }, document.createTextNode(String(yr).slice(2))));
  });
  if (med !== null) {
    root.append(svg('line', { x1: m.l, x2: W - m.r, y1: y(med), y2: y(med), stroke: BLUE, 'stroke-width': 2, 'stroke-dasharray': '6 4' }));
    root.append(svg('text', { x: W - m.r, y: y(med) - 6, 'text-anchor': 'end', 'font-size': 12, fill: BLUE }, document.createTextNode(`median ${fmtInt(med)} · band = 25–75%`)));
  }
  container.append(root);
}

/** Cross-validated predicted vs actual, log axes. */
export function scatter(container, { points, tip }) {
  container.innerHTML = '';
  const W = 460, H = 380, m = { t: 12, r: 12, b: 44, l: 56 };
  const iw = W - m.l - m.r, ih = H - m.t - m.b;
  const max = Math.max(10, ...points.map((p) => Math.max(p.V, p.P, p.P0)));
  const L = (v) => Math.log10(1 + v) / Math.log10(1 + max);
  const x = (v) => m.l + L(v) * iw, y = (v) => m.t + ih - L(v) * ih;
  const root = svg('svg', { viewBox: `0 0 ${W} ${H}`, role: 'img', 'aria-label': 'Predicted versus actual monthly VIIRS hotspots' });
  for (const t of [0, 10, 100, 1000, 10000].filter((t) => t <= max * 1.01)) {
    root.append(svg('line', { x1: x(t), x2: x(t), y1: m.t, y2: m.t + ih, stroke: LINE }));
    root.append(svg('line', { x1: m.l, x2: m.l + iw, y1: y(t), y2: y(t), stroke: LINE }));
    root.append(svg('text', { x: x(t), y: H - 26, 'text-anchor': 'middle', 'font-size': 11, fill: MUTED }, document.createTextNode(fmt(t))));
    root.append(svg('text', { x: m.l - 6, y: y(t) + 4, 'text-anchor': 'end', 'font-size': 11, fill: MUTED }, document.createTextNode(fmt(t))));
  }
  root.append(svg('line', { x1: x(0), y1: y(0), x2: x(max), y2: y(max), stroke: INK, 'stroke-dasharray': '4 4' }));
  for (const p of points) root.append(svg('circle', { cx: x(p.V), cy: y(p.P0), r: 2.2, fill: GREY, opacity: 0.6 }));
  for (const p of points) {
    const c = svg('circle', { cx: x(p.V), cy: y(p.P), r: 2.6, fill: EMBER, opacity: 0.75 });
    attachTip(c, `${p.c} ${p.y}-${String(p.m).padStart(2, '0')}: actual ${fmtInt(p.V)}, predicted ${fmtInt(p.P)} (raw MODIS ${fmtInt(p.P0)})`, tip);
    root.append(c);
  }
  root.append(svg('text', { x: m.l + iw / 2, y: H - 6, 'text-anchor': 'middle', 'font-size': 12, fill: INK }, document.createTextNode('Actual VIIRS hotspots (month, country)')));
  root.append(svg('text', { x: 14, y: m.t + ih / 2, 'text-anchor': 'middle', 'font-size': 12, fill: INK, transform: `rotate(-90 14 ${m.t + ih / 2})` }, document.createTextNode('Predicted from MODIS')));
  container.append(root);
}

/** Horizontal bars of an error metric per model. */
export function errorBars(container, { rows, chosen, metricLabel }) {
  container.innerHTML = '';
  const W = 460, rowH = 34, m = { t: 8, r: 70, b: 8, l: 210 };
  const H = m.t + m.b + rows.length * rowH;
  const max = Math.max(...rows.map((r) => r.value || 0), 0.0001);
  const root = svg('svg', { viewBox: `0 0 ${W} ${H}`, role: 'img', 'aria-label': `${metricLabel} by model` });
  rows.forEach((r, i) => {
    const yy = m.t + i * rowH;
    const w = ((r.value || 0) / max) * (W - m.l - m.r);
    root.append(svg('text', { x: m.l - 8, y: yy + rowH / 2 + 4, 'text-anchor': 'end', 'font-size': 12.5, fill: INK, 'font-weight': r.id === chosen ? 700 : 400 }, document.createTextNode(r.label)));
    root.append(svg('rect', { x: m.l, y: yy + 7, width: Math.max(w, 1), height: rowH - 14, rx: 3, fill: r.id === chosen ? EMBER : r.id === 'M0' ? GREY : BLUE }));
    root.append(svg('text', { x: m.l + w + 6, y: yy + rowH / 2 + 4, 'font-size': 12.5, fill: INK }, document.createTextNode(r.text)));
  });
  container.append(root);
}

/** Year-by-year VIIRS/MODIS ratio with the calibration band. */
export function driftChart(container, { drift, ref, tol, tip }) {
  container.innerHTML = '';
  const W = 460, H = 280, m = { t: 14, r: 14, b: 32, l: 46 };
  const iw = W - m.l - m.r, ih = H - m.t - m.b;
  const ys = drift.map((d) => d.year);
  const vals = drift.map((d) => d.ratio_N_over_A).filter((v) => v);
  const ymax = Math.max(...vals, ref * (1 + tol)) * 1.12, ymin = Math.min(...vals, ref * (1 - tol)) * 0.85;
  const x = (yr) => m.l + ((yr - ys[0]) / Math.max(1, ys[ys.length - 1] - ys[0])) * iw;
  const y = (v) => m.t + ih - ((v - ymin) / (ymax - ymin)) * ih;
  const root = svg('svg', { viewBox: `0 0 ${W} ${H}`, role: 'img', 'aria-label': 'VIIRS to MODIS ratio by year' });
  root.append(svg('rect', { x: m.l, width: iw, y: y(ref * (1 + tol)), height: y(ref * (1 - tol)) - y(ref * (1 + tol)), fill: 'rgba(63,169,245,.15)' }));
  for (const t of niceTicks(ymax, 4).filter((t) => t >= ymin)) {
    root.append(svg('line', { x1: m.l, x2: W - m.r, y1: y(t), y2: y(t), stroke: LINE }));
    root.append(svg('text', { x: m.l - 6, y: y(t) + 4, 'text-anchor': 'end', 'font-size': 11, fill: MUTED }, document.createTextNode(t.toFixed(1))));
  }
  const pts = drift.filter((d) => d.ratio_N_over_A).map((d) => `${x(d.year)},${y(d.ratio_N_over_A)}`);
  root.append(svg('polyline', { points: pts.join(' '), fill: 'none', stroke: INK, 'stroke-width': 2 }));
  drift.forEach((d) => {
    if (!d.ratio_N_over_A) return;
    const c = svg('circle', { cx: x(d.year), cy: y(d.ratio_N_over_A), r: 5, fill: d.used_for_calibration ? INK : '#fff', stroke: INK, 'stroke-width': 2 });
    attachTip(c, `${d.year}: ${d.ratio_N_over_A.toFixed(2)} VIIRS hotspots per MODIS hotspot${d.used_for_calibration ? ' (used for calibration)' : ' (not used)'}`, tip);
    root.append(c);
    root.append(svg('text', { x: x(d.year), y: H - 10, 'text-anchor': 'middle', 'font-size': 11, fill: MUTED }, document.createTextNode(String(d.year).slice(2))));
  });
  container.append(root);
}
