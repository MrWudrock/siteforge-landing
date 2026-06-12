(function () {
  'use strict';

  /* ========== PARTICLES ========== */
  var pCanvas = document.getElementById('particles-canvas');
  if (pCanvas) {
    var ctx = pCanvas.getContext('2d');
    var particles = [];
    var pCount = 60;

    function resizeP() {
      pCanvas.width = window.innerWidth;
      pCanvas.height = window.innerHeight;
    }
    resizeP();
    window.addEventListener('resize', resizeP);

    for (var i = 0; i < pCount; i++) {
      particles.push({
        x: Math.random() * pCanvas.width,
        y: Math.random() * pCanvas.height,
        vx: (Math.random() - 0.5) * 0.5,
        vy: (Math.random() - 0.5) * 0.5,
        r: Math.random() * 3 + 1,
        a: Math.random() * 0.3 + 0.1
      });
    }

    function drawP() {
      ctx.clearRect(0, 0, pCanvas.width, pCanvas.height);
      for (var i = 0; i < particles.length; i++) {
        var p = particles[i];
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.fillStyle = 'rgba(245, 158, 11, ' + p.a + ')';
        ctx.fill();
        p.x += p.vx;
        p.y += p.vy;
        if (p.x < 0 || p.x > pCanvas.width) p.vx *= -1;
        if (p.y < 0 || p.y > pCanvas.height) p.vy *= -1;
        for (var j = i + 1; j < particles.length; j++) {
          var q = particles[j];
          var dx = p.x - q.x;
          var dy = p.y - q.y;
          var dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < 120) {
            ctx.beginPath();
            ctx.moveTo(p.x, p.y);
            ctx.lineTo(q.x, q.y);
            ctx.strokeStyle = 'rgba(245, 158, 11, ' + (0.08 * (1 - dist / 120)) + ')';
            ctx.stroke();
          }
        }
      }
      requestAnimationFrame(drawP);
    }
    drawP();
  }

  /* ========== CONFETTI ========== */
  var cCanvas = document.getElementById('confetti-canvas');
  var confettiCtx, confettiPieces, confettiAnim;

  function startConfetti() {
    if (!cCanvas) return;
    cCanvas.width = window.innerWidth;
    cCanvas.height = window.innerHeight;
    confettiCtx = cCanvas.getContext('2d');
    confettiPieces = [];
    var colors = ['#f59e0b', '#f97316', '#ef4444', '#fbbf24', '#fcd34d', '#fb923c'];
    for (var i = 0; i < 150; i++) {
      confettiPieces.push({
        x: Math.random() * cCanvas.width,
        y: Math.random() * cCanvas.height * -1,
        w: Math.random() * 10 + 5,
        h: Math.random() * 6 + 3,
        color: colors[Math.floor(Math.random() * colors.length)],
        vx: (Math.random() - 0.5) * 4,
        vy: Math.random() * 3 + 2,
        rot: Math.random() * 360,
        rotSpeed: (Math.random() - 0.5) * 10
      });
    }
    if (confettiAnim) cancelAnimationFrame(confettiAnim);
    drawConfetti();
  }

  function drawConfetti() {
    confettiCtx.clearRect(0, 0, cCanvas.width, cCanvas.height);
    var allDone = true;
    for (var i = 0; i < confettiPieces.length; i++) {
      var c = confettiPieces[i];
      confettiCtx.save();
      confettiCtx.translate(c.x, c.y);
      confettiCtx.rotate((c.rot * Math.PI) / 180);
      confettiCtx.fillStyle = c.color;
      confettiCtx.fillRect(-c.w / 2, -c.h / 2, c.w, c.h);
      confettiCtx.restore();
      c.x += c.vx;
      c.y += c.vy;
      c.rot += c.rotSpeed;
      c.vy += 0.05;
      if (c.y < cCanvas.height + 20) allDone = false;
    }
    if (!allDone) {
      confettiAnim = requestAnimationFrame(drawConfetti);
    } else {
      confettiCtx.clearRect(0, 0, cCanvas.width, cCanvas.height);
    }
  }

  /* ========== COUNTDOWN ========== */
  function getEndOfDay() {
    var now = new Date();
    var end = new Date(now);
    end.setHours(23, 59, 59, 999);
    return end;
  }

  function formatTime(ms) {
    if (ms <= 0) return '00:00:00';
    var h = Math.floor(ms / 3600000);
    var m = Math.floor((ms % 3600000) / 60000);
    var s = Math.floor((ms % 60000) / 1000);
    return [h, m, s].map(function (n) { return String(n).padStart(2, '0'); }).join(':');
  }

  function updateCountdowns() {
    var remaining = getEndOfDay() - Date.now();
    var formatted = formatTime(remaining);
    ['topCountdown', 'pricingCountdown'].forEach(function (id) {
      var el = document.getElementById(id);
      if (el) el.textContent = formatted;
    });
  }
  updateCountdowns();
  setInterval(updateCountdowns, 1000);

  /* ========== SCARCITY SLOTS ========== */
  function getSlots() {
    var key = 'siteforge_slots_' + new Date().toDateString();
    var slots = localStorage.getItem(key);
    if (!slots) {
      slots = String(Math.floor(Math.random() * 2) + 2);
      localStorage.setItem(key, slots);
    }
    return parseInt(slots, 10);
  }

  var slots = getSlots();
  var slotsTotal = 5;
  var slotsUsed = slotsTotal - slots;

  ['slotsLeft', 'slotsPricing', 'slotsOrder'].forEach(function (id) {
    var el = document.getElementById(id);
    if (el) el.textContent = slots;
  });

  var slotsBar = document.getElementById('slotsBar');
  if (slotsBar) {
    slotsBar.style.width = ((slotsUsed / slotsTotal) * 100) + '%';
  }

  /* ========== STICKY CTA ========== */
  var stickyCta = document.getElementById('stickyCta');
  var hero = document.querySelector('.hero');
  if (stickyCta && hero) {
    var observer = new IntersectionObserver(
      function (entries) {
        stickyCta.classList.toggle('visible', !entries[0].isIntersecting);
      },
      { threshold: 0 }
    );
    observer.observe(hero);
  }

  /* ========== MOBILE MENU ========== */
  var burger = document.getElementById('burger');
  var mobileNav = document.getElementById('mobileNav');
  if (burger && mobileNav) {
    burger.addEventListener('click', function () {
      mobileNav.classList.toggle('open');
    });
    mobileNav.querySelectorAll('a').forEach(function (link) {
      link.addEventListener('click', function () { mobileNav.classList.remove('open'); });
    });
  }

  /* ========== SCROLL REVEAL ========== */
  function initScrollReveal() {
    var els = document.querySelectorAll('.reveal, .reveal-left, .reveal-right, .reveal-scale');
    if (els.length === 0) return;
    var ro = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible');
          ro.unobserve(entry.target);
        }
      });
    }, { threshold: 0.15 });
    els.forEach(function (el) { ro.observe(el); });
  }
  initScrollReveal();

  /* ========== NUMBER COUNTER ========== */
  function animateCounters() {
    var counters = document.querySelectorAll('.stat-num');
    if (counters.length === 0) return;
    var co = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          var el = entry.target;
          var text = el.textContent;
          var target = parseInt(text.replace(/[^0-9]/g, ''), 10);
          if (isNaN(target)) { co.unobserve(el); return; }
          var suffix = text.replace(/[0-9]/g, '');
          var duration = 2000;
          var start = performance.now();
          function step(now) {
            var p = Math.min((now - start) / duration, 1);
            var eased = 1 - Math.pow(1 - p, 3);
            var current = Math.round(eased * target);
            el.textContent = current + suffix;
            if (p < 1) requestAnimationFrame(step);
            else el.textContent = target + suffix;
          }
          requestAnimationFrame(step);
          co.unobserve(el);
        }
      });
    }, { threshold: 0.5 });
    counters.forEach(function (el) { co.observe(el); });
  }
  animateCounters();

  /* ========== ORDER FORM ========== */
  var form = document.getElementById('orderForm');
  var modal = document.getElementById('successModal');
  var closeModal = document.getElementById('closeModal');
  var modalLink = document.getElementById('modalOrderLink');
  var modalOrderId = document.getElementById('modalOrderId');
  var modalIcon = document.querySelector('.modal-icon');

  if (form) {
    form.addEventListener('submit', function (e) {
      e.preventDefault();

      var name = document.getElementById('name').value.trim();
      var phone = document.getElementById('phone').value.trim();
      var email = document.getElementById('email').value.trim();
      var description = document.getElementById('description').value.trim();

      var payload = { name: name, phone: phone, email: email, description: description };
      var WEBHOOK_URL = 'https://bot.symplesite.ru/webhook';

      fetch(WEBHOOK_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.order_id) {
          var link = 'https://bot.symplesite.ru/order/' + data.order_id + '/questions';
          if (modalLink) { modalLink.href = link; modalLink.textContent = link; }
          if (modalOrderId) { modalOrderId.textContent = data.order_id; }
        }
      })
      .catch(function () {});

      if (modal) {
        modal.classList.add('open');
        modal.setAttribute('aria-hidden', 'false');
        startConfetti();
      }

      form.reset();
    });
  }

  if (closeModal && modal) {
    closeModal.addEventListener('click', function () {
      modal.classList.remove('open');
      modal.setAttribute('aria-hidden', 'true');
      if (confettiAnim) cancelAnimationFrame(confettiAnim);
      if (confettiCtx) confettiCtx.clearRect(0, 0, cCanvas.width, cCanvas.height);
    });
    modal.querySelector('.modal-overlay').addEventListener('click', function () {
      modal.classList.remove('open');
      modal.setAttribute('aria-hidden', 'true');
      if (confettiAnim) cancelAnimationFrame(confettiAnim);
      if (confettiCtx) confettiCtx.clearRect(0, 0, cCanvas.width, cCanvas.height);
    });
  }

  /* ========== SMOOTH ANCHOR SCROLL ========== */
  document.querySelectorAll('a[href^="#"]').forEach(function (anchor) {
    anchor.addEventListener('click', function (e) {
      var targetId = this.getAttribute('href');
      if (targetId === '#') return;
      var target = document.querySelector(targetId);
      if (!target) return;
      e.preventDefault();
      var offset = 120;
      var top = target.getBoundingClientRect().top + window.scrollY - offset;
      window.scrollTo({ top: top, behavior: 'smooth' });
    });
  });
})();