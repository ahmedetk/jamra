// Anomaly rules. Mirrors pipeline/jamra/anomaly.py so the site and the pipeline agree.
// Written with the help of an SI coding assistant (Claude Code).

export function quantile(values, q) {
  const xs = values.filter((v) => v !== null && v !== undefined).sort((a, b) => a - b);
  if (!xs.length) return null;
  const pos = (xs.length - 1) * q, lo = Math.floor(pos), hi = Math.ceil(pos);
  return xs[lo] + (xs[hi] - xs[lo]) * (pos - lo);
}

export function percentileRank(value, others) {
  const xs = others.filter((v) => v !== null && v !== undefined);
  if (!xs.length || value === null || value === undefined) return null;
  let below = 0, equal = 0;
  for (const v of xs) { if (v < value) below++; else if (v === value) equal++; }
  return (100 * (below + 0.5 * equal)) / xs.length;
}

export function baseline(others) {
  const xs = others.filter((v) => v !== null && v !== undefined);
  if (!xs.length) return null;
  return { median: quantile(xs, 0.5), p25: quantile(xs, 0.25), p75: quantile(xs, 0.75), n: xs.length };
}

export function passesGuard(value, med, cfg) {
  return Math.abs(value - med) >= Math.max(cfg.small_count_min_abs, cfg.small_count_min_rel * med);
}

export const CAT_ORDER = ['much_lower', 'lower', 'typical', 'higher', 'much_higher'];
export const CAT_LABEL = { much_lower: 'Much lower', lower: 'Lower', typical: 'Typical', higher: 'Higher', much_higher: 'Much higher' };

export function category(value, others, cfg) {
  if (value === null || value === undefined) return null;
  const b = baseline(others);
  if (!b) return null;
  const pr = percentileRank(value, others);
  const c = cfg.categories;
  const guard = passesGuard(value, b.median, cfg);
  if (pr >= c.much_higher && guard) return 'much_higher';
  if (pr >= c.higher && guard) return 'higher';
  if (pr <= c.much_lower && guard) return 'much_lower';
  if (pr <= c.lower && guard) return 'lower';
  return 'typical';
}

export function warningLevel(mtd, othersMtd, cfg) {
  const b = baseline(othersMtd);
  if (!b) return { level: 'unknown' };
  const pr = percentileRank(mtd, othersMtd);
  const lv = cfg.warning_levels;
  const guard = passesGuard(mtd, b.median, cfg);
  let level = 'normal';
  if (guard && mtd > b.median) {
    if (pr >= lv.extreme) level = 'extreme';
    else if (pr >= lv.high) level = 'high';
    else if (pr >= lv.elevated) level = 'elevated';
  }
  return { level, percentile: pr, ...b };
}

export function seasonStart(monthly, share = 0.1, minTotal = 20) {
  const vals = monthly.map((v) => v || 0);
  const total = vals.reduce((a, b) => a + b, 0);
  if (total < minTotal) return null;
  let acc = 0;
  for (let i = 0; i < 12; i++) { acc += vals[i]; if (acc >= share * total) return i + 1; }
  return null;
}

export function theilSen(xs, ys) {
  const s = [];
  for (let i = 0; i < xs.length; i++) for (let j = i + 1; j < xs.length; j++) if (xs[j] !== xs[i]) s.push((ys[j] - ys[i]) / (xs[j] - xs[i]));
  return s.length ? quantile(s, 0.5) : null;
}

export function mannKendall(ys) {
  const n = ys.length;
  if (n < 4) return { S: 0, z: 0, p: 1 };
  let S = 0;
  for (let i = 0; i < n - 1; i++) for (let j = i + 1; j < n; j++) S += Math.sign(ys[j] - ys[i]);
  const ties = {};
  ys.forEach((y) => { ties[y] = (ties[y] || 0) + 1; });
  let tsum = 0;
  Object.values(ties).forEach((t) => { tsum += t * (t - 1) * (2 * t + 5); });
  const v = (n * (n - 1) * (2 * n + 5) - tsum) / 18;
  if (v <= 0) return { S, z: 0, p: 1 };
  const z = S > 0 ? (S - 1) / Math.sqrt(v) : S < 0 ? (S + 1) / Math.sqrt(v) : 0;
  return { S, z, p: erfc(Math.abs(z) / Math.SQRT2) };
}

function erfc(x) { // Numerical Recipes approximation
  const t = 1 / (1 + 0.5 * Math.abs(x));
  const r = t * Math.exp(-x * x - 1.26551223 + t * (1.00002368 + t * (0.37409196 + t * (0.09678418 + t * (-0.18628806 + t * (0.27886807 + t * (-1.13520398 + t * (1.48851587 + t * (-0.82215223 + t * 0.17087277)))))))));
  return x >= 0 ? r : 2 - r;
}
