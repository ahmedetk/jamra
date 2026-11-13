// Map: MapLibre GL (loaded lazily), area outline, live hotspots, polygon/circle drawing.
// Written with the help of an SI coding assistant (Claude Code).
import { circleRing, haversineKm, ringBBox } from './util.js';
import { BASE } from './data.js';

// Realistic Earth: NASA GIBS Blue Marble imagery (EPSG:3857, GoogleMapsCompatible_Level8, max zoom 8,
// verified from the GIBS GetCapabilities), a subtle atmosphere, and above zoom ~6.5 a crossfade to a
// clean, muted vector basemap (OpenFreeMap) so detail stays sharp.
const GIBS = 'https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/BlueMarble_ShadedRelief_Bathymetry/default/GoogleMapsCompatible_Level8/{z}/{y}/{x}.jpeg';
const TILES = 'https://tiles.openfreemap.org/planet';
const GLYPHS = 'https://tiles.openfreemap.org/fonts/{fontstack}/{range}.pbf';
const EN = ['coalesce', ['get', 'name:en'], ['get', 'name_en']]; // English-only labels
const FADE = (from, to) => ['interpolate', ['linear'], ['zoom'], 6.2, from, 7.4, to];
export function earthStyle({ labels = true } = {}) {
  const layers = [
    { id: 'space', type: 'background', paint: { 'background-color': '#05070D' } },
    { id: 'imagery', type: 'raster', source: 'gibs', paint: { 'raster-opacity': FADE(1, 0), 'raster-fade-duration': 300 } },
    { id: 'v-land', type: 'background', paint: { 'background-color': '#EEF0EA', 'background-opacity': FADE(0, 1) } },
    { id: 'v-water', type: 'fill', source: 'omt', 'source-layer': 'water', minzoom: 5.5, paint: { 'fill-color': '#B7CCDD', 'fill-opacity': FADE(0, 1) } },
    { id: 'v-park', type: 'fill', source: 'omt', 'source-layer': 'park', minzoom: 6, paint: { 'fill-color': '#DCE6D3', 'fill-opacity': FADE(0, 0.8) } },
    { id: 'v-roads', type: 'line', source: 'omt', 'source-layer': 'transportation', minzoom: 7,
      filter: ['in', ['get', 'class'], ['literal', ['motorway', 'trunk', 'primary', 'secondary']]],
      paint: { 'line-color': '#FFFFFF', 'line-width': ['interpolate', ['linear'], ['zoom'], 7, 0.6, 12, 2.4], 'line-opacity': FADE(0, 1) } },
    { id: 'admin-region', type: 'line', source: 'omt', 'source-layer': 'boundary', minzoom: 6,
      filter: ['all', ['==', ['get', 'admin_level'], 4], ['!=', ['get', 'maritime'], 1]],
      paint: { 'line-color': '#9AA3AE', 'line-width': 0.5, 'line-dasharray': [3, 2] } },
    { id: 'admin-country', type: 'line', source: 'omt', 'source-layer': 'boundary', minzoom: 3.5,
      filter: ['all', ['<=', ['get', 'admin_level'], 2], ['!=', ['get', 'maritime'], 1]],
      paint: { 'line-color': ['interpolate', ['linear'], ['zoom'], 6.2, 'rgba(255,255,255,0.45)', 7.4, '#8D96A3'], 'line-width': 0.8 } },
  ];
  if (labels) {
    const text = (size) => ({
      'text-color': ['interpolate', ['linear'], ['zoom'], 6.2, '#F8FAFC', 7.4, '#1F2937'],
      'text-halo-color': ['interpolate', ['linear'], ['zoom'], 6.2, 'rgba(15,23,42,0.85)', 7.4, 'rgba(255,255,255,0.95)'],
      'text-halo-width': 1.3,
    });
    layers.push(
      { id: 'place-city', type: 'symbol', source: 'omt', 'source-layer': 'place', minzoom: 5.5,
        filter: ['in', ['get', 'class'], ['literal', ['city', 'town']]],
        layout: { 'text-field': EN, 'text-font': ['Noto Sans Regular'], 'text-size': ['interpolate', ['linear'], ['zoom'], 6, 11, 11, 14] }, paint: text() },
      { id: 'place-country', type: 'symbol', source: 'omt', 'source-layer': 'place', minzoom: 3.8, maxzoom: 8,
        filter: ['==', ['get', 'class'], 'country'],
        layout: { 'text-field': EN, 'text-font': ['Noto Sans Bold'], 'text-size': 12, 'text-letter-spacing': 0.04 }, paint: text() });
  }
  return {
    version: 8, glyphs: GLYPHS, projection: { type: 'globe' },
    sky: {
      'sky-color': '#05070D', 'horizon-color': '#9CC3F2', 'fog-color': '#DCE9F7',
      'sky-horizon-blend': 0.5, 'horizon-fog-blend': 0.6, 'fog-ground-blend': 0.9,
      'atmosphere-blend': ['interpolate', ['linear'], ['zoom'], 0, 0.85, 5, 0.6, 7, 0],
    },
    sources: {
      gibs: { type: 'raster', tiles: [GIBS], tileSize: 256, maxzoom: 8, attribution: 'Imagery: NASA GIBS / Blue Marble' },
      omt: { type: 'vector', url: TILES, attribution: '© OpenStreetMap contributors · OpenMapTiles · OpenFreeMap' },
    },
    layers,
  };
}
// hotspot dots: small and crisp; sized by FRP only when zoomed in
const HOT_RADIUS = ['interpolate', ['linear'], ['zoom'],
  1, 1.6, 4, 2.4, 7, ['+', 2.5, ['*', 0.12, ['sqrt', ['to-number', ['get', 'frp'], 1]]]],
  11, ['+', 3.5, ['*', 0.25, ['sqrt', ['to-number', ['get', 'frp'], 1]]]]];
const HOT_PAINT = { 'circle-radius': HOT_RADIUS, 'circle-color': '#FF7A33', 'circle-stroke-color': 'rgba(120,40,10,0.35)', 'circle-stroke-width': 0.6 };
const SOFT_ORANGE = '#FDBA74';

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
      container, style: earthStyle(), center: [16, 38], zoom: 3.3, attributionControl: { compact: true },
      cooperativeGestures: matchMedia('(pointer: coarse)').matches,
    });
    map.addControl(new ml.NavigationControl({ showCompass: false }), 'top-right');
    await new Promise((res, rej) => {
      const t = /guide=1/.test(location.search) ? 0 : setTimeout(() => rej(new Error('map timeout')), 20000);
      map.on('load', () => { clearTimeout(t); res(); });
      map.on('error', (e) => { if (!map.loaded()) console.warn('map error', e?.error?.message); });
    });
    map.addSource('area', { type: 'geojson', data: empty });
    map.addLayer({ id: 'area-line', type: 'line', source: 'area', paint: { 'line-color': SOFT_ORANGE, 'line-width': 1.6 } });
    map.addSource('live', { type: 'geojson', data: empty });
    map.addLayer({
      id: 'live-pts', type: 'circle', source: 'live',
      paint: { ...HOT_PAINT, 'circle-opacity': ['case', ['<', ['get', 'age'], 1], 1, 0.75] },
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
    m.fitBounds([[w, s], [e, n]], { padding: 40, maxZoom: 9, duration: reduce ? 0 : 2200, easing: (t) => (t < 0.5 ? 4 * t * t * t : 1 - (-2 * t + 2) ** 3 / 2), essential: true });
  }
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
    container, style: earthStyle({ labels: false }), center: [10, 30], zoom: 1.95, attributionControl: { compact: true },
    dragRotate: false, pitchWithRotate: false, scrollZoom: false, touchZoomRotate: false, doubleClickZoom: false, keyboard: false,
  });
  window.__jamraGlobe = g; // for our automated checks
  await new Promise((res, rej) => { g.on('load', res); g.on('error', (e) => { if (!g.loaded()) rej(e.error || new Error('globe')); }); });
  g.addSource('hot', { type: 'geojson', data: { type: 'FeatureCollection', features: points.map((p) => ({ type: 'Feature', geometry: { type: 'Point', coordinates: [p[1], p[0]] }, properties: { frp: p[4] } })) } });
  g.addLayer({ id: 'hot', type: 'circle', source: 'hot', paint: HOT_PAINT });
  // invisible hit areas for the fire areas (hover: name and alert level; click: open the Calendar)
  g.addSource('areas', { type: 'geojson', data: { type: 'FeatureCollection', features: areas.map((a) => ({ type: 'Feature', geometry: { type: 'Point', coordinates: a.center }, properties: { id: a.id, label: a.label, level: a.level } })) } });
  g.addLayer({ id: 'areas', type: 'circle', source: 'areas', paint: { 'circle-radius': 9, 'circle-opacity': 0, 'circle-stroke-width': 0 } });
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

  // slow rotation: one turn per 120 s, easing in at the start and out when the user interacts
  const DEG_PER_MS = 360 / 120000;
  let speed = 0, target = 1, last = null, visible = true, lng = 10;
  const stop = () => { target = 0; };
  ['mousedown', 'touchstart', 'wheel', 'keydown'].forEach((ev) => container.addEventListener(ev, stop, { passive: true }));
  new IntersectionObserver(([en]) => { visible = en.isIntersecting; }).observe(container);
  const step = (t) => {
    if (last !== null && visible) {
      const dt = Math.min(64, t - last);
      speed += (target - speed) * Math.min(1, dt / 1200);     // smooth ease in / out
      if (speed > 0.002) { lng = (lng + DEG_PER_MS * speed * dt + 540) % 360 - 180; g.setCenter([lng, 30]); }
    }
    last = t;
    if (target > 0 || speed > 0.002) requestAnimationFrame(step);
  };
  const t1 = performance.now();
  const reveal = () => {
    if ((g.isSourceLoaded('gibs') && g.areTilesLoaded()) || performance.now() - t1 > 12000) {
      onReady && onReady();
      if (!matchMedia('(prefers-reduced-motion: reduce)').matches) requestAnimationFrame(step);
    } else setTimeout(reveal, 300);
  };
  reveal();
  return g;
}

export function webglOK() {
  try { const c = document.createElement('canvas'); return !!(c.getContext('webgl2') || c.getContext('webgl')); } catch { return false; }
}
