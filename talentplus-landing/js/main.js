/* ═══════════════════════════════════════════════════
   TALENTPLUS AI — LANDING PAGE JS
   Features:
   - Neural canvas particle network
   - Magnetic hover effect on CTAs
   - AOS (scroll-triggered animations)
   - Counter animation
   - Reviews carousel autoplay
   - Nav scroll behavior
   - Hamburger mobile menu
═══════════════════════════════════════════════════ */

/* ─── DOM READY ──────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  initAppLoginLinks();
  initLandingTabs();
  initNeuralCanvas();
  initMagneticElements();
  initScrollAnimations();
  initCounters();
  initTestimonialSlider();
  initNav();
  initMobileMenu();
});

function initLandingTabs() {
  document.querySelectorAll('[data-tabs]').forEach((root) => {
    const tabs = root.querySelectorAll('.landing-tab');
    const panels = root.querySelectorAll('.landing-panel');
    tabs.forEach((tab) => {
      tab.addEventListener('click', () => {
        const id = tab.getAttribute('data-tab');
        tabs.forEach((t) => {
          const on = t === tab;
          t.classList.toggle('active', on);
          t.setAttribute('aria-selected', on ? 'true' : 'false');
        });
        panels.forEach((p) => {
          const on = p.getAttribute('data-panel') === id;
          p.classList.toggle('active', on);
          if (on) p.removeAttribute('hidden');
          else p.setAttribute('hidden', '');
        });
      });
    });
  });
}

/* Sign in → Next.js `/login`. Different origins in dev; set window.TALENTPLUS_APP_URL in index.html for production. https://developer.mozilla.org/en-US/docs/Web/API/URL/URL */
function initAppLoginLinks() {
  const origin = (window.TALENTPLUS_APP_URL || 'http://127.0.0.1:3000').replace(/\/$/, '');
  document.querySelectorAll('[data-app-login]').forEach((el) => {
    el.setAttribute('href', origin + '/login');
  });
}

/* ─── NEURAL CANVAS ─────────────────────────────── */
function initNeuralCanvas() {
    const canvas = document.getElementById('neuralCanvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
  
    let W = 0, H = 0, nodes = [], raf;
    const NODE_COUNT = 80;
    const MAX_DIST = 160;
    const TEAL = '0,230,200';
    const INDIGO = '129,140,248';
  
    function resize() {
      W = canvas.width = window.innerWidth;
      H = canvas.height = window.innerHeight;
    }
    window.addEventListener('resize', resize);
    resize();
  
    function createNodes() {
      nodes = [];
      for (let i = 0; i < NODE_COUNT; i++) {
        nodes.push({
          x: Math.random() * W,
          y: Math.random() * H,
          vx: (Math.random() - 0.5) * 0.35,
          vy: (Math.random() - 0.5) * 0.35,
          r: Math.random() * 1.8 + 0.6,
          color: Math.random() > 0.6 ? INDIGO : TEAL,
          opacity: Math.random() * 0.5 + 0.3
        });
      }
    }
    createNodes();
  
    let mouseX = -999, mouseY = -999;
    document.addEventListener('mousemove', (e) => { mouseX = e.clientX; mouseY = e.clientY; });
  
    function draw() {
      ctx.clearRect(0, 0, W, H);
  
      nodes.forEach(n => {
        n.x += n.vx;
        n.y += n.vy;
        if (n.x < 0) n.x = W;
        if (n.x > W) n.x = 0;
        if (n.y < 0) n.y = H;
        if (n.y > H) n.y = 0;
  
        const dx = mouseX - n.x;
        const dy = mouseY - n.y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < 200 && dist > 0) {
          n.vx += (dx / dist) * 0.008;
          n.vy += (dy / dist) * 0.008;
        }
        const speed = Math.sqrt(n.vx * n.vx + n.vy * n.vy);
        if (speed > 0.9) { n.vx *= 0.95; n.vy *= 0.95; }
      });
  
      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          const a = nodes[i], b = nodes[j];
          const dx = a.x - b.x;
          const dy = a.y - b.y;
          const d = Math.sqrt(dx * dx + dy * dy);
          if (d < MAX_DIST) {
            const alpha = (1 - d / MAX_DIST) * 0.3;
            ctx.beginPath();
            ctx.moveTo(a.x, a.y);
            ctx.lineTo(b.x, b.y);
            ctx.strokeStyle = `rgba(${a.color},${alpha})`;
            ctx.lineWidth = 0.7;
            ctx.stroke();
          }
        }
      }
  
      nodes.forEach(n => {
        ctx.beginPath();
        ctx.arc(n.x, n.y, n.r, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(${n.color},${n.opacity})`;
        ctx.fill();
      });
  
      raf = requestAnimationFrame(draw);
    }
    draw();
  }
  
  /* ─── MAGNETIC HOVER EFFECT ──────────────────────── */
  function initMagneticElements() {
    const magnets = document.querySelectorAll('.magnetic');
    magnets.forEach(el => {
      el.addEventListener('mousemove', (e) => {
        const rect = el.getBoundingClientRect();
        const cx = rect.left + rect.width / 2;
        const cy = rect.top + rect.height / 2;
        const dx = e.clientX - cx;
        const dy = e.clientY - cy;
        const maxStrength = 12;
        const tx = (dx / rect.width) * maxStrength * 2;
        const ty = (dy / rect.height) * maxStrength * 2;
        el.style.transform = `translate(${tx}px, ${ty}px)`;
      });
      el.addEventListener('mouseleave', () => {
        el.style.transform = '';
      });
    });
  }
  
  /* ─── SCROLL-BASED ANIMATIONS (AOS) ─────────────── */
  function initScrollAnimations() {
    const elements = document.querySelectorAll('.aos-fade-up');
  
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible');
          observer.unobserve(entry.target);
        }
      });
    }, {
      threshold: 0.12,
      rootMargin: '0px 0px -40px 0px'
    });
  
    elements.forEach(el => observer.observe(el));
  }
  
  /* ─── COUNTER ANIMATION ───────────────────────────── */
  function initCounters() {
    const counters = document.querySelectorAll('.counter');
  
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (!entry.isIntersecting) return;
        const el = entry.target;
        const target = parseInt(el.dataset.target, 10);
        const suffix = el.querySelector('span') ? el.querySelector('span').textContent : '';
  
        let start = 0;
        const duration = 1800;
        const step = (timestamp) => {
          if (!start) start = timestamp;
          const progress = Math.min((timestamp - start) / duration, 1);
          const eased = 1 - Math.pow(1 - progress, 3);
          const current = Math.round(eased * target);
  
          el.childNodes[0].textContent = current;
  
          if (progress < 1) requestAnimationFrame(step);
        };
        requestAnimationFrame(step);
        observer.unobserve(el);
      });
    }, { threshold: 0.5 });
  
    counters.forEach(c => observer.observe(c));
  }
  
  /* ─── REVIEWS CAROUSEL ───────────────────────────── */
  function initTestimonialSlider() {
    const track = document.getElementById('testimonialTrack');
    const dotsContainer = document.getElementById('sliderDots');
    if (!track) return;
  
    const cards = track.querySelectorAll('.testimonial-card');
    const dots = dotsContainer ? dotsContainer.querySelectorAll('.dot') : [];
    let current = 0;
    let autoTimer;
    let cardsPerView = window.innerWidth > 768 ? 2 : 1;
  
    window.addEventListener('resize', () => {
      cardsPerView = window.innerWidth > 768 ? 2 : 1;
      goTo(current);
    });
  
    function goTo(idx) {
      current = ((idx % cards.length) + cards.length) % cards.length;
      const cardWidth = cards[0].offsetWidth + 24;
      track.style.transform = `translateX(-${current * cardWidth}px)`;
      dots.forEach((d, i) => d.classList.toggle('active', i === current));
    }
  
    function startAuto() {
      autoTimer = setInterval(() => goTo(current + 1), 5000);
    }
    function stopAuto() {
      clearInterval(autoTimer);
    }
  
    dots.forEach((d) => {
      d.addEventListener('click', () => {
        stopAuto();
        goTo(parseInt(d.dataset.idx, 10));
        startAuto();
      });
    });
  
    let touchStartX = 0;
    track.addEventListener('touchstart', (e) => { touchStartX = e.touches[0].clientX; stopAuto(); });
    track.addEventListener('touchend', (e) => {
      const diff = touchStartX - e.changedTouches[0].clientX;
      if (Math.abs(diff) > 40) goTo(current + (diff > 0 ? 1 : -1));
      startAuto();
    });
  
    startAuto();
  }
  
  /* ─── NAV SCROLL BEHAVIOR ────────────────────────── */
  function initNav() {
    const nav = document.getElementById('mainNav');
    if (!nav) return;
  
    window.addEventListener('scroll', () => {
      nav.classList.toggle('scrolled', window.scrollY > 40);
    });
  }
  
  /* ─── MOBILE MENU ────────────────────────────────── */
  function initMobileMenu() {
    const btn = document.getElementById('hamburger');
    const menu = document.getElementById('mobileMenu');
    if (!btn || !menu) return;
  
    btn.addEventListener('click', () => {
      const open = menu.classList.toggle('open');
      btn.querySelectorAll('span').forEach((s, i) => {
        s.style.transform = open
          ? (i === 0 ? 'translateY(7px) rotate(45deg)' : i === 2 ? 'translateY(-7px) rotate(-45deg)' : 'scaleX(0)')
          : '';
        s.style.opacity = open && i === 1 ? '0' : '';
      });
    });
  
    menu.querySelectorAll('a').forEach(a => {
      a.addEventListener('click', () => {
        menu.classList.remove('open');
        btn.querySelectorAll('span').forEach(s => { s.style.transform = ''; s.style.opacity = ''; });
      });
    });
  }