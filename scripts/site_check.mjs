// Automated site checks (Edge + puppeteer-core): JavaScript errors, horizontal scroll, overlapping chart and
// calendar labels, the summary renderer, and the four downloads (CSV, PNG, Summary PNG, Summary PDF).
// Needs: npm i puppeteer-core.  Usage: node scripts/site_check.mjs [base_url]   (default http://localhost:8765/)
// Exit code 1 if anything fails. Written with the help of an AI coding assistant (Claude Code by Anthropic).
import puppeteer from 'puppeteer-core';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

const BASE = process.argv[2] || 'http://localhost:8765/';
const EDGE = 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe';
const wait = (ms) => new Promise((r) => setTimeout(r, ms));
const PAGES = [['home', ''], ['calendar-evia', 'calendar/?area=evia&from=2003&to=2025&month=2007-08&mode=abs&detail=1'],
  ['calendar-greece', 'calendar/?area=greece&from=2003&to=2025&month=2007-08&mode=anomaly&detail=1'], ['alerts', 'alerts/'],
  ['live', 'live/?area=greece'], ['validation', 'validation/'], ['about', 'about/']];
let failed = 0;
const fail = (msg) => { failed++; console.log('  FAIL', msg); };

const browser = await puppeteer.launch({ executablePath: EDGE, headless: 'new', args: ['--enable-webgl', '--use-angle=swiftshader-webgl', '--enable-unsafe-swiftshader'] });

async function open(url, w, h, mobile) {
  const p = await browser.newPage();
  const errors = [];
  p.on('pageerror', (e) => errors.push('pageerror: ' + e.message));
  p.on('console', (m) => { if (m.type() === 'error' && !/favicon|net::ERR|Failed to load resource/.test(m.text())) errors.push('console: ' + m.text()); });
  await p.setViewport({ width: w, height: h, deviceScaleFactor: mobile ? 2 : 1, isMobile: mobile, hasTouch: mobile });
  await p.goto(BASE + url, { waitUntil: 'networkidle2', timeout: 90000 }).catch(() => {});
  await wait(7000);
  return { p, errors };
}

// overlapping text: svg <text> on the same row (x-axis labels, month headers) must not overlap
const overlapScript = () => {
  const out = [];
  document.querySelectorAll('#cal svg, .chart svg, .season svg').forEach((s) => {
    const rows = {};
    s.querySelectorAll(':scope > text').forEach((t) => { const r = t.getBoundingClientRect(); if (r.width) (rows[Math.round(r.top / 4)] ||= []).push([r, t.textContent]); });
    Object.values(rows).forEach((row) => {
      row.sort((a, b) => a[0].left - b[0].left);
      for (let i = 1; i < row.length; i++) if (row[i][0].left < row[i - 1][0].right - 1) out.push(`${row[i - 1][1]} / ${row[i][1]}`);
    });
  });
  return out;
};

for (const [w, h, mobile, tag] of [[1440, 900, false, 'desktop 1440'], [390, 844, true, 'phone 390']]) {
  console.log(`\n== ${tag}`);
  for (const [name, url] of PAGES) {
    const { p, errors } = await open(url, w, h, mobile);
    const r = await p.evaluate(() => ({ sw: document.documentElement.scrollWidth, iw: innerWidth }));
    const ov = await p.evaluate(overlapScript);
    console.log(`${name.padEnd(16)} js-errors ${errors.length}  h-scroll ${r.sw > r.iw ? 'YES' : 'no'}  overlapping-labels ${ov.length}`);
    errors.forEach((e) => fail(`${name}: ${e}`));
    if (r.sw > r.iw) fail(`${name}: page is ${r.sw}px wide in a ${r.iw}px viewport`);
    ov.slice(0, 3).forEach((o) => fail(`${name}: overlapping labels ${o}`));
    if (name.startsWith('calendar') && !mobile) {
      // summary renderer + the four downloads
      const t = await p.evaluate(async () => { try { return await window.__jamraSummaryTest(); } catch (e) { return 'ERROR ' + e.message; } });
      if (!Array.isArray(t) || !(t[2] > 1000)) fail(`${name}: summary test ${JSON.stringify(t)}`); else console.log(`  summary test ok ${t[0]}x${t[1]}`);
      const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'jamra-dl-'));
      const cdp = await p.target().createCDPSession();
      await cdp.send('Browser.setDownloadBehavior', { behavior: 'allow', downloadPath: dir });
      for (const id of ['#dl-cal-csv', '#dl-cal-png', '#dl-summary-png', '#dl-summary-pdf']) {
        const before = new Set(fs.readdirSync(dir));
        await p.click(id);
        let got = null;
        for (let k = 0; k < 40 && !got; k++) { await wait(250); got = fs.readdirSync(dir).find((f) => !before.has(f) && !f.endsWith('.crdownload')); }
        const size = got ? fs.statSync(path.join(dir, got)).size : 0;
        console.log(`  download ${id.padEnd(16)} ${got ? `${got} (${size} bytes)` : 'NONE'}`);
        if (!got || size < 200) fail(`${name}: download ${id} did not produce a file`);
      }
    }
    await p.close();
  }
}
// ---- feature checks (desktop)
console.log('\n== features');
{
  const { p } = await open('calendar/', 1440, 900, false);
  const f = await p.evaluate(async () => {
    const r = {};
    r.toYear = document.querySelector('#to-year').value;
    r.palettes = [...document.querySelectorAll('#palette option')].map((o) => o.value).join(',');
    r.kpis = document.querySelectorAll('#kpi-grid .kpi').length;
    r.kpiTitles = [...document.querySelectorAll('#kpi-grid .k')].map((k) => k.textContent).join(' | ');
    r.season = document.querySelectorAll('#season svg circle').length;
    const total = () => document.querySelectorAll('#kpi-grid .kpi')[4]?.querySelector('.v')?.textContent;
    r.totalOn = total();
    document.querySelector('#static-filter').click(); await new Promise((x) => setTimeout(x, 800));
    r.totalOff = total();
    document.querySelector('#static-filter').click(); await new Promise((x) => setTimeout(x, 400));
    document.querySelector('[data-res=week]').click(); await new Promise((x) => setTimeout(x, 1200));
    r.weekCells = document.querySelectorAll('#cal .cell').length;
    document.querySelector('[data-res=month]').click();
    document.querySelector('[data-hero=harm]').click(); await new Promise((x) => setTimeout(x, 600));
    r.validationLabel = /Validation: harmonized MODIS vs VIIRS, 2012–2025/.test(document.querySelector('#yearly').textContent);
    return r;
  });
  console.log(JSON.stringify(f, null, 1));
  if (f.toYear !== '2026') fail('default To year is ' + f.toYear);
  if (!/ember/.test(f.palettes) || !/viridis/.test(f.palettes) || !/cividis/.test(f.palettes) || !/ylorrd/.test(f.palettes)) fail('palette options ' + f.palettes);
  if (f.kpis < 4) fail('KPI cards ' + f.kpis);
  if (!(f.season > 5)) fail('season chart has no dots');
  if (f.totalOn === f.totalOff) fail('gas-flare filter did not change the total');
  if (!(f.weekCells > 500)) fail('weeks view cells ' + f.weekCells);
  if (!f.validationLabel) fail('validation label missing on the yearly chart');
  await p.close();
  const o = await open('calendar/?bbox=-100,30,-99,31', 1440, 900, false);
  const out = await o.p.evaluate(() => ({ cls: document.body.classList.contains('outside-coverage'), msg: document.querySelector('.outside')?.textContent || '', calVisible: !!document.querySelector('#calendar')?.offsetParent }));
  console.log('outside area:', JSON.stringify(out));
  if (!out.cls || !/Harmonized history covers PT, ES, GR, TR, CY, LB, JO, PS\. Outside these, live data only/.test(out.msg) || out.calVisible) fail('outside-coverage message / hidden calendar');
  await o.p.close();
}
await browser.close();
console.log(failed ? `\n${failed} problem(s)` : '\nAll site checks passed.');
process.exit(failed ? 1 : 0);
