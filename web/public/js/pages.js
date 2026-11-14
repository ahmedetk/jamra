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
    const fr = report.frp_test;
    kp('FRP test', fr.validated ? 'Passed' : 'Not supported', `ratio variation: FRP ${fmt(fr.pooled_cv_frp_ratio, 2)} vs counts ${fmt(fr.pooled_cv_count_ratio, 2)}, so the calendar uses counts`);
    kp('NOAA-20 → S-NPP', `×${fmt(report.noaa20_to_snpp.global, 2)}`, `live data since S-NPP stopped (2 Nov 2026), measured on ${fmtInt(report.noaa20_to_snpp.months_used)} country-months`);
  }
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
