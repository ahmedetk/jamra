// Map: MapLibre GL (loaded lazily), area outline, live hotspots, polygon/circle drawing.
// Written with the help of an SI coding assistant (Claude Code).
import { circleRing, haversineKm, ringBBox } from './util.js';
import { BASE } from './data.js';

const STYLE = 'https://tiles.openfreemap.org/styles/positron';
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
      container, style: STYLE, center: [14, 38.5], zoom: 3.3, attributionControl: { compact: true },
      cooperativeGestures: matchMedia('(pointer: coarse)').matches,
    });
    map.addControl(new ml.NavigationControl({ showCompass: false }), 'top-right');
    await new Promise((res, rej) => {
      const t = setTimeout(() => rej(new Error('map timeout')), 20000);
      map.on('load', () => { clearTimeout(t); res(); });
      map.on('error', (e) => { if (!map.loaded()) console.warn('map error', e?.error?.message); });
    });
    // English-only place labels (OpenMapTiles name:en / name_en)
    for (const layer of map.getStyle().layers) {
      if (layer.type === 'symbol' && map.getLayoutProperty(layer.id, 'text-field') !== undefined) {
        map.setLayoutProperty(layer.id, 'text-field', ['coalesce', ['get', 'name:en'], ['get', 'name_en'], '']);
      }
    }
    map.addSource('area', { type: 'geojson', data: empty });
    map.addLayer({ id: 'area-fill', type: 'fill', source: 'area', paint: { 'fill-color': '#14213d', 'fill-opacity': 0.08 } });
    map.addLayer({ id: 'area-line', type: 'line', source: 'area', paint: { 'line-color': '#14213d', 'line-width': 2 } });
    map.addSource('live', { type: 'geojson', data: empty });
    map.addLayer({
      id: 'live-pts', type: 'circle', source: 'live',
      paint: {
        'circle-radius': ['interpolate', ['linear'], ['zoom'], 3, 2.5, 8, 5, 12, 8],
        'circle-color': ['case', ['<', ['get', 'age'], 1], '#d9480f', '#f59f00'],
        'circle-stroke-color': '#7a1f00', 'circle-stroke-width': 0.6, 'circle-opacity': 0.9,
      },
    });
    map.addSource('draw', { type: 'geojson', data: empty });
    map.addLayer({ id: 'draw-line', type: 'line', source: 'draw', paint: { 'line-color': '#d9480f', 'line-width': 2, 'line-dasharray': [2, 1] } });
    map.addLayer({ id: 'draw-pts', type: 'circle', source: 'draw', filter: ['==', '$type', 'Point'], paint: { 'circle-radius': 5, 'circle-color': '#d9480f' } });
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
