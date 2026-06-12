(function () {
  'use strict';

  // ===== Countdown to end of day =====
  function getEndOfDay() {
    const now = new Date();
    const end = new Date(now);
    end.setHours(23, 59, 59, 999);
    return end;
  }

  function formatTime(ms) {
    if (ms <= 0) return '00:00:00';
    const h = Math.floor(ms / 3600000);
    const m = Math.floor((ms % 3600000) / 60000);
    const s = Math.floor((ms % 60000) / 1000);
    return [h, m, s].map(n => String(n).padStart(2, '0')).join(':');
  }

  function updateCountdowns() {
    const remaining = getEndOfDay() - Date.now();
    const formatted = formatTime(remaining);
    ['topCountdown', 'pricingCountdown'].forEach(id => {
      const el = document.getElementById(id);
      if (el) el.textContent = formatted;
    });
  }

  updateCountdowns();
  setInterval(updateCountdowns, 1000);

  // ===== Scarcity slots (persisted per day) =====
  function getSlots() {
    const key = 'siteforge_slots_' + new Date().toDateString();
    let slots = localStorage.getItem(key);
    if (!slots) {
      slots = String(Math.floor(Math.random() * 2) + 2); // 2-3 slots
      localStorage.setItem(key, slots);
    }
    return parseInt(slots, 10);
  }

  const slots = getSlots();
  const slotsTotal = 5;
  const slotsUsed = slotsTotal - slots;

  ['slotsLeft', 'slotsPricing', 'slotsOrder'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.textContent = slots;
  });

  const slotsBar = document.getElementById('slotsBar');
  if (slotsBar) {
    slotsBar.style.width = ((slotsUsed / slotsTotal) * 100) + '%';
  }

  // ===== Sticky CTA on scroll =====
  const stickyCta = document.getElementById('stickyCta');
  const hero = document.querySelector('.hero');

  if (stickyCta && hero) {
    const observer = new IntersectionObserver(
      ([entry]) => {
        stickyCta.classList.toggle('visible', !entry.isIntersecting);
      },
      { threshold: 0 }
    );
    observer.observe(hero);
  }

  // ===== Mobile menu =====
  const burger = document.getElementById('burger');
  const mobileNav = document.getElementById('mobileNav');

  if (burger && mobileNav) {
    burger.addEventListener('click', () => {
      mobileNav.classList.toggle('open');
    });

    mobileNav.querySelectorAll('a').forEach(link => {
      link.addEventListener('click', () => mobileNav.classList.remove('open'));
    });
  }

  // ===== Order form =====
  const form = document.getElementById('orderForm');
  const modal = document.getElementById('successModal');
  const closeModal = document.getElementById('closeModal');

  if (form) {
    form.addEventListener('submit', function (e) {
      e.preventDefault();

      const name = document.getElementById('name').value.trim();
      const phone = document.getElementById('phone').value.trim();
      const email = document.getElementById('email').value.trim();
      const description = document.getElementById('description').value.trim();

      const payload = { name, phone, email, description };

      // Try webhook (Render), fallback to mailto
      const WEBHOOK_URL = 'https://siteforge-bot.onrender.com/webhook';

      fetch(WEBHOOK_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      }).catch(function () {
        const subject = encodeURIComponent('Заявка: сайт за 1000₽ — SiteForge AI');
        const body = encodeURIComponent(
          'Новая заявка на сайт за 1000₽\n\n' +
          'Имя: ' + name + '\n' +
          'Телефон: ' + phone + '\n' +
          'Email: ' + (email || 'не указан') + '\n\n' +
          'Описание сайта:\n' + description + '\n\n' +
          '---\nОтправлено с siteforge-ai.ru'
        );
        window.location.href = 'mailto:flash83@list.ru?subject=' + subject + '&body=' + body;
      });

      if (modal) {
        modal.classList.add('open');
        modal.setAttribute('aria-hidden', 'false');
      }

      form.reset();
    });
  }

  if (closeModal && modal) {
    closeModal.addEventListener('click', () => {
      modal.classList.remove('open');
      modal.setAttribute('aria-hidden', 'true');
    });

    modal.querySelector('.modal-overlay')?.addEventListener('click', () => {
      modal.classList.remove('open');
      modal.setAttribute('aria-hidden', 'true');
    });
  }

  // ===== Smooth anchor offset for fixed header =====
  document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
      const targetId = this.getAttribute('href');
      if (targetId === '#') return;
      const target = document.querySelector(targetId);
      if (!target) return;
      e.preventDefault();
      const offset = 120;
      const top = target.getBoundingClientRect().top + window.scrollY - offset;
      window.scrollTo({ top, behavior: 'smooth' });
    });
  });
})();
