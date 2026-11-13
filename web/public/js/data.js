// Data loading and custom-area harmonization.
// Written with the help of an SI coding assistant (Claude Code).
import { pointInRing, ringBBox } from './util.js';

// Site root (works under /jamra/ on GitHub Pages and on localhost): js/ sits one level below it.
export const BASE = new URL('../', import.meta.url).href;
const cache = new Map();
export async function getJSON(url, { fresh = false } = {}) {
  if (!fresh && cache.has(url)) return cache.get(url);
  const full = /^https?:/.test(url) ? url : BASE + url;
  const p = fetch(full + (fresh ? `?t=${Date.now()}` : ''), { cache: fresh ? 'no-store' : 'default' })
    .then((r) => { if (!r.ok) throw new Error(`${url}: HTTP ${r.status}`); return r.json(); });
  if (!fresh) cache.set(url, p);
  p.catch(() => cache.delete(url));
  return p;
}

export const monthLabel = (meta, i) => {
  const [y0, m0] = meta.start.split('-').map(Number);
  const t = (y0 * 12 + m0 - 1) + i;
  return `${Math.floor(t / 12)}-${String((t % 12) + 1).padStart(2, '0')}`;
};
export const monthIndex = (meta, y, m) => {
  const [y0, m0] = meta.start.split('-').map(Number);
  return (y * 12 + m - 1) - (y0 * 12 + m0 - 1);
};

export async function loadArea(id) {
  return getJSON(`data/areas/${id}.json`);
}

/** Build an area object (same shape as data/areas/*.json) for a custom polygon. */
export async function customArea(ring, label, meta, report) {
  const grid = await getJSON('data/cells.json');
  const deg = grid.cell_deg;
  const n = meta.n_months;
  const flagged = new Set(grid.flagged);
  const z = () => new Array(n).fill(0);
  const S = { A: z(), N: z(), J: z() }, St = { A: z(), N: z(), J: z() };
  const [w, s, e, nn] = ringBBox(ring);
  const countryHits = {};
  let nCells = 0, nStatic = 0;
  const idByName = Object.fromEntries(meta.areas.filter((a) => a.kind === 'country').map((a) => [a.country, a.id]));
  for (const [cid, c] of Object.entries(grid.cells)) {
    const [ix, iy] = cid.split('_').map(Number);
    const lon = (ix + 0.5) * deg - 180, lat = (iy + 0.5) * deg - 90;
    if (lon < w - deg || lon > e + deg || lat < s - deg || lat > nn + deg) continue;
    if (!pointInRing(lon, lat, ring)) continue;
    const isStatic = flagged.has(cid);
    nCells++; if (isStatic) nStatic++;
    const target = isStatic ? St : S;
    for (const k of ['A', 'N', 'J']) {
      const arr = c[k];
      if (!arr) continue;
      for (let i = 0; i < arr.length; i += 2) if (arr[i] < n) target[k][arr[i]] += arr[i + 1];
    }
    const cc = idByName[c.c] || c.c;
    countryHits[cc] = (countryHits[cc] || 0) + 1;
  }
  const switchIdx = monthIndex(meta, ...meta.snpp_switch.split('-').map(Number));
  const j0 = monthIndex(meta, 2018, 5);
  const outN = new Set(report.outages.filter((o) => o.sensor === 'N').map((o) => o.month));
  const outA = new Set(report.outages.filter((o) => o.sensor === 'A').map((o) => o.month));
  const calYears = new Set(report.calibration.years);
  const calIdx = [];
  for (let i = switchIdx; i < n; i++) {
    const lab = monthLabel(meta, i);
    if (calYears.has(+lab.slice(0, 4)) && !outN.has(lab) && !outA.has(lab)) calIdx.push(i);
  }
  const Vc = calIdx.reduce((a, i) => a + S.N[i], 0);
  const Mc = calIdx.reduce((a, i) => a + S.A[i], 0);
  // parent factor: mix of the countries the area covers, weighted by MODIS overlap counts
  const total = Object.values(countryHits).reduce((a, b) => a + b, 0);
  let kParent = meta.k_global, kJN = 1;
  if (total) {
    kParent = 0; kJN = 0;
    for (const [cid, h] of Object.entries(countryHits)) {
      kParent += (h / total) * (meta.k_by_country[cid] ?? meta.k_global);
      kJN += (h / total) * (meta.k_jn_by_country[cid] ?? 1);
    }
  }
  const lam = meta.lambda;
  const local = meta.area_method !== 'baseline';
  const lamA = meta.lambda_area ?? lam;
  const k = local ? (Vc + lamA * kParent) / (Mc + lamA) : kParent;
  const own = local ? Mc / (Mc + lamA) : 0;
  // year-to-year relative standard error of the ratio
  const byYear = {};
  for (const i of calIdx) {
    const y = monthLabel(meta, i).slice(0, 4);
    byYear[y] = byYear[y] || [0, 0];
    byYear[y][0] += S.N[i]; byYear[y][1] += S.A[i];
  }
  const rs = Object.values(byYear).filter(([, m]) => m > 0).map(([v, m]) => v / m);
  let seRel = null;
  if (rs.length >= 3) {
    const mu = rs.reduce((a, b) => a + b, 0) / rs.length;
    const sd = Math.sqrt(rs.reduce((a, r) => a + (r - mu) ** 2, 0) / (rs.length - 1));
    seRel = mu > 0 ? sd / Math.sqrt(rs.length) / mu : null;
  }
  // shrinkage also shrinks the uncertainty contribution of the area's own ratio
  // uncertainty = typical small-region error on the held-out test years
  const rel = meta.uncertainty_small ?? meta.uncertainty_monthly;
  const harm = [], src = [], lo = [], hi = [], harmStatic = [];
  for (let i = 0; i < n; i++) {
    const lab = monthLabel(meta, i);
    if (i < switchIdx) {
      const h = S.A[i] * k;
      harm.push(round1(h)); src.push('M'); lo.push(round1(h * (1 - rel))); hi.push(round1(h * (1 + rel)));
      harmStatic.push(round1(St.A[i] * k));
    } else if (outN.has(lab)) {
      if (i >= j0) { harm.push(round1(S.J[i] * kJN)); src.push('J'); harmStatic.push(round1(St.J[i] * kJN)); }
      else { harm.push(null); src.push('G'); harmStatic.push(null); }
      lo.push(null); hi.push(null);
    } else {
      harm.push(S.N[i]); src.push('N'); lo.push(null); hi.push(null); harmStatic.push(St.N[i]);
    }
  }
  return {
    id: 'custom', label, kind: 'custom', ring, start: meta.start,
    series: { A: S.A, N: S.N.map((v, i) => (i >= switchIdx ? v : null)), J: S.J.map((v, i) => (i >= j0 ? v : null)), T: null },
    harm, src, lo, hi, harm_static: harmStatic,
    factor: { k, k_country: kParent, own_weight: own, rel_se: seRel, V_overlap: Vc, M_overlap: Mc, rel, kJN },
    cells: nCells, static_cells: nStatic, daily: null,
  };
}

function round1(x) { return x === null ? null : Math.round(x * 10) / 10; }

/** Monthly values for the calendar, honouring the static-source filter switch. */
export function monthlyValues(area, staticFilter) {
  return area.harm.map((h, i) => {
    if (h === null) return null;
    if (staticFilter) return h;
    const s = area.harm_static?.[i];
    return s === null || s === undefined ? h : h + s;
  });
}
