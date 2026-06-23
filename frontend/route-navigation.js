/* ═══════════════════════════════════════════════════════
   LUMINALIFE ROUTE NAVIGATION ENGINE
   v1.0 — Premium Medical Donor Journey
   ═══════════════════════════════════════════════════════ */

'use strict';

/* ── URL PARAMS / DATA INJECTION ─────────────────────── */
const params = new URLSearchParams(window.location.search);
const HOSPITAL_DATA = {
  name:      params.get('name')     || 'Apollo Hospital',
  lat:       parseFloat(params.get('lat'))  || 12.9716,
  lng:       parseFloat(params.get('lng'))  || 77.5946,
  blood:     params.get('blood')    || 'O+',
  emergency: params.get('emg')      !== 'false',
};

/* ── GLOBAL STATE ────────────────────────────────────── */
let map, routingControl, routeLatLngs = [];
let currentMode = 'car';
let donorMarker, hospitalMarker;
let avatarEl, avatarIcon;
let animationFrameId = null;
let animProgress = 0;
let isNavigating = false;
let totalRouteLength = 0;
let userLatLng = null;

const MODE_CONFIG = {
  car:  { speed: 40, label: 'Drive',  color: '#ff2d55', trailColor: 'rgba(255,45,85,0.7)',  routeWeight: 7, icon: '🚗', etaMult: 1 },
  bike: { speed: 18, label: 'Bike',   color: '#00bfff', trailColor: 'rgba(0,191,255,0.7)',  routeWeight: 6, icon: '🚴', etaMult: 2.2 },
  walk: { speed: 5,  label: 'Walk',   color: '#00e676', trailColor: 'rgba(0,230,118,0.7)',  routeWeight: 5, icon: '🚶', etaMult: 8 },
};

/* ══════════════════════════════════════════════════════
   1. MAP INIT
══════════════════════════════════════════════════════ */
function initMap() {
  map = L.map('map', {
    zoomControl: false,
    attributionControl: false,
    preferCanvas: true,
  });

  // Carto dark premium tiles
  L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    maxZoom: 19,
    subdomains: 'abcd',
  }).addTo(map);

  // Tiny attribution in corner
  L.control.attribution({ position: 'bottomright', prefix: '' }).addTo(map);

  // Zoom control top-right with glass styling
  L.control.zoom({ position: 'topright' }).addTo(map);

  populateHospitalCard();
  getUserLocation();
}

/* ══════════════════════════════════════════════════════
   2. GEOLOCATION
══════════════════════════════════════════════════════ */
function getUserLocation() {
  if (!navigator.geolocation) {
    fallbackLocation();
    return;
  }
  navigator.geolocation.getCurrentPosition(
    pos => {
      userLatLng = L.latLng(pos.coords.latitude, pos.coords.longitude);
      onLocationReady();
    },
    () => fallbackLocation(),
    { enableHighAccuracy: true, timeout: 8000 }
  );
}

function fallbackLocation() {
  // Bangalore centre as fallback
  userLatLng = L.latLng(12.9716, 77.5946);
  onLocationReady();
}

function onLocationReady() {
  const hospLatLng = L.latLng(HOSPITAL_DATA.lat, HOSPITAL_DATA.lng);

  // Place custom donor avatar
  donorMarker = L.marker(userLatLng, { icon: createDonorIcon(), zIndexOffset: 1000 }).addTo(map);
  avatarEl = donorMarker.getElement();

  // Place hospital marker
  hospitalMarker = L.marker(hospLatLng, { icon: createHospitalIcon(HOSPITAL_DATA.emergency) }).addTo(map);

  // Fit bounds
  map.fitBounds([userLatLng, hospLatLng], { padding: [60, 60] });

  // Build route
  buildRoute(userLatLng, hospLatLng);
}

/* ══════════════════════════════════════════════════════
   3. CUSTOM ICONS
══════════════════════════════════════════════════════ */
function createDonorIcon() {
  const html = `
    <div class="donor-avatar-marker">
      <div class="aura"></div>
      <div class="ring1"></div>
      <div class="ring2"></div>
      <div class="body">
        <div class="donor-avatar-inner">🧑‍⚕️</div>
      </div>
      <div class="float-heart">❤️</div>
    </div>`;
  return L.divIcon({ html, className: '', iconSize: [56, 56], iconAnchor: [28, 28] });
}

function createHospitalIcon(emergency = false) {
  const html = `
    <div style="position:relative;width:44px;height:52px;display:flex;flex-direction:column;align-items:center;">
      ${emergency ? `<div style="position:absolute;inset:-6px;border-radius:50%;border:2.5px solid rgba(255,45,85,0.6);animation:ringExpand 1.5s ease-out infinite;"></div>` : ''}
      <div style="
        width:44px;height:44px;
        background:linear-gradient(145deg,#1a0814,#2d0820);
        border:2px solid ${emergency ? 'rgba(255,45,85,0.8)' : 'rgba(255,45,85,0.4)'};
        border-radius:14px 14px 0 14px;
        display:flex;align-items:center;justify-content:center;
        font-size:22px;
        box-shadow:0 4px 20px rgba(255,45,85,0.${emergency ? '5' : '3'}),
                   ${emergency ? '0 0 20px rgba(255,45,85,0.3)' : ''};
        backdrop-filter:blur(8px);
        position:relative;z-index:2;
      ">✚</div>
      <div style="width:10px;height:10px;background:linear-gradient(135deg,#1a0814,#2d0820);border-right:2px solid rgba(255,45,85,0.4);border-bottom:2px solid rgba(255,45,85,0.4);transform:rotate(45deg);margin-top:-5px;z-index:1;position:relative;"></div>
    </div>`;
  return L.divIcon({ html, className: '', iconSize: [44, 52], iconAnchor: [22, 52] });
}

/* ══════════════════════════════════════════════════════
   4. ROUTING
══════════════════════════════════════════════════════ */
function buildRoute(from, to) {
  if (routingControl) {
    map.removeControl(routingControl);
    routingControl = null;
  }

  // Clear any existing polylines
  map.eachLayer(l => { if (l._isRouteLayer) map.removeLayer(l); });

  const cfg = MODE_CONFIG[currentMode];

  routingControl = L.Routing.control({
    waypoints: [from, to],
    routeWhileDragging: false,
    addWaypoints: false,
    showAlternatives: false,
    lineOptions: { styles: [], extendToWaypoints: false, missingRouteTolerance: 0 },
    createMarker: () => null,
    router: L.Routing.osrmv1({
      serviceUrl: 'https://router.project-osrm.org/route/v1',
      profile: currentMode === 'car' ? 'driving' : currentMode === 'bike' ? 'cycling' : 'foot',
    }),
  }).addTo(map);

  routingControl.on('routesfound', e => {
    const route = e.routes[0];
    routeLatLngs = route.coordinates;
    totalRouteLength = route.summary.totalDistance;

    // Draw styled polyline
    drawStyledRoute(routeLatLngs, cfg);

    // Update UI
    updateStats(route.summary.totalDistance, currentMode);

    // Re-animate avatar back to start if was navigating
    if (isNavigating) {
      animProgress = 0;
    }
  });

  routingControl.on('routingerror', () => {
    // Fallback: straight line
    routeLatLngs = [from, to];
    drawStyledRoute(routeLatLngs, cfg);
    const dist = from.distanceTo(to);
    updateStats(dist, currentMode);
  });
}

function drawStyledRoute(coords, cfg) {
  // Shadow/glow layer
  const glow = L.polyline(coords, {
    color: cfg.trailColor,
    weight: cfg.routeWeight + 8,
    opacity: 0.18,
    smoothFactor: 1,
  });
  glow._isRouteLayer = true;
  glow.addTo(map);

  // Main route
  const main = L.polyline(coords, {
    color: cfg.color,
    weight: cfg.routeWeight,
    opacity: 0.92,
    smoothFactor: 1,
    lineCap: 'round',
    lineJoin: 'round',
  });
  main._isRouteLayer = true;
  main.addTo(map);

  // Animated dash overlay
  const dash = L.polyline(coords, {
    color: '#fff',
    weight: 2,
    opacity: 0.3,
    smoothFactor: 1,
    dashArray: '8 16',
    dashOffset: '0',
  });
  dash._isRouteLayer = true;
  dash.addTo(map);

  // Animate dash offset
  let offset = 0;
  const animDash = () => {
    offset = (offset - 1) % 24;
    if (dash._path) dash._path.style.strokeDashoffset = offset;
    requestAnimationFrame(animDash);
  };
  requestAnimationFrame(animDash);
}

/* ══════════════════════════════════════════════════════
   5. STATS UPDATE
══════════════════════════════════════════════════════ */
function updateStats(distMetres, mode) {
  const cfg = MODE_CONFIG[mode];
  const km = (distMetres / 1000).toFixed(1);
  const minutes = Math.round((distMetres / 1000) / cfg.speed * 60);

  const etaEl    = document.getElementById('hospEta');
  const distEl   = document.getElementById('statDist');
  const etaEl2   = document.getElementById('statEta');
  const routeEl  = document.getElementById('statRoute');

  // Animate number change
  animCount(etaEl,  minutes + ' min');
  animCount(distEl, km + ' km');
  animCount(etaEl2, minutes + '');
  routeEl.textContent = cfg.label;
}

function animCount(el, newVal) {
  if (el.textContent === newVal) return;
  gsap.to(el, { opacity: 0, y: -8, duration: 0.18, onComplete: () => {
    el.textContent = newVal;
    gsap.to(el, { opacity: 1, y: 0, duration: 0.22 });
  }});
}

/* ══════════════════════════════════════════════════════
   6. TRANSPORT MODE
══════════════════════════════════════════════════════ */
function setMode(mode) {
  if (mode === currentMode) return;
  currentMode = mode;

  // Update buttons
  document.querySelectorAll('.transport-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.mode === mode);
  });

  // Rebuild route with new mode
  if (userLatLng) {
    const hospLatLng = L.latLng(HOSPITAL_DATA.lat, HOSPITAL_DATA.lng);
    buildRoute(userLatLng, hospLatLng);
  }

  // Flash transition
  gsap.fromTo('#map-container', { opacity: 0.6 }, { opacity: 1, duration: 0.4 });
}

/* ══════════════════════════════════════════════════════
   7. DONOR AVATAR ANIMATION ALONG ROUTE
══════════════════════════════════════════════════════ */
function startNavigation() {
  if (routeLatLngs.length < 2) return;
  isNavigating = true;
  animProgress = 0;

  // Button morph
  const btn = document.getElementById('startBtn');
  btn.innerHTML = `<span class="start-icon">⏸</span><span class="start-text">Navigating…</span><div class="start-shimmer"></div>`;
  btn.onclick = pauseNavigation;

  // Begin avatar travel
  travelAlongRoute();
}

function pauseNavigation() {
  isNavigating = false;
  if (animationFrameId) cancelAnimationFrame(animationFrameId);
  const btn = document.getElementById('startBtn');
  btn.innerHTML = `<span class="start-icon">▶</span><span class="start-text">Resume Navigation</span><div class="start-shimmer"></div>`;
  btn.onclick = startNavigation;
}

function travelAlongRoute() {
  if (!isNavigating) return;

  const DURATION_MS = 28000; // 28s full journey
  let startTime = null;

  // Total path length in screen coords — use latlng distances
  const segLengths = [];
  let total = 0;
  for (let i = 1; i < routeLatLngs.length; i++) {
    const d = routeLatLngs[i - 1].distanceTo(routeLatLngs[i]);
    segLengths.push(d);
    total += d;
  }

  function step(ts) {
    if (!isNavigating) return;
    if (!startTime) startTime = ts;
    const elapsed = ts - startTime;
    const t = Math.min(elapsed / DURATION_MS, 1);
    const eased = easeInOutCubic(t);

    // Find position along path
    const target = eased * total;
    let accumulated = 0;
    let pos = null;
    let angle = 0;

    for (let i = 0; i < segLengths.length; i++) {
      if (accumulated + segLengths[i] >= target) {
        const frac = (target - accumulated) / segLengths[i];
        const a = routeLatLngs[i];
        const b = routeLatLngs[i + 1];
        pos = L.latLng(
          a.lat + (b.lat - a.lat) * frac,
          a.lng + (b.lng - a.lng) * frac
        );
        // Heading angle
        angle = Math.atan2(b.lat - a.lat, b.lng - a.lng) * 180 / Math.PI;
        break;
      }
      accumulated += segLengths[i];
    }

    if (pos) {
      donorMarker.setLatLng(pos);
      // Rotate avatar body
      const body = donorMarker.getElement()?.querySelector('.body');
      if (body) body.style.transform = `rotate(${angle}deg)`;

      // Pan map gently
      map.panTo(pos, { animate: true, duration: 0.3, easeLinearity: 1 });

      // Update ETA countdown
      const pctLeft = 1 - eased;
      const cfg = MODE_CONFIG[currentMode];
      const remainDist = total * pctLeft;
      const remainMin = Math.round((remainDist / 1000) / cfg.speed * 60);
      const etaEl = document.getElementById('hospEta');
      if (etaEl) etaEl.textContent = remainMin + ' min';
    }

    if (t < 1) {
      animationFrameId = requestAnimationFrame(step);
    } else {
      onArrival();
    }
  }

  animationFrameId = requestAnimationFrame(step);
}

function easeInOutCubic(t) {
  return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
}

/* ══════════════════════════════════════════════════════
   8. ARRIVAL EXPERIENCE
══════════════════════════════════════════════════════ */
function onArrival() {
  isNavigating = false;

  // Move donor to hospital
  donorMarker.setLatLng(L.latLng(HOSPITAL_DATA.lat, HOSPITAL_DATA.lng));

  // Glow hospital marker
  const hospEl = hospitalMarker.getElement();
  if (hospEl) {
    gsap.to(hospEl, { filter: 'drop-shadow(0 0 20px #ff2d55)', duration: 0.6, repeat: -1, yoyo: true });
  }

  // Show confetti + overlay
  setTimeout(() => {
    launchConfetti();
    showArrivalOverlay();
  }, 600);
}

function showArrivalOverlay() {
  const overlay = document.getElementById('arrivalOverlay');
  overlay.classList.add('show');
  spawnHeartParticles();
}

function closeArrival() {
  document.getElementById('arrivalOverlay').classList.remove('show');
  stopConfetti();
  // Reset button
  const btn = document.getElementById('startBtn');
  btn.innerHTML = `<span class="start-icon">▶</span><span class="start-text">Navigate Again</span><div class="start-shimmer"></div>`;
  btn.onclick = startNavigation;
}

/* ══════════════════════════════════════════════════════
   9. HEART PARTICLES
══════════════════════════════════════════════════════ */
function spawnHeartParticles() {
  const container = document.getElementById('arrivalHearts');
  for (let i = 0; i < 18; i++) {
    setTimeout(() => {
      const h = document.createElement('div');
      h.textContent = ['❤️', '🩸', '💗', '💖'][Math.floor(Math.random() * 4)];
      h.style.cssText = `
        position:absolute;
        font-size:${14 + Math.random() * 18}px;
        left:${Math.random() * 100}%;
        bottom:0;
        animation: floatUp ${2 + Math.random() * 2}s ease-out forwards;
        opacity:0;
      `;
      container.appendChild(h);
      setTimeout(() => h.remove(), 4500);
    }, i * 160);
  }
}

/* Add floatUp keyframe dynamically */
const floatStyle = document.createElement('style');
floatStyle.textContent = `
  @keyframes floatUp {
    0% { transform: translateY(0) scale(0.5) rotate(0deg); opacity: 0; }
    20% { opacity: 1; }
    100% { transform: translateY(-220px) scale(1.2) rotate(${Math.random() > 0.5 ? '' : '-'}20deg); opacity: 0; }
  }`;
document.head.appendChild(floatStyle);

/* ══════════════════════════════════════════════════════
   10. CONFETTI
══════════════════════════════════════════════════════ */
let confettiRunning = false;
const canvas = document.getElementById('confettiCanvas');
const ctx = canvas.getContext('2d');
let particles = [];

function launchConfetti() {
  canvas.classList.add('show');
  canvas.width = window.innerWidth;
  canvas.height = window.innerHeight;
  confettiRunning = true;

  for (let i = 0; i < 140; i++) {
    particles.push({
      x: Math.random() * canvas.width,
      y: Math.random() * canvas.height * -0.5,
      r: 3 + Math.random() * 7,
      color: ['#ff2d55','#ff6b8a','#c0102a','#fff','#ffd60a','#00bfff'][Math.floor(Math.random() * 6)],
      rot: Math.random() * 360,
      vx: (Math.random() - 0.5) * 3,
      vy: 2 + Math.random() * 4,
      vr: (Math.random() - 0.5) * 8,
      shape: Math.random() > 0.5 ? 'rect' : 'circle',
    });
  }
  runConfetti();
}

function runConfetti() {
  if (!confettiRunning) { ctx.clearRect(0, 0, canvas.width, canvas.height); return; }
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  let alive = false;
  particles.forEach(p => {
    p.x += p.vx; p.y += p.vy; p.rot += p.vr; p.vy += 0.08;
    if (p.y < canvas.height + 30) alive = true;
    ctx.save();
    ctx.translate(p.x, p.y);
    ctx.rotate(p.rot * Math.PI / 180);
    ctx.fillStyle = p.color;
    ctx.globalAlpha = Math.max(0, 1 - (p.y / canvas.height));
    if (p.shape === 'rect') ctx.fillRect(-p.r, -p.r / 2, p.r * 2, p.r);
    else { ctx.beginPath(); ctx.arc(0, 0, p.r, 0, Math.PI * 2); ctx.fill(); }
    ctx.restore();
  });
  if (alive) requestAnimationFrame(runConfetti);
  else stopConfetti();
}

function stopConfetti() {
  confettiRunning = false;
  particles = [];
  canvas.classList.remove('show');
  ctx.clearRect(0, 0, canvas.width, canvas.height);
}

/* ══════════════════════════════════════════════════════
   11. HOSPITAL CARD POPULATION
══════════════════════════════════════════════════════ */
function populateHospitalCard() {
  document.getElementById('hospName').textContent = HOSPITAL_DATA.name;
  document.getElementById('bloodBadge').textContent = `🩸 ${HOSPITAL_DATA.blood} Needed`;
  if (!HOSPITAL_DATA.emergency) {
    const emg = document.getElementById('emgBadge');
    emg.style.display = 'none';
  }
}

/* ══════════════════════════════════════════════════════
   12. GSAP ENTRANCE ANIMATIONS
══════════════════════════════════════════════════════ */
function runEntranceAnimations() {
  // Panel slides up
  gsap.from('.bottom-panel', { y: 80, opacity: 0, duration: 0.6, ease: 'power3.out', delay: 0.3 });
  gsap.from('.back-btn',     { x: -30, opacity: 0, duration: 0.5, ease: 'back.out(1.7)', delay: 0.5 });
  gsap.from('.live-badge',   { x: 30, opacity: 0, duration: 0.5, ease: 'back.out(1.7)', delay: 0.6 });
  gsap.from('.transport-bar',{ y: 30, opacity: 0, duration: 0.5, ease: 'back.out(1.7)', delay: 0.7 });
  gsap.from('.hospital-card',{ y: 20, opacity: 0, duration: 0.5, ease: 'power2.out', delay: 0.5 });
  gsap.from('.stats-row',    { y: 20, opacity: 0, duration: 0.4, ease: 'power2.out', delay: 0.65 });
  gsap.from('.start-btn',    { y: 20, opacity: 0, duration: 0.4, ease: 'power2.out', delay: 0.75 });
}

/* ══════════════════════════════════════════════════════
   BOOT
══════════════════════════════════════════════════════ */
window.addEventListener('DOMContentLoaded', () => {
  gsap.registerPlugin(MotionPathPlugin);
  initMap();
  runEntranceAnimations();
});

window.addEventListener('resize', () => {
  canvas.width = window.innerWidth;
  canvas.height = window.innerHeight;
});