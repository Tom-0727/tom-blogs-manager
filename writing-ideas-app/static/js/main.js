// main.js — top-level router. Watches the URL hash, lazy-imports the active tab,
// calls its mount/unmount lifecycle, and updates the unread-badge count on tab buttons.

import { api } from './api.js';

const TABS = {
  ideas:    { module: '/static/js/tabs/ideas.js' },
  writings: { module: '/static/js/tabs/writings.js' },
};

const DEFAULT_TAB = 'ideas';
let currentTab = null;
let currentMod = null;

function tabFromHash() {
  // The hash may carry a sub-route like "#writings/draft" — only the segment
  // before the first "/" identifies the active tab.
  const h = (location.hash || '').replace(/^#/, '').split('/')[0];
  return TABS[h] ? h : DEFAULT_TAB;
}

async function showTab(name) {
  if (!TABS[name]) name = DEFAULT_TAB;
  if (currentTab === name) return;

  // Unmount previous
  if (currentMod && typeof currentMod.unmount === 'function') {
    try { currentMod.unmount(); } catch (e) { console.error('unmount error', e); }
  }

  // Update tab-bar visual state
  document.querySelectorAll('.tab-btn').forEach((b) => {
    b.classList.toggle('active', b.getAttribute('data-tab') === name);
  });

  // Lazy import + mount
  const mod = await import(TABS[name].module);
  currentMod = mod;
  currentTab = name;
  const root = document.getElementById('content');
  await mod.mount(root);
}

async function refreshBadges() {
  // The writings tab badge counts feedback the AGENT has not yet
  // incorporated for the current stage of each writing.
  try {
    const data = await api.writings();
    const total = (data.writings || []).reduce((s, w) => s + (w.agent_pending_feedback || 0), 0);
    const btn = document.querySelector('.tab-btn[data-tab="writings"]');
    if (!btn) return;
    btn.querySelectorAll('.tab-badge').forEach((el) => el.remove());
    if (total > 0) {
      const span = document.createElement('span');
      span.className = 'tab-badge';
      span.textContent = String(total);
      btn.appendChild(span);
    }
  } catch (_) { /* tolerate */ }
}

function bindTabClicks() {
  document.querySelectorAll('.tab-btn').forEach((b) => {
    b.addEventListener('click', () => {
      const name = b.getAttribute('data-tab');
      // Drop any sub-route when switching tabs from the top bar.
      if (location.hash !== '#' + name) location.hash = '#' + name;
    });
  });
  window.addEventListener('hashchange', () => showTab(tabFromHash()));
}

(async () => {
  bindTabClicks();
  await showTab(tabFromHash());
  await refreshBadges();
  setInterval(refreshBadges, 30 * 1000); // poll badge counts every 30s
})();
