// Burning Activity Calendar (years x months, or years x 52 weeks).
// Written with the help of an SI coding assistant (Claude Code).
import { svg, el, fmt, fmtInt, MONTHS, MONTHS_LONG } from './util.js';
import { ramp, rampCSS, CAT_COLOR, textOn, logScale } from './colors.js';
import { category, percentileRank, baseline, CAT_LABEL, CAT_ORDER } from './stats.js';

export const CAT_TEXT = { much_lower: 'Much lower than usual', lower: 'Lower than usual', typical: 'Typical', higher: 'Higher than usual', much_higher: 'Much higher than usual' };
export const CAT_SYM = { much_lower: '▼▼', lower: '▼', typical: '', higher: '▲', much_higher: '▲▲' };

/**
 * grid: { years:[...], cols: 12|52, value(y,c) -> number|null, src(y,c) -> 'M'|'N'|'J'|'G', label(c) }
 * opts: { mode:'abs'|'anomaly', palette, anomalyCfg, baselineYears:[from,to], tip, onSelect, selected }
 */
export function renderCalendar(container, legend, grid, opts) {
  container.innerHTML = '';
  legend.innerHTML = '';
  const { years, cols } = grid;
  const width = Math.max(container.clientWidth || 800, 320);
  const labelW = 56, top = 30;
  const cw = Math.max(cols === 12 ? 24 : 9, Math.floor((width - labelW - 4) / cols));
  const ch = cols === 12 ? Math.max(24, Math.min(36, cw * 0.5)) : 18;
  const W = labelW + cw * cols + 4, H = top + ch * years.length + 4;
  const root = svg('svg', { width: W, height: H, viewBox: `0 0 ${W} ${H}`, 'aria-hidden': 'false' });
  root.append(svg('defs', {},
    svg('pattern', { id: 'cal-hatch', width: 5, height: 5, patternUnits: 'userSpaceOnUse', patternTransform: 'rotate(45)' },
      svg('line', { x1: 0, y1: 0, x2: 0, y2: 5, stroke: 'rgba(255,255,255,.6)', 'stroke-width': 1.6 })),
    svg('pattern', { id: 'cal-hatch-dark', width: 5, height: 5, patternUnits: 'userSpaceOnUse', patternTransform: 'rotate(45)' },
      svg('line', { x1: 0, y1: 0, x2: 0, y2: 5, stroke: 'rgba(17,24,39,.35)', 'stroke-width': 1.4 })),
    svg('pattern', { id: 'cal-gap', width: 6, height: 6, patternUnits: 'userSpaceOnUse', patternTransform: 'rotate(-45)' },
      svg('rect', { width: 6, height: 6, fill: '#eeeeee' }), svg('line', { x1: 0, y1: 0, x2: 0, y2: 6, stroke: '#c7c7c7', 'stroke-width': 2 }))));

  // values + colour
  const [b0, b1] = opts.baselineYears;
  const all = [];
  years.forEach((y) => { for (let c = 0; c < cols; c++) { const v = grid.value(y, c); if (v !== null && v !== undefined) all.push(v); } });
  const scale = logScale(Math.max(...all, 1));
  const colInfo = [];
  for (let c = 0; c < cols; c++) {
    const vals = years.filter((y) => y >= b0 && y <= b1).map((y) => [y, grid.value(y, c)]).filter(([, v]) => v !== null && v !== undefined);
    colInfo.push(vals);
  }
  const cellData = (y, c) => {
    const v = grid.value(y, c);
    const others = colInfo[c].filter(([yy]) => yy !== y).map(([, vv]) => vv);
    const cat = opts.mode === 'anomaly' ? category(v, others, opts.anomalyCfg) : null;
    const fill = v === null ? 'url(#cal-gap)' : opts.mode === 'anomaly' ? (cat ? CAT_COLOR[cat] : '#f7f7f7') : ramp(opts.palette, scale(v));
    return { v, cat, fill, others, src: grid.src(y, c) };
  };

  // headers
  for (let c = 0; c < cols; c++) {
    if (cols === 12 || c % 4 === 0) {
      root.append(svg('text', { x: labelW + c * cw + cw / 2, y: 18, 'text-anchor': 'middle' }, document.createTextNode(grid.label(c))));
    }
  }
  const cells = [];
  years.forEach((y, r) => {
    root.append(svg('text', { x: labelW - 8, y: top + r * ch + ch / 2 + 5, 'text-anchor': 'end' }, document.createTextNode(String(y))));
    for (let c = 0; c < cols; c++) {
      if (grid.value(y, c) === undefined) continue; // future: nothing to show
      const d = cellData(y, c);
      const g = svg('g', { class: 'cell', role: 'gridcell', tabindex: '-1', 'data-y': y, 'data-c': c });
      const x = labelW + c * cw, yy = top + r * ch;
      g.append(svg('rect', { class: 'bg', x: x + 1, y: yy + 1, width: cw - 2, height: ch - 2, rx: 2, fill: d.fill, stroke: d.src === 'J' ? '#4B5563' : 'none', 'stroke-dasharray': d.src === 'J' ? '3 2' : null }));
      if (d.src === 'M' && d.v !== null) {
        const dark = opts.mode === 'anomaly' ? (d.cat === 'typical' || d.cat === 'lower' || d.cat === 'higher') : scale(d.v) > 0.6 && opts.palette !== 'ylorrd';
        g.append(svg('rect', { x: x + 1, y: yy + 1, width: cw - 2, height: ch - 2, rx: 2, fill: dark ? 'url(#cal-hatch-dark)' : 'url(#cal-hatch)', 'pointer-events': 'none' }));
      }
      const fillHex = d.fill.startsWith('#') ? d.fill : '#ffffff';
      if (opts.mode === 'anomaly' && d.cat && CAT_SYM[d.cat] && cw >= 14) {
        g.append(svg('text', { x: x + cw / 2, y: yy + ch / 2 + 4, 'text-anchor': 'middle', 'font-size': cols === 12 ? 13 : 9, fill: textOn(fillHex), 'pointer-events': 'none' }, document.createTextNode(CAT_SYM[d.cat])));
      } else if (opts.mode !== 'anomaly' && cols === 12 && cw >= 50 && d.v !== null) {
        g.append(svg('text', { x: x + cw / 2, y: yy + ch / 2 + 5, 'text-anchor': 'middle', 'font-size': 14, fill: textOn(fillHex), 'pointer-events': 'none' }, document.createTextNode(short(d.v))));
      }
      const text = describe(y, c, d, grid, opts);
      g.setAttribute('aria-label', text.replace(/<[^>]+>/g, ''));
      g.addEventListener('mousemove', (e) => opts.tip.show(e.clientX, e.clientY, text));
      g.addEventListener('mouseleave', () => opts.tip.hide());
      g.addEventListener('click', () => { focusCell(y, c); opts.onSelect(y, c); });
      root.append(g);
      cells.push(g);
    }
  });
  container.append(root);

  // keyboard navigation (roving tabindex)
  let cur = opts.selected && years.includes(opts.selected[0]) ? opts.selected : [years[years.length - 1], 0];
  const find = (y, c) => cells.find((g) => +g.dataset.y === y && +g.dataset.c === c);
  function focusCell(y, c, move = false) {
    cells.forEach((g) => { g.setAttribute('tabindex', '-1'); g.classList.remove('focus'); });
    const g = find(y, c);
    if (!g) return;
    g.setAttribute('tabindex', '0');
    g.classList.add('focus');
    if (move) g.focus();
    cur = [y, c];
  }
  if (opts.selected) { const s = find(...opts.selected); if (s) s.classList.add('sel'); }
  focusCell(...cur);
  root.addEventListener('keydown', (e) => {
    let [y, c] = cur;
    const yi = years.indexOf(y);
    if (e.key === 'ArrowRight') c = Math.min(cols - 1, c + 1);
    else if (e.key === 'ArrowLeft') c = Math.max(0, c - 1);
    else if (e.key === 'ArrowDown') y = years[Math.min(years.length - 1, yi + 1)];
    else if (e.key === 'ArrowUp') y = years[Math.max(0, yi - 1)];
    else if (e.key === 'Enter' || e.key === ' ') { opts.onSelect(y, c); e.preventDefault(); return; }
    else return;
    e.preventDefault();
    focusCell(y, c, true);
    const g = find(y, c);
    if (g) { const r = g.getBoundingClientRect(); opts.tip.show(r.right, r.top, describe(y, c, cellData(y, c), grid, opts)); }
    if (opts.liveSelect) opts.onSelect(y, c);
  });
  root.addEventListener('focusout', () => opts.tip.hide());

  // legend
  if (opts.mode === 'abs') {
    const maxV = Math.max(...all, 1);
    legend.append(el('span', { text: '0' }), el('span', { class: 'ramp', style: `background:${rampCSS(opts.palette)}` }),
      el('span', { text: `${fmtInt(maxV)} hotspots per ${cols === 12 ? 'month' : 'week'}` }), el('span', { class: 'base', text: 'VIIRS scale · log colour scale' }));
  } else {
    CAT_ORDER.forEach((k) => legend.append(el('span', { class: 'sw' }, el('i', { style: `background:${CAT_COLOR[k]}` }), `${CAT_SYM[k] ? CAT_SYM[k] + ' ' : ''}${CAT_TEXT[k]}`)));
    legend.append(el('span', { class: 'base', text: `vs the same ${cols === 12 ? 'month' : 'week'} in ${b0}–${b1}` }));
  }
}

function short(v) {
  if (v >= 10000) return `${Math.round(v / 1000)}k`;
  if (v >= 1000) return `${(v / 1000).toFixed(1)}k`;
  return String(Math.round(v));
}

function describe(y, c, d, grid, opts) {
  const when = grid.cols === 12 ? `${MONTHS_LONG[c]} ${y}` : `${y}, week ${c + 1}`;
  if (d.v === null) return `<b>${when}</b><br>Data gap (satellite outage)`;
  const b = baseline(d.others);
  const pr = percentileRank(d.v, d.others);
  const unc = opts.unc ? Math.round(opts.unc * 100) : null;
  let s = `<b>${when}</b><br>`;
  if (d.src === 'M') s += `≈ ${fmtInt(d.v)} hotspots${unc ? ` (±${unc}%)` : ''} · estimated from MODIS on the VIIRS scale`;
  else if (d.src === 'J') s += `${fmtInt(d.v)} hotspots · NOAA-20 converted to the S-NPP scale`;
  else s += `${fmtInt(d.v)} hotspots · observed (VIIRS)`;
  if (b) s += `<br>Usual: ${fmtInt(b.median)} (middle half ${fmtInt(b.p25)}–${fmtInt(b.p75)})`;
  if (pr !== null) s += `<br>Higher than ${Math.round(pr)}% of other years`;
  if (d.cat) s += `<br>${CAT_TEXT[d.cat]}`;
  return s;
}

export { fmt };
