// Validation (key numbers) and Limits sections, also used on About (all numbers read from model_report.json).
// Written with the help of an AI coding assistant (Claude Code by Anthropic).
import { $, el, fmt, fmtInt, pct } from './util.js';

const NAME = { Turkey: 'Türkiye' };

function table(head, rows) {
  return el('table', { class: 'table' },
    el('thead', {}, el('tr', {}, ...head.map((h) => el('th', { scope: 'col', text: h })))),
    el('tbody', {}, ...rows.map((r) => el('tr', {}, ...r.map((c) => el('td', { text: String(c) }))))));
}

export function renderKeyNumbers(report, box, { full = true, split = null } = {}) {
  const v = report.validation;
  if (!v || !box) return;
  const ch = report.chosen_model, tc = v.test_countries;
  const cc = v.confusion_countries.harmonized, cr = v.confusion_countries.raw_modis;
  const sp = v.small_regions.presets, sg = v.small_regions.grid_1deg;
  const meth = v.decision.adopt_local_factor ? 'local' : 'baseline';
  const ty = `${v.test_years[0]}–${v.test_years[v.test_years.length - 1]}`;
  if (split) {
    split.innerHTML = '';
    split.append(el('h2', { class: 'h3', text: 'How we tested' }),
      el('p', { text: `We built the model on development years (${v.dev_years[0]}–${v.dev_years[v.dev_years.length - 1]}, without 2021) and kept ${v.test_years.join(', ')} hidden as a final test. Every number below comes only from those held-out test years.` }));
  }
  box.innerHTML = '';
  const kp = (h, val, d) => box.append(el('div', { class: 'kpi' }, el('div', { class: 'k', text: h }), el('div', { class: 'v', text: val }), el('div', { class: 'd', text: d })));
  kp('Monthly error, countries', `${pct(tc.M0.mdape)} → ${pct(tc[ch].mdape)}`, `raw MODIS → harmonized, test years ${ty}`);
  kp('Yearly totals error', pct(tc[ch].annual.mdape), `a country's yearly total (raw MODIS: ${pct(tc.M0.annual.mdape)})`);
  kp('High-activity months found', `${cc.hits} of ${cc.hits + cc.misses}`, `${cc.false_alarms} false alarms (raw MODIS found ${cr.hits})`);
  kp('Small regions error', `${pct(sg[meth].mdape)} / ${pct(sp[meth].mdape)}`, `${fmtInt(sg.regions)} 1° areas / the ${sp.regions} fire areas`);
  if (full) {
    kp('Local factor for small areas', v.decision.adopt_local_factor ? 'Adopted' : 'Not adopted', v.decision.adopt_local_factor ? 'each small area gets its own factor, pulled toward the country value' : 'small areas use the country factor');
    const ca = report.colour_agreement;
    kp('Calendar colors agree', `${fmt(ca.same_colour_pct, 0)}%`, `same anomaly color from harmonized MODIS as from real VIIRS (${fmtInt(ca.months)} country-months; raw MODIS ${fmt(ca.without_harmonization_pct, 0)}%)`);
  }
}

// Validation page: the detail tables (high-activity months, small regions, fire areas one by one)
export function renderValidationDetails(report, meta) {
  const v = report.validation;
  if (!v) return;
  const ch = report.chosen_model;
  const cc = v.confusion_countries.harmonized, cr = v.confusion_countries.raw_modis;
  const sp = v.small_regions.presets, sg = v.small_regions.grid_1deg;
  const put = (sel, ...nodes) => { const n = $(sel); if (n) { n.innerHTML = ''; n.append(...nodes); } };
  const conf = (c) => [fmtInt(c.hits), fmtInt(c.misses), fmtInt(c.false_alarms), pct(c.hit_rate), pct(c.false_alarm_ratio)];
  put('#conf-country', table(['', 'Detected (hits)', 'Missed', 'False alarms', 'Hit rate', 'Share of flags wrong'],
    [['Raw MODIS', ...conf(cr)], [`Harmonized (${ch})`, ...conf(cc)]]),
    el('p', { class: 'fine', text: `Country-months in ${v.test_years.join(', ')} that real VIIRS called "Higher" or "Much higher" than usual, compared with what each record said.` }));

  const row = (label, s, m) => [label, fmt(s[m].mae, 1), pct(s[m].mdape), pct(s[m].bias, 1), `${s[m].confusion.hits}/${s[m].confusion.hits + s[m].confusion.misses}`, fmtInt(s[m].confusion.false_alarms)];
  put('#small-table', table(['Areas · method', 'Error (MAE)', 'Typical % error', 'Bias', 'High months found', 'False alarms'], [
    row(`Fire areas (${sp.regions}) · country factor`, sp, 'baseline'), row(`Fire areas (${sp.regions}) · local factor`, sp, 'local'),
    row(`1° areas (${sg.regions}) · country factor`, sg, 'baseline'), row(`1° areas (${sg.regions}) · local factor`, sg, 'local'),
  ]));
  const dt = $('#decision-text'); if (dt) dt.textContent = `${v.decision.text} Rule: ${v.decision.rule}`;

  const label = Object.fromEntries(meta.areas.map((a) => [a.id, a.label]));
  const pr = Object.entries(sp.per_region).map(([id, r]) => [label[id] || id, fmtInt(r.actual_total), pct(r.baseline.mdape), pct(r.local.mdape), fmt(r.baseline.mae, 1), fmt(r.local.mae, 1)]);
  put('#preset-table', table(['Fire area', 'VIIRS hotspots (test years)', '% error · country factor', '% error · local factor', 'MAE · country', 'MAE · local'], pr),
    el('p', { class: 'fine', text: 'Small areas are where harmonization is hardest: few hotspots, so every month is noisy. Errors here are larger than for countries.' }));
}

export function renderLimits(report, meta) {
  const k = $('#unc-kpis');
  const u = report.uncertainty;
  const kp = (h, val, d) => k.append(el('div', { class: 'kpi' }, el('div', { class: 'k', text: h }), el('div', { class: 'v', text: val }), el('div', { class: 'd', text: d })));
  kp('Country, one month', `±${Math.round(u.monthly_rel * 100)}%`, 'typical error of an estimated (pre-2012) month, test years');
  kp('Country, one year', `±${Math.round(u.annual_rel * 100)}%`, 'typical error of an estimated yearly total');
  kp('Small area, one month', `±${Math.round(u.small_regions_rel * 100)}%`, 'fire areas and drawn areas');
  kp('NOAA-20 → S-NPP', `×${fmt(report.noaa20_to_snpp.global, 2)}`, 'factor for live data since 2 Nov 2026');
}

export { NAME };
