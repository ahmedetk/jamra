// Screenshots for the Arabic user guide, cropped to real page elements (Edge + puppeteer-core).
// Needs: npm i puppeteer-core (any folder; run with NODE_PATH or from that folder).
// Usage: node scripts/guide_shots.mjs [base_url] [out_dir]
// Defaults: the local preview server on port 8765, report/shots/. Written with the help of an AI coding assistant (Claude Code by Anthropic).
import puppeteer from 'puppeteer-core';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const BASE = process.argv[2] || 'http://localhost:8765/';
const OUT = process.argv[3] || path.join(ROOT, 'report', 'shots');
const EDGE = 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe';
const wait = (ms) => new Promise((r) => setTimeout(r, ms));

const browser = await puppeteer.launch({ executablePath: EDGE, headless: 'new', args: ['--no-first-run', '--enable-webgl', '--ignore-gpu-blocklist', '--use-angle=swiftshader-webgl', '--enable-unsafe-swiftshader'] });

async function open(url, { w = 1280, h = 900, dpr = 1, mobile = false, settle = 8000 } = {}) {
  const p = await browser.newPage();
  await p.setViewport({ width: w, height: h, deviceScaleFactor: dpr, isMobile: mobile, hasTouch: mobile });
  await p.goto(BASE + url, { waitUntil: 'networkidle2', timeout: 90000 }).catch(() => {});
  await wait(settle);
  return p;
}
// crop from the top of one element to the bottom of another (page coordinates)
async function crop(p, name, a, b = a, pad = 0) {
  const r = await p.evaluate((a, b) => {
    const A = document.querySelector(a), B = document.querySelector(b);
    if (!A || !B) return null;
    const ra = A.getBoundingClientRect(), rb = B.getBoundingClientRect();
    return { y: ra.top + scrollY, h: rb.bottom - ra.top, w: document.documentElement.clientWidth };
  }, a, b);
  if (!r) { console.log(name, 'missing', a, b); return; }
  await p.screenshot({ path: path.join(OUT, name + '.png'), clip: { x: 0, y: Math.max(0, r.y - pad), width: r.w, height: r.h + 2 * pad }, captureBeyondViewport: true });
  console.log(name, Math.round(r.h));
}

let p = await open('?guide=1');
await crop(p, 'g_home', '#hero', '#tools'); await p.close();
p = await open('calendar/?area=evia&from=2003&to=2025&month=2007-08&mode=abs&detail=1&guide=1', { settle: 11000 });
await crop(p, 'g_cal_top', '.page-head', '#area');
await crop(p, 'g_cal_chart', '#yearly');
await crop(p, 'g_cal_main', '#kpis', '.cal-card', 12);
await crop(p, 'g_cal_detail', '#detail', '#detail', 8); await p.close();
p = await open('calendar/?area=greece&from=2003&to=2025&hero=harm');
await crop(p, 'g_harm', '#yearly'); await p.close();
p = await open('calendar/?area=greece&from=2003&to=2025&month=2007-08&mode=anomaly');
await crop(p, 'g_anomaly', '.cal-card', '.cal-card', 8); await p.close();
p = await open('alerts/?guide=1');
await crop(p, 'g_alerts', '.page-head', '#alerts'); await p.close();
p = await open('live/?area=greece&guide=1', { settle: 11000 });
await crop(p, 'g_live', '.page-head', '#live'); await p.close();
p = await open('about/?guide=1');
await crop(p, 'g_about', '.page-head', '#about'); await p.close();
// phone views (390 px)
p = await open('', { w: 390, h: 844, dpr: 2, mobile: true });
await p.screenshot({ path: path.join(OUT, 'mobile_home.png') }); await p.close();
p = await open('calendar/?area=evia&from=2003&to=2025&month=2007-08&mode=abs&detail=1', { w: 390, h: 844, dpr: 2, mobile: true });
await p.evaluate(() => { document.documentElement.style.scrollBehavior = 'auto'; const d = document.querySelector('#detail'); d.scrollIntoView({ block: 'start' }); scrollBy(0, -90); });
await wait(800);
await p.screenshot({ path: path.join(OUT, 'mobile_detail.png') }); await p.close();
await browser.close();
