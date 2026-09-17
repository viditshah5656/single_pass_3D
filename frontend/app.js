const Aero = (() => {
  const WALLPAPERS = [
    {id: 1, name: 'Dolomite Blue', glow: ['rgba(70,190,255,.2)','rgba(115,130,255,.2)']},
    {id: 2, name: 'Coastal Dusk', glow: ['rgba(255,130,120,.16)','rgba(55,205,220,.2)']},
    {id: 3, name: 'Desert Monuments', glow: ['rgba(255,145,70,.18)','rgba(110,175,255,.17)']},
    {id: 5, name: 'Emerald Coast', glow: ['rgba(40,225,190,.18)','rgba(55,150,255,.18)']},
    {id: 6, name: 'Autumn Garden', glow: ['rgba(255,95,65,.17)','rgba(110,210,115,.16)']},
    {id: 7, name: 'Alpine Mirror', glow: ['rgba(65,155,255,.2)','rgba(90,220,230,.17)']},
    {id: 8, name: 'Lakeside Village', glow: ['rgba(45,215,170,.17)','rgba(80,175,210,.18)']},
  ];
  const $ = (q, root = document) => root.querySelector(q);
  const $$ = (q, root = document) => [...root.querySelectorAll(q)];

  function api(path, options = {}) {
    return fetch(`/api/v1${path}`, options).then(async response => {
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.detail || body.message || `Request failed (${response.status})`);
      return body;
    });
  }

  function toast(message, bad = false) {
    let stack = $('.toast-stack');
    if (!stack) {
      stack = document.createElement('div');
      stack.className = 'toast-stack';
      document.body.appendChild(stack);
    }
    const item = document.createElement('div');
    item.className = `toast${bad ? ' bad' : ''}`;
    item.textContent = message;
    stack.appendChild(item);
    setTimeout(() => item.remove(), 4200);
  }

  function modal(id, open = true) {
    const node = document.getElementById(id);
    if (!node) return;
    if (open) $$('.modal-backdrop.open').forEach(item => item.classList.remove('open'));
    node.classList.toggle('open', open);
    document.body.style.overflow = open ? 'hidden' : '';
  }

  function initShell() {
    const page = document.body.dataset.page;
    $$('[data-nav]').forEach(a => a.classList.toggle('active', a.dataset.nav === page));
    $$('[data-nav], .brand').forEach(link => {
      link.target = '_self';
      link.addEventListener('click', event => {
        if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
        event.preventDefault();
        window.location.assign(link.href);
      });
    });
    $('.menu-toggle')?.addEventListener('click', () => $('.nav')?.classList.toggle('open'));
    $$('[data-modal-open]').forEach(b => b.addEventListener('click', () => modal(b.dataset.modalOpen)));
    $$('[data-modal-close]').forEach(b => b.addEventListener('click', () => modal(b.closest('.modal-backdrop').id, false)));
    $$('.modal-backdrop').forEach(b => b.addEventListener('click', e => { if (e.target === b) modal(b.id, false); }));
    document.addEventListener('keydown', e => { if (e.key === 'Escape') $$('.modal-backdrop.open').forEach(m => modal(m.id, false)); });
    refreshStatus();
    initWallpaper();
    initAmbient();
  }

  function initWallpaper() {
    const root = $('#wallpaperRoot');
    if (!root) return;
    const layers = $$('.wallpaper-layer', root);
    const savedId = Number(localStorage.getItem('aerosynth:wallpaper'));
    let index = Math.max(0, WALLPAPERS.findIndex(item => item.id === savedId));
    let front = 0;
    let autoplay = localStorage.getItem('aerosynth:wallpaperAuto') !== 'false';
    let timer;

    const apply = (nextIndex, persist = true) => {
      index = (nextIndex + WALLPAPERS.length) % WALLPAPERS.length;
      const item = WALLPAPERS[index];
      const nextLayer = layers[1 - front];
      nextLayer.style.backgroundImage = `url('/frontend/assets/wallpapers/wallpaper-${item.id}.webp')`;
      nextLayer.classList.add('active');
      layers[front].classList.remove('active');
      front = 1 - front;
      root.style.setProperty('--wall-glow-a', item.glow[0]);
      root.style.setProperty('--wall-glow-b', item.glow[1]);
      $('#wallpaperName').textContent = item.name;
      $$('.wallpaper-option').forEach(card => card.classList.toggle('active', Number(card.dataset.wallpaper) === item.id));
      if (persist) localStorage.setItem('aerosynth:wallpaper', String(item.id));
      const preloadNext = () => {
        const preload = new Image();
        preload.src = `/frontend/assets/wallpapers/wallpaper-${WALLPAPERS[(index + 1) % WALLPAPERS.length].id}.webp`;
      };
      if ('requestIdleCallback' in window) requestIdleCallback(preloadNext, {timeout: 4000});
      else setTimeout(preloadNext, 2500);
      schedule();
    };
    const schedule = () => {
      clearTimeout(timer);
      if (autoplay) timer = setTimeout(() => apply(index + 1, true), 18000);
    };
    $$('.wallpaper-option').forEach(card => card.addEventListener('click', () => apply(WALLPAPERS.findIndex(item => item.id === Number(card.dataset.wallpaper)))));
    $('#wallpaperPrev').addEventListener('click', () => apply(index - 1));
    $('#wallpaperNext').addEventListener('click', () => apply(index + 1));
    const toggle = $('#wallpaperAuto');
    toggle.checked = autoplay;
    toggle.addEventListener('change', () => { autoplay = toggle.checked; localStorage.setItem('aerosynth:wallpaperAuto', String(autoplay)); schedule(); });
    document.addEventListener('visibilitychange', () => document.hidden ? clearTimeout(timer) : schedule());
    apply(index, false);
  }

  async function refreshStatus() {
    const status = $('#globalStatus');
    try {
      const data = await api('/preflight');
      if (status) status.innerHTML = `<span class="dot ${data.status === 'ready' ? 'good' : ''}"></span>${data.status === 'ready' ? 'Reconstruction ready' : 'Setup incomplete'}`;
    } catch (_) {
      if (status) status.innerHTML = '<span class="dot"></span>API offline';
    }
  }

  function initAmbient() {
    const canvas = document.getElementById('ambient');
    if (!canvas || matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    const ctx = canvas.getContext('2d');
    let points = [];
    const resize = () => {
      canvas.width = innerWidth * devicePixelRatio;
      canvas.height = innerHeight * devicePixelRatio;
      canvas.style.width = `${innerWidth}px`; canvas.style.height = `${innerHeight}px`;
      ctx.setTransform(devicePixelRatio, 0, 0, devicePixelRatio, 0, 0);
      points = Array.from({length: Math.min(65, Math.floor(innerWidth / 22))}, () => ({x: Math.random()*innerWidth, y: Math.random()*innerHeight, r: Math.random()*1.6+.4, v: Math.random()*.18+.05}));
    };
    const draw = () => {
      ctx.clearRect(0,0,innerWidth,innerHeight);
      points.forEach(p => { p.y -= p.v; if (p.y < -4) p.y = innerHeight+4; ctx.beginPath(); ctx.fillStyle='rgba(150,225,255,.42)'; ctx.arc(p.x,p.y,p.r,0,Math.PI*2); ctx.fill(); });
      requestAnimationFrame(draw);
    };
    addEventListener('resize', resize); resize(); draw();
  }

  function shell() {
    const wallpaperCards = WALLPAPERS.map(item => `<button class="wallpaper-option" data-wallpaper="${item.id}" type="button"><img src="/frontend/assets/wallpapers/wallpaper-${item.id}-thumb.webp" alt="${item.name}" loading="lazy"><span>${item.name}</span></button>`).join('');
    return `<div class="wallpaper" id="wallpaperRoot"><div class="wallpaper-layer"></div><div class="wallpaper-layer"></div></div><canvas id="ambient"></canvas>
      <header class="topbar glass">
        <a class="brand" href="/" target="_self"><span class="brand-mark">✦</span><span><strong>AeroSynth</strong><small>Spatial intelligence</small></span></a>
        <nav class="nav">
          <a data-nav="overview" href="/" target="_self">Overview</a><a data-nav="reconstruct" href="/reconstruct" target="_self">Reconstruct</a><a data-nav="jobs" href="/jobs" target="_self">Jobs</a><a data-nav="outputs" href="/outputs" target="_self">Deliverables</a><a data-nav="system" href="/system" target="_self">System</a><a data-nav="studio" href="/studio" target="_self">Studio</a>
        </nav>
        <div class="top-actions"><span id="globalStatus" class="status-pill"><span class="dot"></span>Connecting</span><button class="btn btn-secondary icon-btn" data-modal-open="wallpaperModal" aria-label="Choose wallpaper" title="Choose wallpaper">▧</button><button class="btn btn-primary" data-modal-open="newProjectModal">New project</button><button class="btn btn-secondary icon-btn menu-toggle" aria-label="Open navigation">☰</button></div>
      </header>
      <div class="modal-backdrop" id="wallpaperModal"><div class="modal glass"><div class="modal-head"><div><span class="eyebrow">Live atmosphere</span><h2>Choose your wallpaper</h2><p class="muted" style="margin:5px 0 0">Seven optimized landscapes from the project collection.</p></div><button class="btn btn-secondary icon-btn" data-modal-close>×</button></div><div class="wallpaper-grid">${wallpaperCards}</div><div class="wallpaper-controls"><div><strong id="wallpaperName">Wallpaper</strong><label style="display:flex;align-items:center;gap:8px;margin-top:5px" class="muted"><input id="wallpaperAuto" type="checkbox"> Rotate every 18 seconds</label></div><div class="wallpaper-nav"><button id="wallpaperPrev" class="btn btn-secondary icon-btn" type="button" aria-label="Previous wallpaper">←</button><button id="wallpaperNext" class="btn btn-secondary icon-btn" type="button" aria-label="Next wallpaper">→</button></div></div></div></div>`;
  }

  document.addEventListener('DOMContentLoaded', initShell);
  return { $, $$, api, toast, modal, shell };
})();
