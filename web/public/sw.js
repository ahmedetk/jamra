// Service worker: makes Jamra installable and usable offline (bad Wi-Fi demo).
// Pages, code and live files: network first (always fresh), cached copy if offline or slow (> 4 s).
// History data, map library and map tiles: cache first, refreshed in the background.
// Written with the help of an SI coding assistant (Claude Code).
const VERSION = 'jamra-v8';
const CORE = [
  './', 'index.html', 'calendar/', 'alerts/', 'live/', 'how-it-works/', 'validation/', 'limits/', 'credits/',
  'css/app.css', 'manifest.webmanifest', 'icons/icon.svg', 'icons/icon-192.png', 'icons/favicon-32.png',
  'fonts/inter-latin-400-normal.woff2', 'fonts/inter-latin-600-normal.woff2', 'fonts/plus-jakarta-sans-latin-700-normal.woff2', 'fonts/plus-jakarta-sans-latin-800-normal.woff2',
  'js/app.js', 'js/util.js', 'js/data.js', 'js/stats.js', 'js/colors.js', 'js/charts.js', 'js/calendar.js', 'js/map.js', 'js/live.js',
  'js/pages.js', 'js/summary.js', 'img/earth-blue-marble.webp',
  'data/meta.json', 'data/model_report.json', 'data/site.json',
  'vendor/maplibre-gl.js', 'vendor/maplibre-gl.css',
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
    const fallback = () => caches.match(key).then((hit) => { if (!done && hit) { done = true; resolve(hit); } });
    const timer = setTimeout(fallback, 4000);
    fetch(req).then((r) => {
      clearTimeout(timer);
      if (r.ok) { const copy = r.clone(); caches.open(VERSION).then((c) => c.put(key, copy)); }
      if (!done) { done = true; resolve(r); }
    }).catch(() => {
      clearTimeout(timer);
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
