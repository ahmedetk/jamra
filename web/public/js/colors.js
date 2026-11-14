// Colour ramps. Viridis/Cividis (matplotlib, CC0) and YlOrRd/RdBu (ColorBrewer).
// Written with the help of an AI coding assistant (Claude Code by Anthropic).
const RAMPS = {
  ember: ['#F3F1EB', '#F5DCCD', '#F7C2A6', '#F7A07A', '#F67A4C', '#F4511E', '#C23A10', '#8A2A0B'],
  viridis: ['#440154', '#482878', '#3e4989', '#31688e', '#26828e', '#1f9e89', '#35b779', '#6ece58', '#b5de2b', '#fde725'],
  cividis: ['#00204c', '#00336f', '#39486b', '#575d6d', '#707173', '#8a8779', '#a69d75', '#c4b56c', '#e4cf5b', '#ffe945'],
  ylorrd: ['#ffffcc', '#ffeda0', '#fed976', '#feb24c', '#fd8d3c', '#fc4e2a', '#e31a1c', '#bd0026', '#800026'],
};
export const RAMP_NAMES = Object.keys(RAMPS);

function hex2rgb(h) { const n = parseInt(h.slice(1), 16); return [(n >> 16) & 255, (n >> 8) & 255, n & 255]; }
function rgb2hex([r, g, b]) { return '#' + [r, g, b].map((v) => Math.round(v).toString(16).padStart(2, '0')).join(''); }

export function ramp(name, t) {
  const stops = RAMPS[name] || RAMPS.ember;
  if (!Number.isFinite(t)) t = 0;          // NaN / undefined never crash the colour scale
  const x = Math.min(Math.max(t, 0), 1) * (stops.length - 1);
  const i = Math.min(Math.floor(x), stops.length - 2), f = x - i;
  const a = hex2rgb(stops[i]), b = hex2rgb(stops[i + 1]);
  return rgb2hex(a.map((v, k) => v + (b[k] - v) * f));
}

export function rampCSS(name) {
  const stops = RAMPS[name] || RAMPS.ember;
  return `linear-gradient(90deg, ${stops.join(', ')})`;
}

// Diverging slate blue <-> neutral grey <-> orange (colourblind-safe): lower / typical / higher. Text labels are always shown.
export const CAT_COLOR = {
  much_lower: '#4E77A6', lower: '#B7CADB', typical: '#E2DFD7', higher: '#F9A98A', much_higher: '#F4511E',
};

// pick dark or white text by real WCAG contrast
function lum(hex) {
  return hex2rgb(hex).map((v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; })
    .reduce((a, v, i) => a + v * [0.2126, 0.7152, 0.0722][i], 0);
}
export function textOn(hex) {
  const L = lum(hex), dark = (L + 0.05) / (lum('#2B2B2B') + 0.05), white = 1.05 / (L + 0.05);
  return dark >= white ? '#2B2B2B' : '#ffffff';
}

// log scale helper for skewed counts
export function logScale(maxV) {
  const m = Math.log1p(Math.max(Number.isFinite(maxV) ? maxV : 1, 1));
  return (v) => (v === null || v === undefined ? null : Math.log1p(Math.max(v, 0)) / m);
}
