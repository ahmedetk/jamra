// Colour ramps. Viridis/Cividis (matplotlib, CC0) and YlOrRd/RdBu (ColorBrewer).
// Written with the help of an SI coding assistant (Claude Code).
const RAMPS = {
  viridis: ['#440154', '#482878', '#3e4989', '#31688e', '#26828e', '#1f9e89', '#35b779', '#6ece58', '#b5de2b', '#fde725'],
  cividis: ['#00204c', '#00336f', '#39486b', '#575d6d', '#707173', '#8a8779', '#a69d75', '#c4b56c', '#e4cf5b', '#ffe945'],
  ylorrd: ['#ffffcc', '#ffeda0', '#fed976', '#feb24c', '#fd8d3c', '#fc4e2a', '#e31a1c', '#bd0026', '#800026'],
};
export const RAMP_NAMES = Object.keys(RAMPS);

function hex2rgb(h) { const n = parseInt(h.slice(1), 16); return [(n >> 16) & 255, (n >> 8) & 255, n & 255]; }
function rgb2hex([r, g, b]) { return '#' + [r, g, b].map((v) => Math.round(v).toString(16).padStart(2, '0')).join(''); }

export function ramp(name, t) {
  const stops = RAMPS[name] || RAMPS.viridis;
  const x = Math.min(Math.max(t, 0), 1) * (stops.length - 1);
  const i = Math.min(Math.floor(x), stops.length - 2), f = x - i;
  const a = hex2rgb(stops[i]), b = hex2rgb(stops[i + 1]);
  return rgb2hex(a.map((v, k) => v + (b[k] - v) * f));
}

export function rampCSS(name) {
  const stops = RAMPS[name] || RAMPS.viridis;
  return `linear-gradient(90deg, ${stops.join(', ')})`;
}

// Diverging, colourblind-safe 5-class RdBu for anomaly categories.
export const CAT_COLOR = {
  much_lower: '#2166ac', lower: '#92c5de', typical: '#f7f7f7', higher: '#f4a582', much_higher: '#b2182b',
};

export function textOn(hex) {
  const [r, g, b] = hex2rgb(hex);
  return (0.299 * r + 0.587 * g + 0.114 * b) > 150 ? '#14213d' : '#ffffff';
}

// log scale helper for skewed counts
export function logScale(maxV) {
  const m = Math.log1p(Math.max(maxV, 1));
  return (v) => (v === null || v === undefined ? null : Math.log1p(Math.max(v, 0)) / m);
}
