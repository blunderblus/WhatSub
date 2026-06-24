export function showOnboardingNav(message) {
  let overlay = document.getElementById('ws-nav-overlay');
  if (!overlay) {
    overlay = document.createElement('div');
    overlay.id = 'ws-nav-overlay';
    overlay.className = 'ws-nav-overlay';
    overlay.setAttribute('role', 'status');
    overlay.setAttribute('aria-live', 'polite');
    overlay.innerHTML = `
      <div class="ws-nav-overlay-card">
        <div class="ws-nav-spinner" aria-hidden="true"></div>
        <p class="ws-nav-message"></p>
      </div>`;
    document.body.appendChild(overlay);

    if (!document.getElementById('ws-nav-overlay-styles')) {
      const style = document.createElement('style');
      style.id = 'ws-nav-overlay-styles';
      style.textContent = `
        body.ws-nav-active { overflow: hidden; }
        .ws-nav-overlay {
          position: fixed; inset: 0; z-index: 9999; display: grid; place-items: center;
          padding: 24px; background: rgba(0,0,0,0.72); backdrop-filter: blur(8px);
          opacity: 0; visibility: hidden; transition: opacity 0.28s ease, visibility 0.28s ease;
        }
        .ws-nav-overlay.visible { opacity: 1; visibility: visible; }
        .ws-nav-overlay-card {
          width: min(360px, 100%); padding: 28px 24px;
          border: 1px solid rgba(217,221,146,0.28); border-radius: 18px;
          background: linear-gradient(180deg, #1c2a43, #14213d);
          box-shadow: 0 24px 48px rgba(0,0,0,0.45); text-align: center;
        }
        .ws-nav-spinner {
          width: 42px; height: 42px; margin: 0 auto 16px;
          border: 3px solid rgba(217,221,146,0.18); border-top-color: #D9DD92;
          border-radius: 50%; animation: wsNavSpin 0.85s linear infinite;
        }
        .ws-nav-message { margin: 0; color: #fff; font-size: 16px; font-weight: 800; line-height: 1.5; }
        @keyframes wsNavSpin { to { transform: rotate(360deg); } }
      `;
      document.head.appendChild(style);
    }
  }

  overlay.querySelector('.ws-nav-message').textContent = message || '이동하는 중…';
  requestAnimationFrame(() => overlay.classList.add('visible'));
  document.body.classList.add('ws-nav-active');
}

export function navigateWithOnboardingNav(url, message, delayMs = 480) {
  showOnboardingNav(message);
  window.setTimeout(() => {
    window.location.href = url;
  }, delayMs);
}
