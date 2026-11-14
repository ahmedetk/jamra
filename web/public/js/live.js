// Live system in the browser: status badge, Alert Center, on-demand NASA FIRMS data.
// Written with the help of an SI coding assistant (Claude Code).
import { $, el, fmt, fmtInt, parseCSV, pointInRing, ringBBox, toCSV, downloadBlob } from './util.js';
import { getJSON } from './data.js';
import { warningLevel } from './stats.js';

export const LEVEL_LABEL = { normal: 'Normal', elevated: 'Elevated', high: 'High', extreme: 'Extreme', unknown: 'No data', stale: 'Outdated' };
const LEVEL_RANK = { extreme: 4, high: 3, elevated: 2, normal: 1, unknown: 0, stale: 0 };
const MONTHS3 = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

export async function loadLive() {
  try { return await getJSON('data/live/live.json', { fresh: true }); } catch { return null; }
}
export async function loadStatus() {
  try { return await getJSON('data/live/status.json', { fresh: true }); } catch { return null; }
}

function ago(iso) {
  const h = (Date.now() - Date.parse(iso)) / 36e5;
  if (h < 1) return `${Math.max(1, Math.round(h * 60))} min ago`;
  if (h < 48) return `${Math.round(h)} h ago`;
  return `${Math.round(h / 24)} days ago`;
}
const utc = (iso) => `${iso.slice(0, 10)} ${iso.slice(11, 16)} UTC`;

/** Freshness of the live data: 'live' (≤ 6 h), 'delayed' (≤ 30 h), 'stale' (older), 'none'. */
export function liveState(status, live) {
  if (!live || !status || !status.last_success_utc) return { state: 'none', hours: null };
  const hours = (Date.now() - Date.parse(status.last_success_utc)) / 36e5;
  return { state: hours <= 6 ? 'live' : hours <= 30 ? 'delayed' : 'stale', hours, failed: status.ok === false };
}

export function periodText(live, a) {
  const [y, m] = live.month.split('-').map(Number);
  const from = a?.from_day ?? live.from_day ?? 1;
  const day = a?.day ?? live.day;
  return `${from}–${day} ${MONTHS3[m - 1]} ${y}, ${from === 1 ? 'month-to-date' : `partial month (data from day ${from})`}`;
}

export function renderBadge(status, live) {
  const b = $('#status-badge');
  if (!b) return;
  const t = b.querySelector('.txt');
  b.classList.remove('live', 'delayed', 'down');
  const s = liveState(status, live);
  if (s.state === 'none') {
    b.classList.add('down'); t.textContent = 'Live data unavailable';
    b.title = 'Could not read the live status. The history still works.';
    return;
  }
  if (s.state === 'live') { b.classList.add('live'); t.textContent = `Live · updated ${ago(status.last_success_utc)}`; }
  else if (s.state === 'delayed') { b.classList.add('delayed'); t.textContent = `Delayed · updated ${ago(status.last_success_utc)}`; }
  else { b.classList.add('down'); t.textContent = `Outdated · updated ${ago(status.last_success_utc)}`; }
  b.title = `Source: ${status.source || 'NASA FIRMS'}. Last check: ${status.last_attempt_utc || '?'}${status.message ? ' · ' + status.message : ''}`;
}

export function renderStatusPanel(status, live) {
  const box = $('#data-status');
  if (!box) return;
  box.innerHTML = '';
  const s = liveState(status, live);
  const rows = [];
  if (s.state === 'none') rows.push(['down', 'Live data unavailable', 'The status file could not be read. Alerts are hidden until data arrive.']);
  else {
    rows.push([s.state === 'live' ? 'ok' : 'warn', s.state === 'live' ? 'Data up to date' : s.state === 'delayed' ? 'Data delayed' : 'Data outdated',
      `· updated ${ago(status.last_success_utc)} (${utc(status.last_success_utc)}) · NASA FIRMS API`]);
    if (s.failed) rows.push(['down', 'Last update failed', `· showing the last good data (${utc(status.last_attempt_utc)})`]);
    if ((live.from_day ?? 1) > 1) rows.push(['warn', 'Partial month', `· days ${live.from_day}–${live.day} compared`]);
  }
  rows.forEach(([cls, h, t]) => box.append(el('div', { class: `st st-${cls}` }, el('b', { text: h }), el('span', { text: ' ' + t }))));
}

export function renderAlerts(live, meta, status, onPick) {
  const box = $('#alert-list');
  if (!box) return;
  box.innerHTML = '';
  const s = liveState(status, live);
  if (s.state === 'none' || !live.areas) {
    box.append(el('p', { class: 'note', text: 'No live data right now. The Calendar still works.' }));
    return;
  }
  const label = Object.fromEntries(meta.areas.map((a) => [a.id, a.label]));
  const rows = Object.entries(live.areas).sort((a, b) => (LEVEL_RANK[b[1].level] - LEVEL_RANK[a[1].level]) || (b[1].percentile ?? 0) - (a[1].percentile ?? 0));
  for (const [id, a] of rows) {
    // never show a reassuring "Normal" on outdated data
    const lvl = s.state === 'stale' ? 'stale' : a.level;
    const partial = (a.from_day ?? 1) > 1;
    const diff = a.median > 0 ? Math.round(((a.mtd - a.median) / a.median) * 100) : null;
    const card = el('button', { class: `alert ${lvl}`, type: 'button', onclick: () => onPick(id) },
      el('h3', {}, `${label[id] || id} `, el('span', { class: `lvl lvl-${lvl === 'stale' ? 'unknown' : lvl}`, text: LEVEL_LABEL[lvl] }),
        s.state === 'delayed' ? el('span', { class: 'lvl lvl-elevated tag', text: 'Delayed' }) : null,
        partial ? el('span', { class: 'lvl lvl-unknown tag', text: 'Partial data' }) : null),
      el('p', { class: 'period', text: periodText(live, a) }),
      el('p', { class: 'value', text: a.level === 'unknown' ? 'Not enough history' :
        `${fmt(a.mtd, 0)} hotspots · usual ${fmt(a.median, 0)}${diff === null ? '' : ` (${diff >= 0 ? '+' : ''}${diff}%)`}` }),
      a.level === 'unknown' ? null : el('p', { text: `Higher than ${Math.round(a.percentile)}% of past years` }),
      el('p', { class: 'fine', text: `Updated ${utc(status.last_success_utc)} · ${s.state === 'live' ? 'data up to date' : s.state === 'delayed' ? 'data delayed' : 'data outdated'} · NOAA-20 × ${fmt(a.k_jn, 2)}` }));
    if (id === 'palestine' || id === 'lebanon') card.append(el('p', { class: 'fine', text: 'Conflict area: some hotspots may not be fires.' }));
    box.append(card);
  }
}

/** Early-warning level for any area: live values for countries/presets, approximate for custom areas. */
export function areaWarning(area, live, meta, monthlyVals, status) {
  const s = liveState(status, live);
  if (s.state === 'none') return { level: 'unknown', note: 'live data unavailable' };
  if (s.state === 'stale') return { level: 'stale', note: 'live data outdated' };
  if (area.kind !== 'custom' && live.areas && live.areas[area.id]) return { ...live.areas[area.id], approximate: false };
  if (!area.ring) return { level: 'unknown' };
  const [y, m] = live.month.split('-').map(Number);
  const day = live.day;
  // the points file holds the last 7 days, so a custom area compares only those days
  const from = Math.max(live.from_day ?? 1, day - 6, 1);
  const inside = live.points.filter((p) => p[2].startsWith(live.month) && +p[2].slice(8, 10) >= from && +p[2].slice(8, 10) <= day && pointInRing(p[1], p[0], area.ring));
  const mtd = inside.length * (area.factor?.kJN ?? 1);
  const dim = new Date(Date.UTC(y, m, 0)).getUTCDate();
  const [y0] = meta.start.split('-').map(Number);
  const others = [];
  for (let yy = y0; yy < y; yy++) {
    const i = (yy - y0) * 12 + (m - 1);
    if (monthlyVals[i] !== null && monthlyVals[i] !== undefined) others.push(monthlyVals[i] * ((day - from + 1) / dim));
  }
  return { ...warningLevel(mtd, others, meta.anomaly), mtd, day, from_day: from, approximate: true };
}
// ---------------------------------------------------------------- explorer
let lastRows = [];
let sortKey = 'datetime', sortDir = -1;
const COLS = [
  ['datetime', 'Date / time (UTC)'], ['satellite', 'Satellite'], ['confidence', 'Confidence'],
  ['frp', 'FRP (MW)'], ['latitude', 'Latitude'], ['longitude', 'Longitude'],
];

export async function fetchLive(area, days, site, live, opts = {}) {
  // opts.ring: query box outline; opts.keep(lat, lon): keep a point (countries use the archive's cell -> country map)
  const ring = opts.ring || area.ring;
  const keep = opts.keep || ((lat, lon) => pointInRing(lon, lat, ring));
  const stamp = $('#live-stamp');
  if (!ring) { stamp.textContent = 'Choose an area first.'; return []; }
  const [w, s, e, n] = ringBBox(ring).map((v) => +v.toFixed(3));
  let rows = [], source = '', when = '';
  if (site && site.proxy) {
    stamp.textContent = 'Asking NASA FIRMS…';
    try {
      const url = `${site.proxy.replace(/\/$/, '')}/api/hotspots?bbox=${w},${s},${e},${n}&days=${days}`;
      const r = await fetch(url);
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const text = await r.text();
      rows = parseCSV(text).map(normRow).filter(Boolean);
      source = r.headers.get('x-jamra-source') || 'NASA FIRMS API (VIIRS NOAA-20 NRT)';
      when = r.headers.get('x-jamra-fetched') || new Date().toISOString();
    } catch (err) {
      stamp.textContent = `Live API unavailable (${err.message}). Showing the latest saved NASA data instead.`;
      rows = [];
      source = '';
    }
  }
  if (!source) {
    if (!live) { stamp.textContent = 'Live data unavailable right now. Please try again later.'; renderTable([]); return []; }
    const since = new Date(Date.parse(live.through_date + 'T00:00:00Z') - (days - 1) * 864e5).toISOString().slice(0, 10);
    rows = live.points.filter((p) => p[2] >= since).map((p) => ({
      latitude: p[0], longitude: p[1], acq_date: p[2], acq_time: p[3], frp: p[4], confidence: p[5], satellite: p[6],
    })).map(normRow).filter(Boolean);
    source = live.source;
    when = live.fetched_utc;
  }
  rows = rows.filter((r) => keep(r.latitude, r.longitude));
  lastRows = rows;
  const t = new Date(when);
  stamp.innerHTML = '';
  stamp.append(`${fmtInt(rows.length)} hotspots in the last ${days} day${days > 1 ? 's' : ''}. Fetched from ${source} at ${t.toISOString().slice(11, 16)} UTC, ${t.toISOString().slice(0, 10)}.`);
  renderTable(rows);
  $('#dl-live-csv').disabled = !rows.length;
  return rows;
}

function normRow(r) {
  const lat = +r.latitude, lon = +r.longitude;
  if (!Number.isFinite(lat) || !Number.isFinite(lon)) return null;
  const time = String(r.acq_time || '').padStart(4, '0');
  return {
    latitude: lat, longitude: lon, acq_date: r.acq_date, acq_time: time,
    datetime: `${r.acq_date} ${time.slice(0, 2)}:${time.slice(2)}`,
    satellite: r.satellite === 'N20' || r.satellite === '1' ? 'NOAA-20' : r.satellite === 'N21' ? 'NOAA-21' : r.satellite === 'N' ? 'S-NPP' : r.satellite,
    confidence: ({ n: 'nominal', h: 'high', l: 'low' })[r.confidence] || r.confidence,
    frp: r.frp === undefined ? null : +r.frp,
  };
}

export function renderTable(rows) {
  const table = $('#live-table');
  const thead = table.querySelector('thead'), tbody = table.querySelector('tbody');
  thead.innerHTML = '';
  const tr = el('tr');
  COLS.forEach(([k, label]) => {
    const th = el('th', { scope: 'col', tabindex: '0', 'aria-sort': k === sortKey ? (sortDir > 0 ? 'ascending' : 'descending') : 'none', text: label });
    const go = () => { sortDir = k === sortKey ? -sortDir : -1; sortKey = k; renderTable(lastRows); };
    th.addEventListener('click', go);
    th.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); go(); } });
    tr.append(th);
  });
  thead.append(tr);
  tbody.innerHTML = '';
  if (!rows.length) {
    tbody.append(el('tr', {}, el('td', { class: 'empty', colspan: COLS.length, text: 'Choose an area, then press "Get data from NASA FIRMS".' })));
    return;
  }
  const sorted = [...rows].sort((a, b) => (a[sortKey] > b[sortKey] ? 1 : a[sortKey] < b[sortKey] ? -1 : 0) * sortDir);
  for (const r of sorted.slice(0, 2000)) {
    tbody.append(el('tr', {}, ...COLS.map(([k]) => el('td', { text: k === 'frp' ? fmt(r.frp, 1) : k === 'latitude' || k === 'longitude' ? r[k].toFixed(4) : String(r[k] ?? '') }))));
  }
}

export function downloadLiveCSV(areaLabel) {
  if (!lastRows.length) return;
  const header = ['acq_date', 'acq_time', 'satellite', 'confidence', 'frp', 'latitude', 'longitude'];
  const note = `# Source: NASA FIRMS (VIIRS active fire). Area: ${areaLabel}. Unit: hotspots (satellite fire pixels), not fires.\n`;
  downloadBlob(`jamra_live_hotspots_${new Date().toISOString().slice(0, 10)}.csv`, note + toCSV(lastRows, header));
}
