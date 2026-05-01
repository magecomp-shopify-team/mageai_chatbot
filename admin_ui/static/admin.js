/* ── Toast notifications ─────────────────────────────────────────────────── */
function toast(message, type = 'info', duration = 4000) {
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    document.body.appendChild(container);
  }

  const icons = {
    success: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>`,
    error:   `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>`,
    info:    `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>`,
  };

  const colorMap = { success: '#10B981', error: '#EF4444', info: '#6366F1' };

  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.style.color = colorMap[type] || colorMap.info;
  el.innerHTML = `${icons[type] || icons.info}<span style="color:#E2E8F0;flex:1">${message}</span>`;

  container.appendChild(el);

  setTimeout(() => {
    el.classList.add('closing');
    setTimeout(() => el.remove(), 260);
  }, duration);
}

/* ── Modal helpers ───────────────────────────────────────────────────────── */
function openModal(id) {
  const el = document.getElementById(id);
  if (!el) return;
  el.style.display = 'flex';
}

function closeModal(id) {
  const el = document.getElementById(id);
  if (!el) return;
  el.style.display = 'none';
}

/* Escape key closes any open modal */
document.addEventListener('keydown', e => {
  if (e.key !== 'Escape') return;
  document.querySelectorAll('.modal-overlay').forEach(el => {
    if (el.style.display === 'flex') el.style.display = 'none';
  });
});

/* ── Drawer ──────────────────────────────────────────────────────────────── */
function openDrawerEl() {
  document.getElementById('drawerOverlay').style.display = 'block';
  document.getElementById('sessionDrawer').style.display = 'flex';
}

function closeDrawer() {
  document.getElementById('drawerOverlay').style.display = 'none';
  document.getElementById('sessionDrawer').style.display = 'none';
}

/* ── HTML escape ─────────────────────────────────────────────────────────── */
function esc(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

/* ── Auto-dismiss alerts ─────────────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.alert').forEach(el => {
    // Skip error divs that live inside modals — they are reused across opens
    // and must not be removed from the DOM.
    if (el.closest('.modal-overlay')) return;
    setTimeout(() => {
      el.style.transition = 'opacity 0.4s';
      el.style.opacity = '0';
      setTimeout(() => el.remove(), 400);
    }, 5000);
  });
});

/* ── Confirm dialog helper ───────────────────────────────────────────────── */
function confirmAction(msg, onConfirm) {
  if (confirm(msg)) onConfirm();
}

/* ── Cookie helper ───────────────────────────────────────────────────────── */
function getCookie(name) {
  return document.cookie.split(';')
    .map(c => c.trim())
    .find(c => c.startsWith(name + '='))
    ?.split('=')[1] || '';
}
