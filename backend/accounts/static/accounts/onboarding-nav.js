/**
 * Full-page navigation overlay for onboarding transitions.
 */
(function () {
  const OVERLAY_ID = 'ws-nav-overlay';
  const DEFAULT_DELAY = 480;
  const DEFAULT_ENTER_HOLD = 540;

  function ensureOverlay() {
    let el = document.getElementById(OVERLAY_ID);
    if (el) return el;

    el = document.createElement('div');
    el.id = OVERLAY_ID;
    el.className = 'ws-nav-overlay';
    el.setAttribute('role', 'status');
    el.setAttribute('aria-live', 'polite');
    el.innerHTML = `
      <div class="ws-nav-overlay-card">
        <div class="ws-nav-spinner" aria-hidden="true"></div>
        <p class="ws-nav-message"></p>
      </div>`;
    document.body.appendChild(el);
    return el;
  }

  function show(message) {
    const overlay = ensureOverlay();
    overlay.querySelector('.ws-nav-message').textContent = message || '이동하는 중…';
    requestAnimationFrame(() => overlay.classList.add('visible'));
    document.body.classList.add('ws-nav-active');
  }

  function hide() {
    const overlay = document.getElementById(OVERLAY_ID);
    if (!overlay) return;
    overlay.classList.remove('visible');
    document.body.classList.remove('ws-nav-active');
  }

  function go(message, url, delayMs) {
    const delay = typeof delayMs === 'number' ? delayMs : DEFAULT_DELAY;
    show(message);
    window.setTimeout(() => {
      window.location.href = url;
    }, delay);
  }

  function enterThenRun(message, callback, holdMs) {
    if (!message) {
      if (callback) callback();
      return;
    }
    show(message);
    window.setTimeout(() => {
      hide();
      if (callback) callback();
    }, typeof holdMs === 'number' ? holdMs : DEFAULT_ENTER_HOLD);
  }

  window.WhatSubNav = {
    show,
    hide,
    go,
    enterThenRun,
  };
})();
