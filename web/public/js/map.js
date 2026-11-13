// Map: MapLibre GL (loaded lazily), area outline, live hotspots, polygon/circle drawing.
// Written with the help of an SI coding assistant (Claude Code).
import { circleRing, haversineKm, ringBBox } from './util.js';
import { BASE } from './data.js';

// Own minimal styles on OpenFreeMap vector tiles (OpenMapTiles schema).
const TILES = 'https://tiles.openfreemap.org/planet';
const GLYPHS = 'https://tiles.openfreemap.org/fonts/{fontstack}/{range}.pbf';
const EN = ['coalesce', ['get', 'name:en'], ['get', 'name_en']]; // English-only labels
export function navyStyle() {
  return {
    version: 8, glyphs: GLYPHS,
    sources: { omt: { type: 'vector', url: TILES, attribution: '© OpenStreetMap contributors · OpenMapTiles · OpenFreeMap' } },
    layers: [
      { id: 'land', type: 'background', paint: { 'background-color': '#1B3580' } },
      { id: 'water', type: 'fill', source: 'omt', 'source-layer': 'water', paint: { 'fill-color': '#091640' } },
      { id: 'park', type: 'fill', source: 'omt', 'source-layer': 'park', paint: { 'fill-color': '#173276', 'fill-opacity': 0.5 } },
      { id: 'admin-region', type: 'line', source: 'omt', 'source-layer': 'boundary', minzoom: 5,
        filter: ['all', ['==', ['get', 'admin_level'], 4], ['!=', ['get', 'maritime'], 1]],
        paint: { 'line-color': '#4C5F8F', 'line-width': 0.5, 'line-dasharray': [3, 2] } },
      { id: 'admin-country', type: 'line', source: 'omt', 'source-layer': 'boundary',
        filter: ['all', ['<=', ['get', 'admin_level'], 2], ['!=', ['get', 'maritime'], 1]],
        paint: { 'line-color': '#7183AD', 'line-width': ['interpolate', ['linear'], ['zoom'], 2, 0.5, 8, 1.2] } },
      { id: 'roads', type: 'line', source: 'omt', 'source-layer': 'transportation', minzoom: 7,
        filter: ['in', ['get', 'class'], ['literal', ['motorway', 'trunk', 'primary']]],
        paint: { 'line-color': '#2A4592', 'line-width': 0.8 } },
      { id: 'place-city', type: 'symbol', source: 'omt', 'source-layer': 'place', minzoom: 4.5,
        filter: ['in', ['get', 'class'], ['literal', ['city', 'town']]],
        layout: { 'text-field': EN, 'text-font': ['Noto Sans Regular'], 'text-size': ['interpolate', ['linear'], ['zoom'], 5, 10, 10, 13] },
        paint: { 'text-color': '#E8EEF8', 'text-halo-color': '#0B1D51', 'text-halo-width': 1.4 } },
      { id: 'place-country', type: 'symbol', source: 'omt', 'source-layer': 'place', maxzoom: 8,
        filter: ['==', ['get', 'class'], 'country'],
        layout: { 'text-field': EN, 'text-font': ['Noto Sans Bold'], 'text-size': ['interpolate', ['linear'], ['zoom'], 2, 10, 6, 14], 'text-transform': 'uppercase', 'text-letter-spacing': 0.06 },
        paint: { 'text-color': '#E8EEF8', 'text-halo-color': '#0B1D51', 'text-halo-width': 1.6 } },
    ],
  };
}
function globeStyle() {
  return {
    version: 8, projection: { type: 'globe' },
    sources: { omt: { type: 'vector', url: TILES, attribution: '© OpenStreetMap contributors · OpenFreeMap' } },
    layers: [
      { id: 'land', type: 'background', paint: { 'background-color': '#D6E4FB' } },
      { id: 'water', type: 'fill', source: 'omt', 'source-layer': 'water', paint: { 'fill-color': '#2B63E0' } },
      { id: 'admin-country', type: 'line', source: 'omt', 'source-layer': 'boundary',
        filter: ['all', ['<=', ['get', 'admin_level'], 2], ['!=', ['get', 'maritime'], 1]],
        paint: { 'line-color': '#7FA2E6', 'line-width': 0.6 } },
    ],
  };
}
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

export function initMap(container, { onFallback } = {}) {
  if (ready) return ready;
  ready = (async () => {
    loadCSS(BASE + 'vendor/maplibre-gl.css');
    await loadScript(BASE + 'vendor/maplibre-gl.js');
    const ml = window.maplibregl;
    map = new ml.Map({
      container, style: navyStyle(), center: [14, 38.5], zoom: 3.3, attributionControl: { compact: true },
      cooperativeGestures: matchMedia('(pointer: coarse)').matches,
    });
    map.addControl(new ml.NavigationControl({ showCompass: false }), 'top-right');
    await new Promise((res, rej) => {
      const t = /guide=1/.test(location.search) ? 0 : setTimeout(() => rej(new Error('map timeout')), 20000);
      map.on('load', () => { clearTimeout(t); res(); });
      map.on('error', (e) => { if (!map.loaded()) console.warn('map error', e?.error?.message); });
    });
    map.addSource('area', { type: 'geojson', data: empty });
    map.addLayer({ id: 'area-fill', type: 'fill', source: 'area', paint: { 'fill-color': '#F5C518', 'fill-opacity': 0.08 } });
    map.addLayer({ id: 'area-line', type: 'line', source: 'area', paint: { 'line-color': '#F5C518', 'line-width': 2.5 } });
    map.addSource('live', { type: 'geojson', data: empty });
    map.addLayer({
      id: 'live-pts', type: 'circle', source: 'live',
      paint: {
        'circle-radius': ['interpolate', ['linear'], ['zoom'], 3, 2.5, 8, 5, 12, 8],
        'circle-color': '#FF6A2B', 'circle-opacity': ['case', ['<', ['get', 'age'], 1], 1, 0.7],
        'circle-stroke-color': '#FFFFFF', 'circle-stroke-width': 0.6,
      },
    });
    map.addSource('draw', { type: 'geojson', data: empty });
    map.addLayer({ id: 'draw-line', type: 'line', source: 'draw', paint: { 'line-color': '#F5C518', 'line-width': 2, 'line-dasharray': [2, 1] } });
    map.addLayer({ id: 'draw-pts', type: 'circle', source: 'draw', filter: ['==', '$type', 'Point'], paint: { 'circle-radius': 5, 'circle-color': '#F5C518' } });
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
  const m = await ready; if (!m) return;
  m.getSource('area').setData(ring ? { type: 'Feature', geometry: { type: 'Polygon', coordinates: [ring] } } : empty);
  if (ring) {
    const [w, s, e, n] = ringBBox(ring);
    m.fitBounds([[w, s], [e, n]], { padding: 40, maxZoom: 9, duration: 600 });
  }
}

export async function showLive(points) {
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


// ---------------------------------------------------------------- Home hero globe
/**
 * Slowly turning globe centred on the Mediterranean, with real FIRMS hotspots (ember dots)
 * and the preset fire areas (hover: name and alert level, click: open the Calendar).
 */
export async function initGlobe(container, { points = [], areas = [], onPick, onReady } = {}) {
  loadCSS(BASE + 'vendor/maplibre-gl.css');
  await loadScript(BASE + 'vendor/maplibre-gl.js');
  const ml = window.maplibregl;
  const g = new ml.Map({
    container, style: globeStyle(), center: [18, 34], zoom: 1.6, attributionControl: { compact: true },
    interactive: true, dragRotate: false, pitchWithRotate: false, scrollZoom: false, touchZoomRotate: false, doubleClickZoom: false,
    renderWorldCopies: false,
  });
  await new Promise((res, rej) => { g.on('load', res); g.on('error', (e) => { if (!g.loaded()) rej(e.error || new Error('globe')); }); });
  g.addSource('hot', { type: 'geojson', data: { type: 'FeatureCollection', features: points.map((p) => ({ type: 'Feature', geometry: { type: 'Point', coordinates: [p[1], p[0]] }, properties: {} })) } });
  g.addLayer({ id: 'hot', type: 'circle', source: 'hot', paint: { 'circle-radius': 2.2, 'circle-color': '#FF6A2B', 'circle-stroke-color': '#7C2D12', 'circle-stroke-width': 0.4 } });
  g.addSource('areas', { type: 'geojson', data: { type: 'FeatureCollection', features: areas.map((a) => ({ type: 'Feature', geometry: { type: 'Point', coordinates: a.center }, properties: { id: a.id, label: a.label, level: a.level } })) } });
  g.addLayer({ id: 'areas', type: 'circle', source: 'areas', paint: { 'circle-radius': 7, 'circle-color': 'rgba(245,197,24,0.15)', 'circle-stroke-color': '#F5C518', 'circle-stroke-width': 1.6 } });
  const tip = document.createElement('div');
  tip.className = 'globe-tip'; tip.hidden = true;
  container.parentElement.append(tip);
  g.on('mousemove', 'areas', (e) => {
    const f = e.features[0].properties;
    g.getCanvas().style.cursor = 'pointer';
    tip.innerHTML = `<b>${f.label}</b><br>Alert level: ${f.level}`;
    tip.style.left = `${e.point.x + 12}px`; tip.style.top = `${e.point.y + 12}px`; tip.hidden = false;
  });
  g.on('mouseleave', 'areas', () => { g.getCanvas().style.cursor = ''; tip.hidden = true; });
  g.on('click', 'areas', (e) => onPick && onPick(e.features[0].properties.id));
  // gentle back-and-forth turn around the Mediterranean; stops on interaction or when off screen
  let t0 = performance.now(), running = true, visible = true;
  const stop = () => { running = false; };
  ['mousedown', 'touchstart', 'wheel'].forEach((ev) => container.addEventListener(ev, stop, { passive: true }));
  new IntersectionObserver(([en]) => { visible = en.isIntersecting; }).observe(container);
  let last = 0;
  const step = (t) => {
    if (running && visible && t - last > 40) { last = t; g.jumpTo({ center: [18 + 16 * Math.sin((t - t0) / 9000), 34] }); }
    if (running) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
  onReady && onReady();
  return g;
}

export function webglOK() {
  try { const c = document.createElement('canvas'); return !!(c.getContext('webgl2') || c.getContext('webgl')); } catch { return false; }
}
