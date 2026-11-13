// Jamra main app. Written with the help of an SI coding assistant (Claude Code), following Team Astro Byte's design.
import { $, $$, el, svg, fmt, fmtInt, pct, MONTHS, MONTHS_LONG, store, downloadBlob, toCSV, debounce, circleRing, boxRing, ordinal } from './util.js';
import { getJSON, loadArea, customArea, monthlyValues, monthLabel, monthIndex } from './data.js';
import { heroChart, monthBars, scatter, errorBars, driftChart } from './charts.js';
import { renderCalendar } from './calendar.js';
import { initMap, showArea, showLive, startDraw, clearDraw } from './map.js';
import { loadLive, loadStatus, renderBadge, renderAlerts, areaWarning, fetchLive, renderTable, downloadLiveCSV, LEVEL_LABEL } from './live.js';
import { baseline, percentileRank, category, CAT_LABEL, seasonStart, theilSen, mannKendall } from './stats.js';

const TEAM = [
  ['Shahd Farraj', 'Problem & users', 'Framed the problem for emergency teams, forest managers and firefighters; slides 1–2.'],
  ['Ahmed Etkaidek', 'NASA data', 'NASA FIRMS, MODIS vs VIIRS, sensor limits and the S-NPP to NOAA-20 change; slide 3.'],
  ['Aya Salman', 'Harmonization', 'Overlap calibration, shrinkage factor and model comparison; slide 4.'],
  ['Ahmad Akhras', 'Live demo', 'Demo story, click path and live system checks; slide 5.'],
  ['Diala Abubaker', 'Validation & limits', 'Cross-validation results and honest limits; slide 6.'],
  ['Tala Yousef', 'UX, impact & next steps', 'Calendar design, colour accessibility, impact and roadmap; slide 7.'],
];

const TERMS = {
  hotspot: 'A hotspot is one satellite pixel where the sensor saw unusual heat, usually a fire. One big fire can make many hotspots. Hotspots are not fires and not burned area.',
  modis: 'MODIS: a NASA sensor on the Terra and Aqua satellites (since 2000/2002). Pixels about 1 km wide. Nearing the end of its life.',
  viirs: 'VIIRS: a newer sensor (S-NPP since 2012, NOAA-20 since 2018, NOAA-21 since 2024). Pixels 375 m wide, so it sees smaller fires and more hotspots per fire.',
  harmonization: 'Harmonization: converting the old MODIS counts into "VIIRS-equivalent" counts so both periods can be compared fairly.',
  anomaly: 'Anomaly: how different a month is from its usual value (the median of the same month in other years).',
  percentile: 'Percentile: "higher than 90% of years" means only 1 in 10 years had more hotspots in that month.',
  frp: 'FRP (Fire Radiative Power): the heat a fire gives off, in megawatts, measured by the satellite.',
  api: 'The NASA FIRMS API allows about 5,000 transactions every 10 minutes, and each requested day counts. Twenty years is about 8,700 days per satellite, so one click would use up the whole limit. So the history is pre-built from NASA\'s archive files and refreshed automatically, while the newest days come straight from the API.',
};

const state = {
  areaId: 'greece', custom: null, from: 2003, to: 2025, sel: null, mode: 'abs', res: 'month',
  palette: 'viridis', staticFilter: true, hero: 'raw', liveWin: 1,
};
let meta, report, site, live, status, area, monthly, years;

// ---------------------------------------------------------------- tooltip
const tipEl = $('#tooltip');
const tip = {
  show(x, y, html) {
    tipEl.innerHTML = html; tipEl.hidden = false;
    const r = tipEl.getBoundingClientRect();
    tipEl.style.left = `${Math.min(x + 14, innerWidth - r.width - 8)}px`;
    tipEl.style.top = `${Math.max(8, y - r.height - 12)}px`;
  },
  hide() { tipEl.hidden = true; },
};

// ---------------------------------------------------------------- state <-> URL
function readURL() {
  const p = new URLSearchParams(location.search);
  const saved = store.get('jamra-state', {});
  Object.assign(state, saved);
  if (p.get('area')) { state.areaId = p.get('area'); state.custom = null; }
  if (p.get('from')) state.from = +p.get('from');
  if (p.get('to')) state.to = +p.get('to');
  if (p.get('mode')) state.mode = p.get('mode') === 'anomaly' ? 'anomaly' : 'abs';
  if (p.get('res')) state.res = p.get('res') === 'week' ? 'week' : 'month';
  if (p.get('pal')) state.palette = p.get('pal');
  if (p.get('month')) { const [y, m] = p.get('month').split('-').map(Number); state.sel = [y, m - 1]; }
  if (p.get('bbox')) { const b = p.get('bbox').split(',').map(Number); if (b.length === 4 && b.every(Number.isFinite)) state.custom = { ring: boxRing(b), label: `Box ${b.join(', ')}` }; }
  if (p.get('pt')) { const [la, lo, r] = p.get('pt').split(',').map(Number); if ([la, lo, r].every(Number.isFinite)) state.custom = { ring: circleRing(la, lo, r), label: `${r} km around ${la}, ${lo}` }; }
  if (p.get('poly')) {
    const ring = p.get('poly').split(';').map((s) => s.split(',').map(Number)).filter((c) => c.length === 2 && c.every(Number.isFinite));
    if (ring.length >= 4) state.custom = { ring, label: 'Shared polygon' };
  }
}
const writeURL = debounce(() => {
  const p = new URLSearchParams();
  if (state.custom) {
    const ring = state.custom.ring;
    p.set('poly', ring.map(([x, y]) => `${x.toFixed(3)},${y.toFixed(3)}`).join(';'));
  } else p.set('area', state.areaId);
  p.set('from', state.from); p.set('to', state.to);
  if (state.sel) p.set('month', `${state.sel[0]}-${String(state.sel[1] + 1).padStart(2, '0')}`);
  p.set('mode', state.mode);
  if (state.res === 'week') p.set('res', 'week');
  if (state.palette !== 'viridis') p.set('pal', state.palette);
  history.replaceState(null, '', `${location.pathname}?${p}${location.hash}`);
  const { custom, ...rest } = state;
  store.set('jamra-state', { ...rest, custom: null });
}, 200);

// ---------------------------------------------------------------- boot
async function boot() {
  readURL();
  [meta, report] = await Promise.all([getJSON('data/meta.json'), getJSON('data/model_report.json')]);
  site = await getJSON('data/site.json').catch(() => ({}));
  if (meta.demo) document.body.append(el('div', { class: 'demo-flag', text: 'DEMO DATA' }));
  $$('[data-product-name]').forEach((n) => { n.textContent = meta.product.name; });
  document.title = `${meta.product.name} · Burning Activity Calendar`;
  $$('[data-k-global]').forEach((n) => { n.textContent = `${meta.viirs_vs_modis_ratio.toFixed(1)}×`; });
  if (site.repo) $('#repo-link').href = site.repo;
  $$('[data-k-jn]').forEach((n) => { n.textContent = Number(report.noaa20_to_snpp.global).toFixed(2); });
  const lastYear = +meta.data_through.slice(0, 4) - (meta.data_through.slice(5, 7) === '12' ? 0 : 1);
  years = []; for (let y = +meta.start.slice(0, 4); y <= +meta.data_through.slice(0, 4); y++) years.push(y);
  state.from = Math.max(years[0], Math.min(state.from, lastYear));
  state.to = Math.min(lastYear, Math.max(state.to || lastYear, state.from));
  state.lastFullYear = lastYear;
  if (!meta.areas.some((a) => a.id === state.areaId)) state.areaId = 'greece';
  buildPickers();
  buildControls();
  renderStatic();
  initMap($('#map'));
  await selectArea(state.custom ? null : state.areaId, state.custom);
  refreshLive();
  setInterval(refreshLive, 10 * 60 * 1000);
  if ('serviceWorker' in navigator) navigator.serviceWorker.register('sw.js').catch(() => {});
}

async function refreshLive() {
  [live, status] = await Promise.all([loadLive(), loadStatus()]);
  renderBadge(status);
  renderAlerts(live, meta, (id) => { selectArea(id); $('#area').scrollIntoView(); });
  applyLiveLayer();
  if (area) renderKPIs();
}

function applyLiveLayer() {
  if (!live || !state.liveWin) { showLive([]); return; }
  const since = new Date(Date.parse(live.through_date + 'T00:00:00Z') - (state.liveWin - 1) * 864e5).toISOString().slice(0, 10);
  showLive(live.points.filter((p) => p[2] >= since).map((p) => ({ lat: p[0], lon: p[1], date: p[2], time: p[3], frp: p[4], conf: p[5], sat: p[6] })));
}

// ---------------------------------------------------------------- pickers
function buildPickers() {
  const mk = (box, kind) => {
    box.innerHTML = '';
    meta.areas.filter((a) => a.kind === kind).forEach((a) => {
      box.append(el('button', { type: 'button', class: 'chip', 'data-area': a.id, 'aria-pressed': 'false', text: a.label, onclick: () => selectArea(a.id) }));
    });
  };
  mk($('#preset-list'), 'preset');
  mk($('#country-list'), 'country');
  // tabs
  const tabs = $$('[role="tab"]');
  tabs.forEach((t, i) => {
    t.addEventListener('click', () => activateTab(t));
    t.addEventListener('keydown', (e) => {
      if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') {
        const n = tabs[(i + (e.key === 'ArrowRight' ? 1 : tabs.length - 1)) % tabs.length];
        activateTab(n); n.focus();
      }
    });
  });
  $('#draw-polygon').addEventListener('click', async () => {
    const ok = await startDraw('polygon', (ring, label) => selectArea(null, { ring, label }));
    $('#area-info').textContent = ok ? 'Click on the map to add points. Double-click (or click the first point) to finish.' : 'The map is not available.';
  });
  $('#draw-circle').addEventListener('click', async () => {
    const ok = await startDraw('circle', (ring, label) => selectArea(null, { ring, label }));
    $('#area-info').textContent = ok ? 'Click the centre, then click the edge of the circle.' : 'The map is not available.';
  });
  $('#draw-clear').addEventListener('click', () => { clearDraw(); selectArea('evia'); });
  $('#coords-form').addEventListener('submit', (e) => {
    e.preventDefault();
    const f = new FormData(e.target);
    const num = (k) => (f.get(k) === '' ? NaN : +f.get(k));
    const msg = $('#coords-msg');
    const [lat, lon, r] = [num('lat'), num('lon'), num('r')];
    const [w, s, ea, n] = [num('w'), num('s'), num('e'), num('n')];
    if ([w, s, ea, n].every(Number.isFinite)) {
      if (w >= ea || s >= n || Math.abs(w) > 180 || Math.abs(ea) > 180 || Math.abs(s) > 90 || Math.abs(n) > 90) { msg.textContent = 'Check the box: West < East and South < North.'; return; }
      msg.textContent = '';
      selectArea(null, { ring: boxRing([w, s, ea, n]), label: `Box W${w} S${s} E${ea} N${n}` });
    } else if ([lat, lon].every(Number.isFinite)) {
      if (Math.abs(lat) > 90 || Math.abs(lon) > 180) { msg.textContent = 'Latitude must be −90..90 and longitude −180..180.'; return; }
      const rr = Number.isFinite(r) && r > 0 ? Math.min(r, 300) : 25;
      msg.textContent = '';
      selectArea(null, { ring: circleRing(lat, lon, rr), label: `${rr} km around ${lat}, ${lon}` });
    } else msg.textContent = 'Enter a point (latitude and longitude) or all four box edges.';
  });
}

function activateTab(t) {
  $$('[role="tab"]').forEach((x) => { x.setAttribute('aria-selected', x === t); x.tabIndex = x === t ? 0 : -1; $('#' + x.getAttribute('aria-controls')).hidden = x !== t; });
}

function buildControls() {
  const fill = (sel, val) => { sel.innerHTML = ''; years.filter((y) => y <= state.lastFullYear).forEach((y) => sel.append(el('option', { value: y, text: y, selected: y === val }))); };
  fill($('#from-year'), state.from); fill($('#to-year'), state.to);
  $('#from-year').addEventListener('change', (e) => { state.from = Math.min(+e.target.value, state.to); e.target.value = state.from; update(); });
  $('#to-year').addEventListener('change', (e) => { state.to = Math.max(+e.target.value, state.from); e.target.value = state.to; update(); });
  $('#static-filter').checked = state.staticFilter;
  $('#static-filter').addEventListener('change', (e) => { state.staticFilter = e.target.checked; recompute(); update(); });
  $('#palette').value = state.palette;
  $('#palette').addEventListener('change', (e) => { state.palette = e.target.value; update(); });
  const seg = (attr, key, after) => $$(`[data-${attr}]`).forEach((b) => {
    b.setAttribute('aria-pressed', String(b.dataset[attr]) === String(state[key]));
    b.addEventListener('click', () => {
      state[key] = attr === 'livewin' ? +b.dataset[attr] : b.dataset[attr];
      $$(`[data-${attr}]`).forEach((x) => x.setAttribute('aria-pressed', x === b));
      after();
    });
  });
  seg('hero', 'hero', renderHero);
  seg('mode', 'mode', update);
  seg('res', 'res', update);
  seg('livewin', 'liveWin', applyLiveLayer);
  $('#dl-cal-csv').addEventListener('click', downloadCalendarCSV);
  $('#dl-cal-png').addEventListener('click', downloadCalendarPNG);
  $('#live-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const days = +new FormData(e.target).get('days');
    const rows = await fetchLive(area, days, site, live);
    if (rows.length) showLive(rows.map((r) => ({ lat: r.latitude, lon: r.longitude, date: r.acq_date, time: r.acq_time, frp: r.frp, conf: r.confidence, sat: r.satellite })));
  });
  $('#dl-live-csv').addEventListener('click', () => downloadLiveCSV(area.label));
  renderTable([]);
  addEventListener('resize', debounce(() => { renderCalendarNow(); }, 250));
  document.addEventListener('click', (e) => {
    const t = e.target.closest('.term');
    const pop = $('#term-pop');
    if (!t) { if (!e.target.closest('#term-pop')) pop.hidden = true; return; }
    pop.textContent = TERMS[t.dataset.term] || '';
    const r = t.getBoundingClientRect();
    pop.style.left = `${Math.min(scrollX + r.left, scrollX + innerWidth - 340)}px`;
    pop.style.top = `${scrollY + r.bottom + 6}px`;
    pop.hidden = false;
  });
}

// ---------------------------------------------------------------- area selection
async function selectArea(id, custom = null) {
  $('#area-info').textContent = 'Loading…';
  try {
    if (custom) {
      area = await customArea(custom.ring, custom.label, meta, report);
      state.custom = custom;
    } else {
      area = await loadArea(id);
      area.ring = area.box ? boxRing(area.box) : null;
      state.areaId = id; state.custom = null;
    }
  } catch (err) {
    $('#area-info').textContent = `Could not load this area (${err.message}).`;
    return;
  }
  $$('.chip').forEach((c) => c.setAttribute('aria-pressed', !state.custom && c.dataset.area === state.areaId));
  recompute();
  if (area.ring) showArea(area.ring);
  else showArea(countryRing(area));
  if (!state.sel) state.sel = defaultSelection();
  update();
}

function countryRing(a) {
  // countries: frame the map on the live box that contains them (outline drawn by the basemap)
  const boxes = { portugal: [-9.6, 36.9, -6.1, 42.2], spain: [-9.4, 35.9, 4.4, 43.9], greece: [19.3, 34.8, 29.7, 41.8], turkiye: [25.6, 35.8, 44.9, 42.2], cyprus: [32.2, 34.5, 34.7, 35.8], lebanon: [35.0, 33.0, 36.7, 34.8], jordan: [34.9, 29.1, 39.4, 33.4], palestine: [34.2, 31.2, 35.6, 32.6] };
  const b = boxes[a.id];
  return b ? boxRing(b) : null;
}

function recompute() {
  monthly = monthlyValues(area, state.staticFilter);
}

function defaultSelection() {
  // the month with the most hotspots in the record
  let best = 0;
  monthly.forEach((v, i) => { if (v !== null && v > (monthly[best] ?? -1)) best = i; });
  const lab = monthLabel(meta, best);
  return [+lab.slice(0, 4), +lab.slice(5, 7) - 1];
}

function update() {
  writeURL();
  renderAreaInfo();
  renderHero();
  renderKPIs();
  renderCalendarNow();
  renderDetail();
  renderSeason();
}

// ---------------------------------------------------------------- helpers
const val = (y, m) => { const i = monthIndex(meta, y, m + 1); return i >= 0 && i < monthly.length ? monthly[i] : null; };
const srcOf = (y, m) => { const i = monthIndex(meta, y, m + 1); return area.src[i] || 'G'; };
const winYears = () => years.filter((y) => y >= state.from && y <= state.to);
function annual(y, arr = monthly) {
  let s = 0, any = false;
  for (let m = 0; m < 12; m++) { const i = monthIndex(meta, y, m + 1); const v = arr[i]; if (v !== null && v !== undefined) { s += v; any = true; } }
  return any ? s : null;
}
function rawStitched(y) {
  let s = 0;
  for (let m = 0; m < 12; m++) {
    const i = monthIndex(meta, y, m + 1);
    const v = y < 2012 ? area.series.A[i] : area.series.N[i];
    if (v !== null && v !== undefined) s += v;
  }
  return s;
}

function renderAreaInfo() {
  const f = area.factor || {};
  const box = $('#area-info');
  box.innerHTML = '';
  $('#area-title').textContent = area.label;
  const kind = area.kind === 'custom' ? `Custom area · ${fmtInt(area.cells)} grid cells (0.1°)` : area.kind === 'preset' ? `Fire area in ${area.country === 'Turkey' ? 'Türkiye' : area.country} (approximate box)` : 'Country';
  box.append(el('b', { text: area.label }), el('br'), el('span', { text: kind }), el('br'));
  const unc = f.rel ?? (f.rel_se !== null && f.rel_se !== undefined ? Math.sqrt((meta.uncertainty_monthly || 0) ** 2 + (1.96 * f.rel_se) ** 2) : meta.uncertainty_monthly);
  box.append(el('span', { class: 'factor', html: null },
    `Conversion factor for this area: 1 MODIS hotspot ≈ ${fmt(f.k, 2)} VIIRS hotspots (±${Math.round((unc || 0) * 100)}% on monthly values). `,
    area.kind === 'country' ? `Country model: ${report.model_labels[report.chosen_model]}.` :
      `Based ${Math.round((f.own_weight || 0) * 100)}% on this area's own overlap years (${fmtInt(f.M_overlap)} MODIS / ${fmtInt(f.V_overlap)} VIIRS hotspots), the rest on the country value (${fmt(f.k_country, 2)}).`));
  if (['Palestine', 'Lebanon'].includes(area.country)) box.append(el('p', { class: 'msg', text: 'Note: in 2023–2025 this area saw armed conflict. Some hotspots may come from explosions or burning buildings, not wildfires or farm burning. Read changes here with care.' }));
  if (area.kind === 'custom' && area.cells === 0) box.append(el('p', { class: 'msg', text: 'No hotspots recorded here in 2003–2025, or the area is outside our coverage region (Portugal, Spain, Greece, Türkiye, Cyprus, Lebanon, Jordan, Palestine). Live data still work anywhere in the region.' }));
}

// ---------------------------------------------------------------- hero
function renderHero() {
  if (!area) return;
  const ys = years.filter((y) => y <= state.lastFullYear);
  const harmY = ys.map((y) => annual(y));
  const rawY = ys.map((y) => rawStitched(y));
  const aqua = ys.map((y) => (y >= 2012 ? annual(y, area.series.A) : null));
  const viirs = ys.map((y) => (y >= 2012 ? annual(y, area.series.N) : null));
  const conv = ys.map((y) => (y >= 2012 && aqua[ys.indexOf(y)] !== null ? aqua[ys.indexOf(y)] * area.factor.k : null));
  heroChart($('#hero-chart'), { years: ys, raw: rawY, harm: harmY, modisAqua: aqua, viirs, modisConverted: conv, mode: state.hero, tip });
  $('#hero-title').textContent = `Yearly hotspots · ${area.label}`;
  const pre = ys.filter((y) => y <= 2011), post = ys.filter((y) => y >= 2012);
  const avg = (arr, sel) => { const v = sel.map((y) => arr[ys.indexOf(y)]).filter((x) => x !== null); return v.length ? v.reduce((a, b) => a + b, 0) / v.length : null; };
  const rawJump = avg(rawY, post) / avg(rawY, pre), harmJump = avg(harmY, post) / avg(harmY, pre);
  const span = `${post[0]}–${post[post.length - 1]}`, spanPre = `${pre[0]}–${pre[pre.length - 1]}`;
  const cap = $('#hero-caption');
  if (state.hero === 'raw') cap.textContent = Number.isFinite(rawJump) ? `Raw: the yearly average for ${span} is ${rawJump.toFixed(1)}× the average for ${spanPre}. Most of that jump is the sharper sensor, not more fire. Press "Harmonized".` : '';
  else cap.textContent = Number.isFinite(harmJump) ? `Harmonized: ${span} vs ${spanPre} is ${harmJump.toFixed(1)}×, so the fake rise is gone. Hatched bars are estimated from MODIS. The dashed line is MODIS converted to the VIIRS scale in the overlap years; it follows the dark VIIRS bars.` : '';
}

// ---------------------------------------------------------------- KPIs
function renderKPIs() {
  const g = $('#kpi-grid');
  g.innerHTML = '';
  const wy = winYears();
  // peak month
  const med = MONTHS.map((_, m) => baseline(wy.map((y) => val(y, m)))?.median ?? 0);
  const peak = med.indexOf(Math.max(...med));
  // most active year
  const tot = wy.map((y) => [y, annual(y)]).filter(([, v]) => v !== null);
  const top = tot.reduce((a, b) => (b[1] > a[1] ? b : a), [null, -1]);
  const total = tot.reduce((a, [, v]) => a + v, 0);
  let rawTotal = 0;
  wy.forEach((y) => { for (let m = 0; m < 12; m++) { const i = monthIndex(meta, y, m + 1); rawTotal += (y < 2012 ? (area.series.A[i] || 0) + (area.series.T?.[i] || 0) : (area.series.N[i] || 0)); } });
  // current period vs median
  const w = areaWarning(area, live, meta, monthly);
  let changeV = '–', changeD = 'Live data unavailable';
  if (live && w.level !== 'unknown' && w.median !== undefined) {
    const ch = w.median > 0 ? (w.mtd - w.median) / w.median : null;
    const [ly, lm] = live.month.split('-').map(Number);
    changeV = ch === null ? (w.mtd > 0 ? 'new' : '0%') : `${ch >= 0 ? '+' : ''}${Math.round(ch * 100)}%`;
    changeD = `${MONTHS[lm - 1]} ${w.from_day ?? 1}–${w.day}, ${ly}: ${fmt(w.mtd, 0)} vs usual ${fmt(w.median, 0)} (NOAA-20 on the S-NPP scale${w.approximate ? ', approximate' : ''})`;
  } else {
    // latest archive month vs its usual
    const li = monthly.length - 1, lab = monthLabel(meta, li);
    const ly = +lab.slice(0, 4), lm = +lab.slice(5, 7) - 1;
    const b = baseline(wy.filter((y) => y !== ly).map((y) => val(y, lm)));
    if (b && monthly[li] !== null) {
      const ch = b.median > 0 ? (monthly[li] - b.median) / b.median : null;
      changeV = ch === null ? '–' : `${ch >= 0 ? '+' : ''}${Math.round(ch * 100)}%`;
      changeD = `${MONTHS[lm]} ${ly} vs usual ${MONTHS[lm]} (${fmt(b.median, 0)})`;
    }
  }
  const kpi = (k, v, d, extra) => g.append(el('div', { class: 'kpi' }, el('div', { class: 'k', text: k }), extra || el('div', { class: 'v', text: v }), el('div', { class: 'd', text: d })));
  kpi('Peak month', MONTHS_LONG[peak], `Usual ${MONTHS_LONG[peak]}: ${fmt(med[peak], 0)} hotspots (${state.from}–${state.to})`);
  kpi('Now vs usual', changeV, changeD);
  kpi('Most active year', top[0] ?? '–', top[0] ? `${fmtInt(top[1])} VIIRS-equivalent hotspots` : '');
  const lvl = w.level || 'unknown';
  kpi('Early warning now', '', w.percentile !== undefined && lvl !== 'unknown' ? `Higher than ${Math.round(w.percentile)}% of past years for these days${w.approximate ? ' · approximate' : ''}` : 'Waiting for live data',
    el('div', { class: 'v' }, el('span', { class: `lvl lvl-${lvl}`, text: LEVEL_LABEL[lvl] })));
  kpi('Total detections', fmtInt(total), `${state.from}–${state.to}, VIIRS-equivalent · ${fmtInt(rawTotal)} raw satellite detections`);
}

// ---------------------------------------------------------------- calendar
function weeklyGrid() {
  if (!area.daily) return null;
  const d0 = Date.parse(area.daily_start + 'T00:00:00Z');
  const cache = {};
  return (y, c) => {
    const key = y;
    if (!cache[key]) {
      const arr = new Array(52).fill(0);
      const has = new Array(52).fill(false);
      const start = (Date.UTC(y, 0, 1) - d0) / 864e5;
      const end = (Date.UTC(y + 1, 0, 1) - d0) / 864e5;
      for (let k = start; k < end; k++) {
        if (k < 0 || k >= area.daily.length) continue;
        const v = area.daily[k];
        const wk = Math.min(51, Math.floor((k - start) / 7));
        if (v !== null) { arr[wk] += v; has[wk] = true; }
      }
      cache[key] = arr.map((v, i) => (has[i] ? Math.round(v * 10) / 10 : null));
    }
    return cache[key][c];
  };
}

function renderCalendarNow() {
  if (!area) return;
  const ys = years;
  let grid;
  const weekly = state.res === 'week' ? weeklyGrid() : null;
  if (state.res === 'week' && !weekly) {
    state.res = 'month';
    $$('[data-res]').forEach((x) => x.setAttribute('aria-pressed', x.dataset.res === 'month'));
    $('#area-info').append(el('p', { class: 'msg', text: 'Weekly view is available for countries and fire areas (custom areas use monthly grid data).' }));
  }
  if (state.res === 'week') {
    grid = { years: ys, cols: 52, value: weekly, src: (y) => (y < 2012 ? 'M' : 'N'), label: (c) => (c % 4 === 0 ? MONTHS[Math.min(11, Math.floor((c * 7) / 30.5))] : '') };
  } else {
    grid = { years: ys, cols: 12, value: (y, m) => val(y, m), src: (y, m) => srcOf(y, m), label: (c) => MONTHS[c] };
  }
  renderCalendar($('#cal'), $('#cal-legend'), grid, {
    mode: state.mode, palette: state.palette, anomalyCfg: meta.anomaly, baselineYears: [state.from, state.to], tip,
    selected: state.res === 'month' ? state.sel : null,
    onSelect: (y, c) => { if (state.res === 'month') { state.sel = [y, c]; writeURL(); renderDetail(true); renderCalendarNow(); } else renderWeekDetail(y, c, grid); },
  });
}

// ---------------------------------------------------------------- detail panel
function sentence(y, m) {
  const v = val(y, m);
  const wy = winYears().filter((yy) => yy !== y);
  const others = wy.map((yy) => val(yy, m));
  const b = baseline(others);
  const pr = percentileRank(v, others);
  const src = srcOf(y, m);
  if (v === null) return `${MONTHS_LONG[m]} ${y}, ${area.label}: data gap (satellite outage), no value shown.`;
  let s = `${MONTHS_LONG[m]} ${y}, ${area.label}: ${fmtInt(v)} hotspots.`;
  if (b) {
    s += ` A typical ${MONTHS_LONG[m]} (${state.from}–${state.to}) has ${fmtInt(b.median)}.`;
    if (b.median > 0) {
      const ratio = v / b.median;
      s += ratio >= 1.15 ? ` That's ${ratio.toFixed(1)}× typical,` : ratio <= 0.87 ? ` That's ${Math.round((1 - ratio) * 100)}% below typical,` : ' That\'s about typical,';
    }
    if (pr !== null) s += pr >= 99.5 ? ` the highest ${MONTHS_LONG[m]} in ${state.from}–${state.to}.` : pr <= 0.5 ? ` the lowest ${MONTHS_LONG[m]} in ${state.from}–${state.to}.` : ` higher than ${Math.round(pr)}% of ${MONTHS_LONG[m]}s.`;
  }
  if (src === 'M') {
    const unc = area.factor?.rel ?? meta.uncertainty_monthly;
    s += ` Values before 2012 are estimated from MODIS (±${Math.round(unc * 100)}%).`;
  } else if (src === 'J') s += ' This month uses NOAA-20 data converted to the S-NPP scale (S-NPP outage).';
  return s;
}

function renderDetail(focus = false) {
  const box = $('#detail');
  if (!state.sel || state.res !== 'month') { box.hidden = true; return; }
  const [y, m] = state.sel;
  const i = monthIndex(meta, y, m + 1);
  const v = val(y, m);
  const others = winYears().filter((yy) => yy !== y).map((yy) => val(yy, m));
  const b = baseline(others), pr = percentileRank(v, others), cat = category(v, others, meta.anomaly);
  const src = area.src[i];
  const raw = y < 2012 ? area.series.A[i] : area.series.N[i];
  box.hidden = false;
  box.innerHTML = '';
  box.append(
    el('button', { class: 'btn ghost small close', type: 'button', text: 'Close', onclick: () => { box.hidden = true; } }),
    el('h3', { text: `${MONTHS_LONG[m]} ${y} · ${area.label}` }),
    el('p', { class: 'sentence', text: sentence(y, m) }),
  );
  const facts = el('div', { class: 'facts' });
  const fact = (k, vv) => facts.append(el('div', {}, el('b', { text: vv }), k));
  fact(src === 'M' ? 'VIIRS-equivalent (estimated)' : 'VIIRS hotspots', fmtInt(v));
  fact(y < 2012 ? 'Raw MODIS Aqua hotspots' : 'Raw VIIRS S-NPP hotspots', fmtInt(raw));
  if (src === 'M' && area.lo[i] !== null) fact('Uncertainty range', `${fmtInt(area.lo[i])}–${fmtInt(area.hi[i])}`);
  if (b) fact(`Usual ${MONTHS[m]} (median)`, fmtInt(b.median));
  if (b) fact('Middle half of years', `${fmtInt(b.p25)}–${fmtInt(b.p75)}`);
  if (pr !== null) fact('Percentile rank', `${ordinal(Math.round(pr))}`);
  if (cat) fact('Category', CAT_LABEL[cat]);
  box.append(facts);
  const chart = el('div', { class: 'chart' });
  box.append(el('h4', { class: 'h4', text: `${MONTHS_LONG[m]} in every year (selected year in orange)` }), chart);
  const ys = years.filter((yy) => yy >= state.from && yy <= Math.max(state.to, y));
  monthBars(chart, {
    years: ys, values: ys.map((yy) => val(yy, m)), selYear: y, month: m + 1,
    src: ys.map((yy) => srcOf(yy, m)), lo: ys.map((yy) => area.lo[monthIndex(meta, yy, m + 1)]), hi: ys.map((yy) => area.hi[monthIndex(meta, yy, m + 1)]),
    tip, onPick: (yy) => { state.sel = [yy, m]; writeURL(); renderDetail(); renderCalendarNow(); },
  });
  if (focus) box.focus({ preventScroll: true });
}

function renderWeekDetail(y, c, grid) {
  const box = $('#detail');
  const v = grid.value(y, c);
  const others = winYears().filter((yy) => yy !== y).map((yy) => grid.value(yy, c));
  const b = baseline(others), pr = percentileRank(v, others);
  box.hidden = false;
  box.innerHTML = '';
  box.append(el('button', { class: 'btn ghost small close', type: 'button', text: 'Close', onclick: () => { box.hidden = true; } }),
    el('h3', { text: `${y}, week ${c + 1} · ${area.label}` }),
    el('p', { class: 'sentence', text: v === null ? 'Data gap.' : `${fmtInt(v)} hotspots in week ${c + 1} of ${y}. A typical week ${c + 1} (${state.from}–${state.to}) has ${fmtInt(b?.median)}. Higher than ${Math.round(pr ?? 0)}% of other years.${y < 2012 ? ` Estimated from MODIS (±${Math.round(meta.uncertainty_monthly * 100)}% or more for single weeks).` : ''}` }));
}

// ---------------------------------------------------------------- season start
function renderSeason() {
  const box = $('#season');
  box.innerHTML = '';
  const ys = winYears(), starts = [], sy = [];
  ys.forEach((y) => {
    const vals = MONTHS.map((_, m) => val(y, m));
    if (vals.some((v) => v === null)) return;
    const s = seasonStart(vals);
    if (s) { starts.push(s); sy.push(y); }
  });
  box.append(el('h3', { class: 'h4', text: 'Is the fire season starting earlier?' }));
  if (starts.length < 6) { box.append(el('p', { text: 'Not enough hotspots in this area to judge the season start.' })); return; }
  const slope = theilSen(sy, starts) * 10, mk = mannKendall(starts);
  const medStart = Math.round(baseline(starts).median);
  const dir = slope < -0.05 ? `${Math.abs(slope).toFixed(1)} months earlier per decade` : slope > 0.05 ? `${slope.toFixed(1)} months later per decade` : 'no clear shift';
  box.append(el('p', { text: `Season start = the first month when a year reaches 10% of its hotspots. Typical start here: ${MONTHS_LONG[medStart - 1]}. Trend ${state.from}–${state.to}: ${dir}. ${mk.p < 0.05 ? `This trend is statistically significant (Mann–Kendall p = ${mk.p.toFixed(3)}).` : `This is not statistically significant (Mann–Kendall p = ${mk.p.toFixed(2)}), so we cannot say the season is shifting.`}` }));
  const W = 900, H = 120, mL = 40;
  const s = svg('svg', { viewBox: `0 0 ${W} ${H}`, role: 'img', 'aria-label': 'Season start month by year' });
  const x = (y) => mL + ((y - ys[0]) / Math.max(1, ys[ys.length - 1] - ys[0])) * (W - mL - 20);
  const yy = (m) => 10 + ((m - 1) / 11) * (H - 30);
  [1, 4, 7, 10].forEach((m) => { s.append(svg('text', { x: 4, y: yy(m) + 4, 'font-size': 11, fill: '#5f6b80' }, document.createTextNode(MONTHS[m - 1]))); s.append(svg('line', { x1: mL, x2: W - 20, y1: yy(m), y2: yy(m), stroke: '#eef0f4' })); });
  sy.forEach((y, i) => s.append(svg('circle', { cx: x(y), cy: yy(starts[i]), r: 5, fill: y < 2012 ? '#7b8db5' : '#14213d' })));
  sy.filter((y, i) => i % 3 === 0).forEach((y) => s.append(svg('text', { x: x(y), y: H - 4, 'text-anchor': 'middle', 'font-size': 11, fill: '#5f6b80' }, document.createTextNode(String(y)))));
  box.append(s);
}

// ---------------------------------------------------------------- downloads
function downloadCalendarCSV() {
  const rows = [];
  for (let i = 0; i < monthly.length; i++) {
    const lab = monthLabel(meta, i);
    const y = +lab.slice(0, 4), m = +lab.slice(5, 7) - 1;
    const others = winYears().filter((yy) => yy !== y).map((yy) => val(yy, m));
    const b = baseline(others), pr = percentileRank(monthly[i], others), cat = category(monthly[i], others, meta.anomaly);
    rows.push({
      month: lab, area: area.label, hotspots_viirs_equivalent: monthly[i], source: { M: 'estimated from MODIS Aqua', N: 'VIIRS S-NPP', J: 'VIIRS NOAA-20 converted', G: 'data gap' }[area.src[i]],
      low: area.lo[i], high: area.hi[i], raw_modis_aqua: area.series.A[i], raw_modis_terra: area.series.T ? area.series.T[i] : '', raw_viirs_snpp: area.series.N[i], raw_viirs_noaa20: area.series.J[i],
      usual_median: b ? +b.median.toFixed(1) : '', percentile_rank: pr === null ? '' : +pr.toFixed(1), category: cat ? CAT_LABEL[cat] : '',
    });
  }
  const header = Object.keys(rows[0]);
  const note = `# ${meta.product.name} harmonized burning activity calendar. Data: NASA FIRMS. Unit: hotspots (satellite fire pixels), not fires. Baseline years ${state.from}-${state.to}. Static-source filter ${state.staticFilter ? 'on' : 'off'}. Generated ${new Date().toISOString()}\n`;
  downloadBlob(`jamra_calendar_${area.id}_${state.from}-${state.to}.csv`, note + toCSV(rows, header));
}

async function downloadCalendarPNG() {
  const src = $('#cal svg');
  if (!src) return;
  const clone = src.cloneNode(true);
  const w = +src.getAttribute('width'), h = +src.getAttribute('height');
  const title = `${meta.product.name} · ${area.label} · ${state.mode === 'anomaly' ? 'anomaly vs usual' : 'hotspots (VIIRS-equivalent)'} · data: NASA FIRMS`;
  const pad = 40;
  const wrapper = svg('svg', { xmlns: 'http://www.w3.org/2000/svg', width: w + 20, height: h + pad + 10 });
  wrapper.append(svg('rect', { width: '100%', height: '100%', fill: '#ffffff' }));
  wrapper.append(svg('text', { x: 10, y: 24, 'font-size': 15, 'font-family': 'Segoe UI, Arial, sans-serif', fill: '#14213d' }, document.createTextNode(title)));
  clone.setAttribute('x', 10); clone.setAttribute('y', pad);
  clone.querySelectorAll('text').forEach((t) => { t.setAttribute('font-family', 'Segoe UI, Arial, sans-serif'); if (!t.getAttribute('font-size')) t.setAttribute('font-size', 11); if (!t.getAttribute('fill')) t.setAttribute('fill', '#3d4a63'); });
  wrapper.append(clone);
  const blob = new Blob([new XMLSerializer().serializeToString(wrapper)], { type: 'image/svg+xml' });
  const url = URL.createObjectURL(blob);
  const img = new Image();
  img.onload = () => {
    const c = document.createElement('canvas');
    const scale = 2;
    c.width = (w + 20) * scale; c.height = (h + pad + 10) * scale;
    const ctx = c.getContext('2d'); ctx.scale(scale, scale); ctx.drawImage(img, 0, 0);
    c.toBlob((png) => downloadBlob(`jamra_calendar_${area.id}.png`, png, 'image/png'));
    URL.revokeObjectURL(url);
  };
  img.src = url;
}

// ---------------------------------------------------------------- static report sections
function renderStatic() {
  // team
  const tg = $('#team-grid');
  TEAM.forEach(([n, r, d]) => tg.append(el('div', { class: 'member' }, el('b', { text: n }), el('span', { text: r }), el('p', { class: 'fine', text: d }))));
  // why not just
  const cv = report.cv;
  const order = ['M0', 'M1', 'M2', 'M3', 'M4', 'M5'];
  const t = el('table', {}, el('thead', {}, el('tr', {}, ...['Approach', 'Monthly error (MAE)', 'Typical % error', 'Total bias', 'Verdict'].map((h) => el('th', { scope: 'col', text: h })))));
  const tb = el('tbody');
  const verdict = {
    M0: 'Shows the problem: VIIRS-era counts look much higher.', M1: 'Simple, but ignores country differences.', M2: 'Simple and fair per country.',
    M3: 'Adds seasons; leans on the country value when a month has few fires.', M4: 'Curved fit; can drift at the extremes.', M5: 'Matches distributions; needs many years.',
  };
  order.forEach((m) => {
    const r = cv[m].monthly;
    tb.append(el('tr', { class: m === report.chosen_model ? 'chosen' : '' },
      el('td', { text: `${m}: ${report.model_labels[m]}${m === report.chosen_model ? ' ✓ chosen' : ''}` }),
      el('td', { text: fmt(r.mae, 1) }), el('td', { text: pct(r.mdape) }), el('td', { text: pct(r.bias, 1) }), el('td', { text: verdict[m] })));
  });
  tb.append(el('tr', {}, el('td', { text: 'Use VIIRS only' }), el('td', { text: '–' }), el('td', { text: '–' }), el('td', { text: '–' }), el('td', { text: 'Honest but throws away 2003–2011, nine years of history (including Greece 2007).' })));
  t.append(tb);
  $('#why-table').append(t, el('p', { class: 'fine', text: report.choice_reason + ' Errors come from leave-one-year-out cross-validation on the calibration years ' + report.calibration.years.join(', ') + '.' }));

  // validation
  scatter($('#scatter'), { points: report.scatter, tip });
  $('#scatter-cap').textContent = 'Orange: harmonized MODIS. Grey: raw MODIS. Dashed: perfect agreement. Each dot is one country-month in a hidden year.';
  errorBars($('#err-bars'), {
    rows: order.map((m) => ({ id: m, label: `${m} ${report.model_labels[m]}`, value: cv[m].monthly.mdape, text: pct(cv[m].monthly.mdape) })),
    chosen: report.chosen_model, metricLabel: 'Typical % error',
  });
  $('#err-cap').textContent = `Typical (median) % error per month, months with at least 10 VIIRS hotspots. Raw MODIS: ${pct(cv.M0.monthly.mdape)} → harmonized (${report.chosen_model}): ${pct(cv[report.chosen_model].monthly.mdape)}.`;
  const vk = $('#val-kpis');
  const ca = report.colour_agreement;
  const kp = (k, v, d) => vk.append(el('div', { class: 'kpi' }, el('div', { class: 'k', text: k }), el('div', { class: 'v', text: v }), el('div', { class: 'd', text: d })));
  kp('Calendar colours agree', `${fmt(ca.same_colour_pct, 0)}%`, `Same anomaly colour from harmonized MODIS as from real VIIRS (${fmtInt(ca.months)} country-months). Raw MODIS: ${fmt(ca.without_harmonization_pct, 0)}%.`);
  kp('Uncertainty', `±${Math.round(report.uncertainty.monthly_rel * 100)}%`, `on a month · ±${Math.round(report.uncertainty.annual_rel * 100)}% on a year (typical cross-validated error)`);
  const fr = report.frp_test;
  kp('FRP test', fr.validated ? 'Passed' : 'Not supported', `Is summed fire heat (FRP) more stable between sensors than counts? Variation of the ratio: FRP ${fmt(fr.pooled_cv_frp_ratio, 2)} vs counts ${fmt(fr.pooled_cv_count_ratio, 2)}. ${fr.validated ? 'FRP could be offered.' : 'So the calendar uses counts.'}`);
  const jn = report.noaa20_to_snpp;
  kp('NOAA-20 → S-NPP scale', `×${fmt(jn.global, 2)}`, `Live counts come from NOAA-20 since S-NPP stopped (2 Nov 2026) and are multiplied by this factor to stay on the S-NPP scale. Measured on ${fmtInt(jn.months_used)} country-months, 2018–2025.`);
  const ref = median(report.drift.filter((d) => d.ratio_N_over_A && d.months >= 10).map((d) => d.ratio_N_over_A));
  driftChart($('#drift'), { drift: report.drift, ref, tol: 0.15, tip });
  $('#drift-cap').textContent = `Each dot = one year's VIIRS S-NPP ÷ MODIS Aqua hotspots (8 countries). ${report.calibration.rule} The headline ${meta.viirs_vs_modis_ratio.toFixed(1)}× pools all hotspots of the calibration years instead of taking the median year. Filled dots = years used to calibrate. MODIS satellites have been drifting in orbit in recent years, so the ratio can shift; we check it every year.`;
  // where it struggles: per-country error
  const per = {};
  report.scatter.forEach((p) => { if (p.V >= 10) { (per[p.c] = per[p.c] || []).push(Math.abs(p.P - p.V) / p.V); } });
  const rows = Object.entries(per).map(([c, e]) => [c, median(e), e.length]).sort((a, b) => b[1] - a[1]);
  const st = $('#struggle');
  st.append(el('p', { text: 'Typical monthly error by country (months with 10+ VIIRS hotspots). Small countries have few fires, so errors are larger there.' }));
  st.append(el('table', { class: 'table' }, el('thead', {}, el('tr', {}, el('th', { text: 'Country' }), el('th', { text: 'Typical error' }), el('th', { text: 'Months' }))),
    el('tbody', {}, ...rows.map(([c, e, n]) => el('tr', {}, el('td', { text: c === 'Turkey' ? 'Türkiye' : c }), el('td', { text: pct(e) }), el('td', { text: n }))))));
  if (report.outages.length) st.append(el('p', { class: 'fine', text: `Outage months detected and excluded from calibration: ${report.outages.map((o) => `${o.month} (${o.sensor === 'N' ? 'S-NPP' : o.sensor === 'A' ? 'Aqua' : 'NOAA-20'})`).join(', ')}.` }));
}

function median(xs) { const s = [...xs].sort((a, b) => a - b); const n = s.length; return n ? (n % 2 ? s[(n - 1) / 2] : (s[n / 2 - 1] + s[n / 2]) / 2) : null; }

boot().catch((err) => {
  console.error(err);
  $('#main').prepend(el('div', { class: 'wrap card', style: 'margin-top:16px;border-color:#c92a2a' }, `Sorry, the data could not be loaded (${err.message}). Please reload the page.`));
});
