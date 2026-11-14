// Validation and Limits page sections (all numbers read from model_report.json).
// Written with the help of an AI coding assistant (Claude Code by Anthropic).
import { $, el, fmt, fmtInt, pct } from './util.js';

const NAME = { Turkey: 'Türkiye' };

function table(head, rows) {
  return el('table', { class: 'table' },
    el('thead', {}, el('tr', {}, ...head.map((h) => el('th', { scope: 'col', text: h })))),
    el('tbody', {}, ...rows.map((r) => el('tr', {}, ...r.map((c) => el('td', { text: String(c) }))))));
}

export function renderValidation(report, meta) {
  const v = report.validation;
  if (!v) return;
  const ch = report.chosen_model;
  const tc = v.test_countries;
  $('#split-text').append(
    el('h2', { class: 'h3', text: 'How we tested' }),
    el('p', { text: `We split the years. Development years (${v.dev_years[0]}–${v.dev_years[v.dev_years.length - 1]}, without 2021) were used to build the model and choose its settings. The final test years (${v.test_years.join(', ')}) were held out and never touched during development. Every result marked "test years" comes only from those held-out years.` }),
    el('p', { class: 'fine', text: `Model chosen on development years: ${ch} (${report.model_labels[ch]}). ${v.high_rule}` }));
  const k = $('#test-kpis');
  const kp = (h, val, d) => k.append(el('div', { class: 'kpi' }, el('div', { class: 'k', text: h }), el('div', { class: 'v', text: val }), el('div', { class: 'd', text: d })));
  kp('Test-year error, countries', `${pct(tc.M0.mdape)} → ${pct(tc[ch].mdape)}`, 'typical monthly error: raw MODIS → harmonized');
  kp('Test-year error, yearly totals', pct(tc[ch].annual.mdape), `typical error on a country's yearly total (raw MODIS: ${pct(tc.M0.annual.mdape)})`);
  const cc = v.confusion_countries.harmonized, cr = v.confusion_countries.raw_modis;
  kp('High-activity months found', `${cc.hits} of ${cc.hits + cc.misses}`, `hit rate ${pct(cc.hit_rate)} (raw MODIS: ${cr.hits} of ${cr.hits + cr.misses})`);
  const sp = v.small_regions.presets, sg = v.small_regions.grid_1deg;
  const meth = v.decision.adopt_local_factor ? 'local' : 'baseline';
  kp('Small regions error', `${pct(sg[meth].mdape)}`, `typical monthly error in ${fmtInt(sg.regions)} 1° areas; ${pct(sp[meth].mdape)} in the ${sp.regions} fire areas (raw MODIS: ${pct(sg.raw_modis.mdape)})`);

  const conf = (c) => [fmtInt(c.hits), fmtInt(c.misses), fmtInt(c.false_alarms), pct(c.hit_rate), pct(c.false_alarm_ratio)];
  $('#conf-country').append(table(['', 'Detected (hits)', 'Missed', 'False alarms', 'Hit rate', 'Share of flags wrong'],
    [['Raw MODIS', ...conf(cr)], [`Harmonized (${ch})`, ...conf(cc)]]),
    el('p', { class: 'fine', text: `Country-months in ${v.test_years.join(', ')} that real VIIRS called "Higher" or "Much higher" than usual, compared with what each record said.` }));

  const row = (label, s, m) => [label, fmt(s[m].mae, 1), pct(s[m].mdape), pct(s[m].bias, 1), `${s[m].confusion.hits}/${s[m].confusion.hits + s[m].confusion.misses}`, fmtInt(s[m].confusion.false_alarms)];
  $('#small-table').append(table(['Areas · method', 'Error (MAE)', 'Typical % error', 'Bias', 'High months found', 'False alarms'], [
    row(`Fire areas (${sp.regions}) · country factor`, sp, 'baseline'), row(`Fire areas (${sp.regions}) · local factor`, sp, 'local'),
    row(`1° areas (${sg.regions}) · country factor`, sg, 'baseline'), row(`1° areas (${sg.regions}) · local factor`, sg, 'local'),
  ]));
  $('#decision-text').textContent = `${v.decision.text} Rule: ${v.decision.rule}`;

  const label = Object.fromEntries(meta.areas.map((a) => [a.id, a.label]));
  const pr = Object.entries(sp.per_region).map(([id, r]) => [label[id] || id, fmtInt(r.actual_total), pct(r.baseline.mdape), pct(r.local.mdape), fmt(r.baseline.mae, 1), fmt(r.local.mae, 1)]);
  $('#preset-table').append(table(['Fire area', 'VIIRS hotspots (test years)', '% error · country factor', '% error · local factor', 'MAE · country', 'MAE · local'], pr),
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
