// Service worker: makes Jamra installable and usable offline (bad Wi-Fi demo).
// Pages and live files: network first (always fresh), cached copy only when offline. Code files carry the build id
// in their URL (?v=), so a page and its code always come from the same build.
// History data, map library and map tiles: cache first, refreshed in the background.
// Written with the help of an AI coding assistant (Claude Code by Anthropic).
const BID = '202611140536';   // build id, written by scripts/build_pages.py on every build
const VERSION = 'jamra-' + BID;
// code files carry the build id (?v=), exactly as the pages request them, so pages and code always match
const CODE = ['css/app.css', 'js/app.js', 'js/util.js', 'js/data.js', 'js/stats.js', 'js/colors.js', 'js/charts.js', 'js/calendar.js',
  'js/map.js', 'js/live.js', 'js/summary.js', 'js/pages.js', 'js/globe3d.js'].map((u) => `${u}?v=${BID}`);
const CORE = [
  './', 'index.html', 'calendar/', 'alerts/', 'live/', 'validation/', 'about/',
  'manifest.webmanifest', 'icons/icon-192.png', 'icons/favicon-32.png',
  'fonts/inter-latin-400-normal.woff2', 'fonts/inter-latin-600-normal.woff2', 'fonts/inter-latin-700-normal.woff2', 'fonts/inter-latin-500-normal.woff2', 'fonts/playfair-display-latin-700-normal.woff2', 'icons/wordmark-dark.png',
  'img/earth-light.webp', 'data/meta.json', 'data/model_report.json', 'data/site.json',
  'vendor/maplibre-gl.js', 'vendor/maplibre-gl.css', ...CODE,
];

self.addEventListener('install', (e) => {
  const base = new URL('./', self.location).href;
  e.waitUntil(caches.open(VERSION).then((c) => c.addAll(CORE.map((u) => base + u))).then(() => self.skipWaiting()));
});
self.addEventListener('activate', (e) => {
  e.waitUntil(caches.keys().then((ks) => Promise.all(ks.filter((k) => k !== VERSION).map((k) => caches.delete(k)))).then(() => self.clients.claim()));
});

function stripQuery(req) { const u = new URL(req.url); u.search = ''; return new Request(u.toString()); }

function networkFirst(req, key) {
  return new Promise((resolve) => {
    let done = false;
    fetch(req, { cache: 'no-cache' }).then((r) => {
      if (r.ok) { const copy = r.clone(); caches.open(VERSION).then((c) => c.put(key, copy)); }
      if (!done) { done = true; resolve(r); }
    }).catch(() => {
      caches.match(key).then((hit) => { if (!done) { done = true; resolve(hit || Response.error()); } });
    });
  });
}

function cacheFirst(req) {
  return caches.match(req).then((hit) => {
    const net = fetch(req).then((r) => {
      if (r.ok || r.type === 'opaque') { const copy = r.clone(); caches.open(VERSION).then((c) => c.put(req, copy)); }
      return r;
    }).catch(() => hit);
    return hit || net;
  });
}

self.addEventListener('fetch', (e) => {
  if (e.request.method !== 'GET') return;
  const url = new URL(e.request.url);
  const sameOrigin = url.origin === location.origin;
  if (url.hostname.endsWith('openfreemap.org')) { e.respondWith(cacheFirst(e.request)); return; }
  if (!sameOrigin) return;
  const stable = url.pathname.includes('/data/areas/') || url.pathname.endsWith('/data/cells.json') || url.pathname.includes('/vendor/') || url.pathname.includes('/fonts/') || url.pathname.includes('/img/');
  if (stable) { e.respondWith(cacheFirst(e.request)); return; }
  // pages (with their query strings) are cached by path, so any shared link works offline
  const key = e.request.mode === 'navigate' || url.pathname.includes('/data/live/') ? stripQuery(e.request) : e.request;
  e.respondWith(networkFirst(e.request, key));
});
