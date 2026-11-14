// Jamra live API proxy (Cloudflare Worker, free plan).
// Hides the FIRMS MAP_KEY, caches answers for 15 minutes and limits request size,
// so user queries stay far below the FIRMS limit of 5,000 transactions / 10 minutes.
// Written with the help of an AI coding assistant (Claude Code by Anthropic).

const FIRMS = 'https://firms.modaps.eosdis.nasa.gov/api/area/csv';
const SOURCES = new Set(['VIIRS_NOAA20_NRT', 'VIIRS_NOAA21_NRT', 'MODIS_NRT']);
const MAX_SPAN_DEG = 20;          // biggest box side allowed
const PER_IP_PER_MIN = 20;        // best-effort limit per isolate
const hits = new Map();

const cors = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, OPTIONS',
  'Access-Control-Expose-Headers': 'x-jamra-source, x-jamra-fetched, x-jamra-cache',
};

function json(obj, status = 200) {
  return new Response(JSON.stringify(obj), { status, headers: { 'content-type': 'application/json', ...cors } });
}

function limited(ip) {
  const now = Date.now(), win = 60000;
  const arr = (hits.get(ip) || []).filter((t) => now - t < win);
  arr.push(now);
  hits.set(ip, arr);
  if (hits.size > 5000) hits.clear();
  return arr.length > PER_IP_PER_MIN;
}

async function firms(key, source, bbox, days) {
  // FIRMS allows DAY_RANGE 1..5 per call; split longer requests.
  const parts = [];
  const today = new Date();
  let remaining = days, offset = 0;
  while (remaining > 0) {
    const span = Math.min(5, remaining);
    const start = new Date(today.getTime() - (offset + span - 1) * 864e5).toISOString().slice(0, 10);
    const url = offset === 0 ? `${FIRMS}/${key}/${source}/${bbox}/${span}` : `${FIRMS}/${key}/${source}/${bbox}/${span}/${start}`;
    let text = null, lastErr = null;
    for (let attempt = 0; attempt < 3 && text === null; attempt++) {
      try {
        const r = await fetch(url, { cf: { cacheTtl: 0 } });
        if (r.status >= 500) throw new Error(`FIRMS HTTP ${r.status}`);
        const t = await r.text();
        if (!r.ok || /^\s*(invalid|error|<)/i.test(t)) throw new Error(`FIRMS: ${t.slice(0, 80)}`);
        text = t;
      } catch (e) {
        lastErr = e;
        await new Promise((res) => setTimeout(res, 600 * 2 ** attempt));
      }
    }
    if (text === null) throw lastErr;
    parts.push(text.trim());
    remaining -= span; offset += span;
  }
  const [first, ...rest] = parts;
  return [first, ...rest.map((p) => p.split('\n').slice(1).join('\n'))].filter(Boolean).join('\n') + '\n';
}

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    if (request.method === 'OPTIONS') return new Response(null, { headers: cors });
    if (url.pathname === '/health') return json({ ok: true, service: 'jamra-proxy', time: new Date().toISOString(), key_configured: Boolean(env.FIRMS_MAP_KEY) });
    if (url.pathname !== '/api/hotspots') return json({ error: 'not found' }, 404);
    if (!env.FIRMS_MAP_KEY) return json({ error: 'FIRMS key not configured' }, 503);

    const ip = request.headers.get('cf-connecting-ip') || 'anon';
    if (limited(ip)) return json({ error: 'Too many requests, please wait a minute.' }, 429);

    const b = (url.searchParams.get('bbox') || '').split(',').map(Number);
    if (b.length !== 4 || !b.every(Number.isFinite)) return json({ error: 'bbox must be west,south,east,north' }, 400);
    let [w, s, e, n] = b.map((v) => Math.round(v * 100) / 100);
    if (w >= e || s >= n || w < -180 || e > 180 || s < -90 || n > 90) return json({ error: 'invalid bbox' }, 400);
    if (e - w > MAX_SPAN_DEG || n - s > MAX_SPAN_DEG) return json({ error: `box too large (max ${MAX_SPAN_DEG} degrees per side)` }, 400);
    const days = Math.min(7, Math.max(1, parseInt(url.searchParams.get('days') || '1', 10) || 1));
    const source = SOURCES.has(url.searchParams.get('source')) ? url.searchParams.get('source') : 'VIIRS_NOAA20_NRT';

    const bucket = Math.floor(Date.now() / (15 * 60000));
    const cacheKey = new Request(`https://jamra-cache/${source}/${w},${s},${e},${n}/${days}/${bucket}`);
    const cache = caches.default;
    const hit = await cache.match(cacheKey);
    if (hit) { const r = new Response(hit.body, hit); r.headers.set('x-jamra-cache', 'hit'); return r; }

    try {
      const csv = await firms(env.FIRMS_MAP_KEY, source, `${w},${s},${e},${n}`, days);
      const resp = new Response(csv, {
        headers: {
          'content-type': 'text/csv; charset=utf-8', 'cache-control': 'public, max-age=900',
          'x-jamra-source': `NASA FIRMS API (${source})`, 'x-jamra-fetched': new Date().toISOString(), 'x-jamra-cache': 'miss', ...cors,
        },
      });
      ctx.waitUntil(cache.put(cacheKey, resp.clone()));
      return resp;
    } catch (err) {
      return json({ error: 'NASA FIRMS is not answering right now. The site shows the latest saved data instead.', detail: String(err.message || err).replace(env.FIRMS_MAP_KEY, '***') }, 502);
    }
  },
};
