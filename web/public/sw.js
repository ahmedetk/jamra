// Service worker: makes Jamra installable and usable offline (bad Wi-Fi demo).
// App files and history data: cache first, refreshed in the background.
// Live files: network first, cached copy if offline.
// Written with the help of an SI coding assistant (Claude Code).
const VERSION = 'jamra-v1';
const CORE = [
  './', 'index.html', 'css/app.css', 'manifest.webmanifest', 'icons/icon.svg', 'icons/icon-192.png',
  'js/app.js', 'js/util.js', 'js/data.js', 'js/stats.js', 'js/colors.js', 'js/charts.js', 'js/calendar.js', 'js/map.js', 'js/live.js',
  'data/meta.json', 'data/model_report.json', 'data/site.json',
  'vendor/maplibre-gl.js', 'vendor/maplibre-gl.css',
];

self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(VERSION).then((c) => c.addAll(CORE)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', (e) => {
  e.waitUntil(caches.keys().then((ks) => Promise.all(ks.filter((k) => k !== VERSION).map((k) => caches.delete(k)))).then(() => self.clients.claim()));
});

self.addEventListener('fetch', (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== 'GET') return;
  const isLive = url.pathname.includes('/data/live/') || url.pathname.includes('/api/');
  const sameOrigin = url.origin === location.origin;
  const isTiles = url.hostname.endsWith('openfreemap.org');
  if (isLive) {
    e.respondWith(fetch(e.request).then((r) => { const copy = r.clone(); caches.open(VERSION).then((c) => c.put(stripQuery(e.request), copy)); return r; })
      .catch(() => caches.match(stripQuery(e.request))));
    return;
  }
  if (sameOrigin || isTiles) {
    e.respondWith(caches.match(e.request).then((hit) => {
      const net = fetch(e.request).then((r) => {
        if (r.ok && (sameOrigin || r.type === 'cors')) { const copy = r.clone(); caches.open(VERSION).then((c) => c.put(e.request, copy)); }
        return r;
      }).catch(() => hit);
      return hit || net;
    }));
  }
});

function stripQuery(req) { const u = new URL(req.url); u.search = ''; return new Request(u.toString()); }
