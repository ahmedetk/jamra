// Map: MapLibre GL (loaded lazily), area outline, live hotspots, polygon/circle drawing.
// Written with the help of an SI coding assistant (Claude Code).
import { circleRing, haversineKm, ringBBox } from './util.js';
import { BASE } from './data.js';

const TILES = 'https://tiles.openfreemap.org/planet';
const GLYPHS = 'https://tiles.openfreemap.org/fonts/{fontstack}/{range}.pbf';
const EN = ['coalesce', ['get', 'name:en'], ['get', 'name_en']]; // English-only labels
// One light cartographic style at every zoom, globe view included (Design v4): warm light-grey land,
// soft blue water, thin borders, charcoal labels. OpenFreeMap / OpenMapTiles vector tiles.
const LAND = '#F3F1EB', WATER = '#B7CADB';
export function earthStyle({ labels = true, flat = false } = {}) {
  const layers = [
    { id: 'land', type: 'background', paint: { 'background-color': LAND } },
    { id: 'water', type: 'fill', source: 'omt', 'source-layer': 'water', paint: { 'fill-color': WATER } },
    { id: 'park', type: 'fill', source: 'omt', 'source-layer': 'park', minzoom: 7, paint: { 'fill-color': '#E3E8D8', 'fill-opacity': 0.7 } },
    { id: 'roads', type: 'line', source: 'omt', 'source-layer': 'transportation', minzoom: 7,
      filter: ['in', ['get', 'class'], ['literal', ['motorway', 'trunk', 'primary', 'secondary']]],
      paint: { 'line-color': '#FFFFFF', 'line-width': ['interpolate', ['linear'], ['zoom'], 7, 0.7, 12, 2.4] } },
    { id: 'admin-region', type: 'line', source: 'omt', 'source-layer': 'boundary', minzoom: 6,
      filter: ['all', ['==', ['get', 'admin_level'], 4], ['!=', ['get', 'maritime'], 1]],
      paint: { 'line-color': '#C9C5BC', 'line-width': 0.6, 'line-dasharray': [3, 2] } },
    { id: 'admin-country', type: 'line', source: 'omt', 'source-layer': 'boundary',
      filter: ['all', ['<=', ['get', 'admin_level'], 2], ['!=', ['get', 'maritime'], 1]],
      paint: { 'line-color': '#B8B3A9', 'line-width': ['interpolate', ['linear'], ['zoom'], 1, 0.5, 8, 1.1] } },
  ];
  if (labels) {
    const text = () => ({ 'text-color': '#2B2B2B', 'text-halo-color': 'rgba(247,246,242,0.95)', 'text-halo-width': 1.3 });
    layers.push(
      { id: 'place-city', type: 'symbol', source: 'omt', 'source-layer': 'place', minzoom: 5.5,
        filter: ['in', ['get', 'class'], ['literal', ['city', 'town']]],
        layout: { 'text-field': EN, 'text-font': ['Noto Sans Regular'], 'text-size': ['interpolate', ['linear'], ['zoom'], 6, 11, 11, 14] }, paint: text() },
      { id: 'place-country', type: 'symbol', source: 'omt', 'source-layer': 'place', minzoom: 3, maxzoom: 8,
        filter: ['==', ['get', 'class'], 'country'],
        layout: { 'text-field': EN, 'text-font': ['Noto Sans Regular'], 'text-size': 12, 'text-letter-spacing': 0.06, 'text-transform': 'uppercase' }, paint: text() });
  }
  return {
    version: 8, glyphs: GLYPHS, projection: { type: flat ? 'mercator' : 'globe' },
    sky: { 'sky-color': '#E7E5DF', 'horizon-color': '#DCE4EA', 'fog-color': '#E7E5DF', 'sky-horizon-blend': 0.4, 'horizon-fog-blend': 0.5, 'fog-ground-blend': 0.9,
      'atmosphere-blend': ['interpolate', ['linear'], ['zoom'], 0, 0.35, 4, 0.15, 6, 0] },
    sources: { omt: { type: 'vector', url: TILES, attribution: '© OpenStreetMap contributors · OpenMapTiles · OpenFreeMap' } },
    layers,
  };
}
// hotspot dots: small and crisp; sized by FRP only when zoomed in
const HOT_RADIUS = ['interpolate', ['linear'], ['zoom'],
  1, 1.6, 4, 2.4, 7, ['+', 2.5, ['*', 0.12, ['sqrt', ['to-number', ['get', 'frp'], 1]]]],
  11, ['+', 3.5, ['*', 0.25, ['sqrt', ['to-number', ['get', 'frp'], 1]]]]];
const HOT_PAINT = { 'circle-radius': HOT_RADIUS, 'circle-color': '#F4511E', 'circle-stroke-color': 'rgba(247,246,242,0.9)', 'circle-stroke-width': 0.8 };
const SOFT_ORANGE = '#F4511E';   // selected area outline: vivid ember orange
const NEW_HOT = '#F4511E';       // hotspots from the last 24 h: full orange (older ones are lighter)

let map = null, ready = null, drawMode = null, drawPts = [], onDrawDone = null;
const empty = { type: 'FeatureCollection', features: [] };

function loadScript(src) {
  return new Promise((res, rej) => {
    const s = document.createElement('script');
    s.src = src; s.onload = res; s.onerror = () => rej(new Error('script ' + src));
    document.head.append(s);
  });
}
function loadCSS(href) {
  const l = document.createElement('link'); l.rel = 'stylesheet'; l.href = href; document.head.append(l);
}

let SOFT = false;
export function initMap(container, { onFallback, loader } = {}) {
  SOFT = softwareGL();
  if (ready) return ready;
  ready = (async () => {
    loadCSS(BASE + 'vendor/maplibre-gl.css');
    await loadScript(BASE + 'vendor/maplibre-gl.js');
    const ml = window.maplibregl;
    map = new ml.Map({
      container, style: earthStyle({ flat: SOFT }), center: [18, 30], zoom: 1.7, attributionControl: { compact: true }, maxZoom: 14, pixelRatio: SOFT ? 1 : undefined,
      cooperativeGestures: matchMedia('(pointer: coarse)').matches,
    });
    map.addControl(new ml.NavigationControl({ showCompass: false }), 'top-right');
    window.__jamraMap = map; // for our automated checks
    // globe view: the globe floats on the page; zoomed in: the canvas edges fade into the page (CSS mask)
    const view = () => container.classList.toggle('globe-view', !SOFT && map.getZoom() < 3.6);
    view(); map.on('zoom', view);
    // 1) the style (our own, inline) must load: only then layers can be added; a real failure here means no map
    await new Promise((res, rej) => {
      const t = setTimeout(() => rej(new Error('map style timeout')), 20000);
      const ok = () => { clearTimeout(t); res(); };
      if (map.isStyleLoaded()) ok(); else map.once('style.load', ok);
      map.on('error', (e) => { if (!map.isStyleLoaded()) console.warn('map error', e?.error?.message); });
    });
    // 2) show the globe when the Earth imagery is in (subtle loader until then), at most 8 s; tiles keep loading after
    await new Promise((res) => {
      const t0 = performance.now();
      const wait = () => ((map.isSourceLoaded('omt') && map.areTilesLoaded()) || performance.now() - t0 > 8000 ? (loader && loader.classList.add('done'), res()) : setTimeout(wait, 150));
      wait();
    });
    map.addSource('area', { type: 'geojson', data: empty });
    map.addLayer({ id: 'area-line', type: 'line', source: 'area', paint: { 'line-color': SOFT_ORANGE, 'line-width': 2.2 } });
    map.addSource('live', { type: 'geojson', data: empty });
    map.addLayer({
      id: 'live-pts', type: 'circle', source: 'live',
      paint: { ...HOT_PAINT, 'circle-color': ['case', ['<', ['get', 'age'], 1], NEW_HOT, '#F7A07A'], 'circle-opacity': 1 },
    });
    map.addSource('draw', { type: 'geojson', data: empty });
    map.addLayer({ id: 'draw-line', type: 'line', source: 'draw', paint: { 'line-color': SOFT_ORANGE, 'line-width': 1.6, 'line-dasharray': [2, 1] } });
    map.addLayer({ id: 'draw-pts', type: 'circle', source: 'draw', filter: ['==', '$type', 'Point'], paint: { 'circle-radius': 4, 'circle-color': SOFT_ORANGE } });
    const popup = new ml.Popup({ closeButton: false, closeOnClick: false });
    map.on('mouseenter', 'live-pts', (e) => {
      map.getCanvas().style.cursor = 'pointer';
      const p = e.features[0].properties;
      popup.setLngLat(e.lngLat).setHTML(`<b>${p.date} ${p.time} UTC</b><br>FRP ${p.frp} MW · confidence ${p.conf}<br>${p.sat}`).addTo(map);
    });
    map.on('mouseleave', 'live-pts', () => { map.getCanvas().style.cursor = ''; popup.remove(); });
    map.on('click', onMapClick);
    map.on('mousemove', onMapMove);
    map.on('dblclick', (e) => { if (drawMode === 'polygon') { e.preventDefault(); finishPolygon(); } });
    return map;
  })().catch((err) => {
    console.warn('Map unavailable:', err.message);
    container.innerHTML = '<div class="map-fallback">The map could not load (offline?). You can still pick fire areas, countries or enter coordinates.</div>';
    onFallback && onFallback(err);
    return null;
  });
  return ready;
}

export async function showArea(ring) {
  if (!ready) return;
  const m = await ready; if (!m) return;
  m.getSource('area').setData(ring ? { type: 'Feature', geometry: { type: 'Polygon', coordinates: [ring] } } : empty);
  if (ring) {
    const [w, s, e, n] = ringBBox(ring);
    const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
    m.fitBounds([[w, s], [e, n]], { padding: 40, maxZoom: 9, duration: reduce || SOFT ? 0 : 3000, easing: (t) => (t < 0.5 ? 4 * t * t * t : 1 - (-2 * t + 2) ** 3 / 2), essential: true });
  }
}

export async function flyToGlobe() {
  if (!ready) return;
  const m = await ready; if (!m) return;
  const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
  m.flyTo({ center: [18, 30], zoom: 1.7, duration: reduce ? 0 : 3000, easing: (t) => (t < 0.5 ? 4 * t * t * t : 1 - (-2 * t + 2) ** 3 / 2), essential: true });
}

export async function showLive(points) {
  if (!ready) return;
  const m = await ready; if (!m) return;
  const now = Date.now();
  m.getSource('live').setData({
    type: 'FeatureCollection',
    features: points.map((p) => ({
      type: 'Feature', geometry: { type: 'Point', coordinates: [p.lon, p.lat] },
      properties: { date: p.date, time: p.time, frp: p.frp, conf: p.conf, sat: p.sat,
        age: (now - Date.parse(`${p.date}T${p.time.slice(0, 2)}:${p.time.slice(2)}:00Z`)) / 864e5 },
    })),
  });
}

export async function startDraw(mode, done) {
  const m = await ready; if (!m) return false;
  drawMode = mode; drawPts = []; onDrawDone = done;
  m.doubleClickZoom.disable();
  m.getCanvas().style.cursor = 'crosshair';
  m.getSource('draw').setData(empty);
  return true;
}

export async function clearDraw() {
  const m = await ready; if (!m) return;
  drawMode = null; drawPts = [];
  m.getSource('draw').setData(empty);
  m.getCanvas().style.cursor = '';
  m.doubleClickZoom.enable();
}

function onMapClick(e) {
  if (!drawMode) return;
  const p = [e.lngLat.lng, e.lngLat.lat];
  if (drawMode === 'polygon') {
    if (drawPts.length >= 3) {
      const a = map.project(drawPts[0]), b = map.project(p);
      if (Math.hypot(a.x - b.x, a.y - b.y) < 12) { finishPolygon(); return; }
    }
    drawPts.push(p);
    renderDraw(drawPts);
  } else if (drawMode === 'circle') {
    if (!drawPts.length) { drawPts.push(p); renderDraw([p]); }
    else {
      const [lon, lat] = drawPts[0];
      const km = haversineKm(lat, lon, p[1], p[0]);
      const ring = circleRing(lat, lon, Math.max(km, 1));
      const label = `Circle ${km.toFixed(0)} km around ${lat.toFixed(2)}, ${lon.toFixed(2)}`;
      finish(ring, label);
    }
  }
}

function onMapMove(e) {
  if (!drawMode || !drawPts.length) return;
  const p = [e.lngLat.lng, e.lngLat.lat];
  if (drawMode === 'polygon') renderDraw([...drawPts, p]);
  else {
    const [lon, lat] = drawPts[0];
    renderDraw(circleRing(lat, lon, Math.max(haversineKm(lat, lon, p[1], p[0]), 0.5)), [drawPts[0]]);
  }
}

function renderDraw(coords, pts = drawMode === 'polygon' ? drawPts : []) {
  const feats = [];
  if (coords.length >= 2) feats.push({ type: 'Feature', geometry: { type: 'LineString', coordinates: coords } });
  pts.forEach((c) => feats.push({ type: 'Feature', geometry: { type: 'Point', coordinates: c } }));
  map.getSource('draw').setData({ type: 'FeatureCollection', features: feats });
}

function finishPolygon() {
  if (drawPts.length < 3) return;
  const ring = [...drawPts, drawPts[0]];
  finish(ring, `Drawn polygon (${drawPts.length} points)`);
}

function finish(ring, label) {
  const cb = onDrawDone;
  clearDraw();
  cb && cb(ring, label);
}


export function softwareGL() {
  try {
    const gl = document.createElement('canvas').getContext('webgl');
    const ext = gl && gl.getExtension('WEBGL_debug_renderer_info');
    return !!ext && /swiftshader|llvmpipe|software|basic render/i.test(gl.getParameter(ext.UNMASKED_RENDERER_WEBGL));
  } catch { return false; }
}

export function webglOK() {
  try { const c = document.createElement('canvas'); return !!(c.getContext('webgl2') || c.getContext('webgl')); } catch { return false; }
}
