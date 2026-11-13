// Live system in the browser: status badge, Alert Center, on-demand NASA FIRMS data.
// Written with the help of an SI coding assistant (Claude Code).
import { $, el, fmt, fmtInt, parseCSV, pointInRing, ringBBox, toCSV, downloadBlob } from './util.js';
import { getJSON } from './data.js';
import { warningLevel } from './stats.js';

export const LEVEL_LABEL = { normal: 'Normal', elevated: 'Elevated', high: 'High', extreme: 'Extreme', unknown: 'No data' };
const LEVEL_RANK = { extreme: 4, high: 3, elevated: 2, normal: 1, unknown: 0 };

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

export function renderBadge(status) {
  const b = $('#status-badge');
  const t = b.querySelector('.txt');
  b.classList.remove('live', 'delayed', 'down');
  if (!status || !status.last_success_utc) {
    b.classList.add('down'); t.textContent = 'Live data unavailable';
    b.title = 'Could not read the live status. The history still works.';
    return;
  }
  const h = (Date.now() - Date.parse(status.last_success_utc)) / 36e5;
  if (h <= 6) { b.classList.add('live'); t.textContent = `Live · updated ${ago(status.last_success_utc)}`; }
  else if (h <= 30) { b.classList.add('delayed'); t.textContent = `Delayed · last update ${ago(status.last_success_utc)}`; }
  else { b.classList.add('down'); t.textContent = `Offline · last update ${ago(status.last_success_utc)}`; }
  b.title = `Source: ${status.source || 'NASA FIRMS'}. Last check: ${status.last_attempt_utc || '?'}${status.message ? ' · ' + status.message : ''}`;
  b.onclick = () => document.getElementById('alerts').scrollIntoView();
}

export function renderAlerts(live, meta, onPick) {
  const box = $('#alert-list');
  box.innerHTML = '';
  if (!live || !live.areas) {
    box.append(el('p', { class: 'note', text: 'Live alerts are not available right now. The historical calendar still works.' }));
    return;
  }
  const label = Object.fromEntries(meta.areas.map((a) => [a.id, a.label]));
  const rows = Object.entries(live.areas).sort((a, b) => (LEVEL_RANK[b[1].level] - LEVEL_RANK[a[1].level]) || (b[1].percentile ?? 0) - (a[1].percentile ?? 0));
  const [y, m] = live.month.split('-');
  const monthName = new Date(Date.UTC(+y, +m - 1, 1)).toLocaleString('en-US', { month: 'long', timeZone: 'UTC' });
  for (const [id, a] of rows) {
    const card = el('button', { class: `alert ${a.level}`, type: 'button', style: 'text-align:left;cursor:pointer;font:inherit', onclick: () => onPick(id) },
      el('h3', {}, `${label[id] || id} `, el('span', { class: `lvl lvl-${a.level}`, text: LEVEL_LABEL[a.level] })),
      el('p', { text: a.level === 'unknown' ? 'Not enough history to compare.' :
        `${monthName} ${a.from_day ?? 1}–${a.day}: ${fmt(a.mtd, 0)} hotspots. Usual for these days: ${fmt(a.median, 0)} (middle half ${fmt(a.p25, 0)}–${fmt(a.p75, 0)}). Higher than ${Math.round(a.percentile)}% of past years.` }));
    if (id === 'palestine' || id === 'lebanon') card.append(el('p', { class: 'fine', text: 'Conflict-related heat sources possible.' }));
    box.append(card);
  }
}

/** Early-warning level for any area: live values for countries/presets, approximate for custom areas. */
export function areaWarning(area, live, meta, monthlyVals) {
  if (!live) return { level: 'unknown', note: 'live data unavailable' };
  if (area.kind !== 'custom' && live.areas && live.areas[area.id]) return { ...live.areas[area.id], approximate: false };
  if (!area.ring) return { level: 'unknown' };
  const [y, m] = live.month.split('-').map(Number);
  const day = live.day;
  const from = live.from_day ?? 1;
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

export async function fetchLive(area, days, site, live) {
  const ring = area.ring;
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
  rows = rows.filter((r) => pointInRing(r.longitude, r.latitude, ring));
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
    tbody.append(el('tr', {}, el('td', { class: 'empty', colspan: COLS.length, text: 'No hotspots yet. Choose an area and press "Fetch from NASA FIRMS".' })));
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
