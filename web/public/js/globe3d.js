// Home hero: a half globe in the colours of our light map (three.js), rising from the bottom right.
// One equirectangular texture drawn from Natural Earth (warm light-grey land, soft blue water, thin borders)
// and small vivid orange dots for real NASA FIRMS hotspots (last 7 days). Drag (mouse or touch) to turn it,
// with inertia; slow auto-rotation when idle, paused on interaction and resumed gently after ~5 s.
// Respects prefers-reduced-motion (no auto-rotation, no inertia).
// Written with the help of an SI coding assistant (Claude Code).
import * as THREE from '../vendor/three.module.min.js';
import { BASE } from './data.js';

const DEG = Math.PI / 180;

// lon/lat -> point on the unit sphere, matching three's SphereGeometry UV layout
function toXYZ(lon, lat, r = 1) {
  const phi = (lon + 180) * DEG, theta = (90 - lat) * DEG;
  return [-r * Math.cos(phi) * Math.sin(theta), r * Math.cos(theta), r * Math.sin(phi) * Math.sin(theta)];
}

export async function initEarth(canvas, { points = [], hiRes = false, onReady } = {}) {
  const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true, powerPreference: 'low-power' });
  renderer.setPixelRatio(Math.min(devicePixelRatio || 1, 2));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(24, 1, 0.1, 100);
  camera.position.set(0, 0, 4.85);

  // tilt (latitude) on the outer group, spin (longitude) on the inner one
  const tilt = new THREE.Group(), spin = new THREE.Group();
  tilt.add(spin); scene.add(tilt);
  const LAT0 = 8, LON0 = 16;   // the visible upper half shows the Mediterranean
  tilt.rotation.x = LAT0 * DEG;
  spin.rotation.y = -(LON0 + 90) * DEG;

  // Earth
  const tex = await new THREE.TextureLoader().loadAsync(BASE + `img/earth-light-${hiRes ? 4096 : 2048}.webp`);
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.anisotropy = Math.min(8, renderer.capabilities.getMaxAnisotropy());
  const earth = new THREE.Mesh(
    new THREE.SphereGeometry(1, 128, 96),
    new THREE.MeshStandardMaterial({ map: tex, roughness: 1, metalness: 0 }),
  );
  spin.add(earth);

  // light: soft sun from the upper left, plus sky light so the night side is never pitch black
  scene.add(new THREE.HemisphereLight(0xffffff, 0xd8d4cc, 2.1));
  const sun = new THREE.DirectionalLight(0xffffff, 0.55);
  sun.position.set(-2, 2.5, 3);
  scene.add(sun);

  // atmosphere: a thin, soft rim (fresnel), drawn behind the Earth's edge
  const atmo = new THREE.Mesh(
    new THREE.SphereGeometry(1.005, 96, 64),
    new THREE.ShaderMaterial({
      side: THREE.BackSide, transparent: true, depthWrite: false,
      uniforms: { c: { value: new THREE.Color(0xc4bfb5) } },
      vertexShader: 'varying vec3 vN; varying vec3 vP; void main(){ vN = normalize(normalMatrix * normal); vec4 p = modelViewMatrix * vec4(position,1.0); vP = p.xyz; gl_Position = projectionMatrix * p; }',
      fragmentShader: 'uniform vec3 c; void main(){ gl_FragColor = vec4(c, 0.9); }',   // a thin crisp outline around the globe
    }),
  );
  scene.add(atmo);
  // a very light haze on the day side edge
  const haze = new THREE.Mesh(
    new THREE.SphereGeometry(1.004, 96, 64),
    new THREE.ShaderMaterial({
      transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
      uniforms: { c: { value: new THREE.Color(0xffffff) } },
      vertexShader: 'varying vec3 vN; varying vec3 vP; void main(){ vN = normalize(normalMatrix * normal); vec4 p = modelViewMatrix * vec4(position,1.0); vP = p.xyz; gl_Position = projectionMatrix * p; }',
      fragmentShader: 'uniform vec3 c; varying vec3 vN; varying vec3 vP; void main(){ float f = 1.0 - max(dot(normalize(-vP), vN), 0.0); gl_FragColor = vec4(c, pow(f, 3.0) * 0.12); }',
    }),
  );
  spin.add(haze);

  // hotspots: small, crisp orange dots (one per detection), slightly above the surface
  if (points.length) {
    const pos = new Float32Array(points.length * 3);
    points.forEach((p, i) => { const [x, y, z] = toXYZ(p[1], p[0], 1.003); pos[i * 3] = x; pos[i * 3 + 1] = y; pos[i * 3 + 2] = z; });
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    const dot = document.createElement('canvas'); dot.width = dot.height = 32;
    const cx = dot.getContext('2d'); cx.fillStyle = '#F4511E'; cx.beginPath(); cx.arc(16, 16, 13, 0, Math.PI * 2); cx.fill();
    const sprite = new THREE.CanvasTexture(dot); sprite.colorSpace = THREE.SRGBColorSpace;
    const dots = new THREE.Points(g, new THREE.PointsMaterial({ size: 4.2 * Math.min(devicePixelRatio || 1, 2), sizeAttenuation: false, map: sprite, transparent: true, alphaTest: 0.4, depthWrite: false }));
    spin.add(dots);
  }

  // size
  const resize = () => {
    const r = canvas.getBoundingClientRect();
    if (!r.width) return;
    renderer.setSize(r.width, r.height, false);
    camera.aspect = r.width / r.height;
    camera.updateProjectionMatrix();
  };
  resize();
  new ResizeObserver(resize).observe(canvas);

  // interaction: drag to turn (with inertia), auto-rotation when idle
  const AUTO = (2 * Math.PI) / 120;        // one turn per 120 s
  let vx = 0, vy = 0, dragging = false, lastX = 0, lastY = 0, lastT = 0, idleSince = performance.now() - 6000, auto = reduce ? 0 : 1;
  const k = () => 2.6 / Math.max(260, canvas.clientWidth);   // radians per pixel
  canvas.addEventListener('pointerdown', (e) => {
    dragging = true; lastX = e.clientX; lastY = e.clientY; lastT = performance.now(); vx = vy = 0;
    canvas.setPointerCapture(e.pointerId);
  });
  canvas.addEventListener('pointermove', (e) => {
    if (!dragging) return;
    const now = performance.now(), dt = Math.max(1, now - lastT);
    const dx = (e.clientX - lastX) * k(), dy = (e.clientY - lastY) * k();
    spin.rotation.y += dx; tilt.rotation.x = Math.max(-0.5, Math.min(0.9, tilt.rotation.x + dy));
    vx = (dx / dt) * 16; vy = (dy / dt) * 16;
    lastX = e.clientX; lastY = e.clientY; lastT = now;
  });
  const end = () => { dragging = false; idleSince = performance.now(); if (reduce) vx = vy = 0; };
  canvas.addEventListener('pointerup', end);
  canvas.addEventListener('pointercancel', end);
  canvas.addEventListener('keydown', (e) => {
    if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') { spin.rotation.y += (e.key === 'ArrowLeft' ? -1 : 1) * 0.15; idleSince = performance.now(); e.preventDefault(); }
  });
  canvas.tabIndex = 0;

  // render only while visible
  let visible = true, last = performance.now(), first = true;
  new IntersectionObserver(([en]) => { visible = en.isIntersecting; if (visible) { last = performance.now(); requestAnimationFrame(frame); } }).observe(canvas);
  function frame(t) {
    if (!visible) return;
    const dt = Math.min(0.05, (t - last) / 1000); last = t;
    if (!dragging) {
      // inertia
      spin.rotation.y += vx; tilt.rotation.x = Math.max(-0.5, Math.min(0.9, tilt.rotation.x + vy));
      vx *= 0.94; vy *= 0.94;
      if (Math.abs(vx) < 1e-5) vx = 0; if (Math.abs(vy) < 1e-5) vy = 0;
      // auto-rotation eases back in about 5 s after the last interaction
      if (!reduce) {
        const target = performance.now() - idleSince > 5000 ? 1 : 0;
        auto += (target - auto) * Math.min(1, dt * 0.9);
        spin.rotation.y += AUTO * auto * dt;
        // drift the tilt back toward the Mediterranean view
        if (target) tilt.rotation.x += (LAT0 * DEG - tilt.rotation.x) * Math.min(1, dt * 0.25);
      }
    } else auto = 0;
    renderer.render(scene, camera);
    if (first) { first = false; onReady && onReady(); }
    requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);
  window.__jamraEarth = { renderer, spin, tilt }; // for our automated checks
  return { renderer };
}
