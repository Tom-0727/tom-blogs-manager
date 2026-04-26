// tabs/ideas.js — Ideas tab module.

import { api } from '../api.js';
import { ensureCss, escapeHtml, loadHtmlFragment } from '../ui.js';

const DIM_LABELS = {
  audience_reach: '受众覆盖',
  distribution_potential: '传播潜力',
  author_differentiation: '作者独特性',
  timeliness: '时效性',
  series_potential: '系列化',
};
const REC_LABELS = { strong: '强烈推荐', moderate: '值得考虑', weak: '优先级低' };

let state = { allData: null, activeDate: 'all' };
let rootEl = null;

function renderIdea(idea) {
  const s = idea.scores || {};
  const dims = Object.entries(DIM_LABELS).map(([k, label]) => {
    const val = s[k] || 0;
    const color = val >= 4 ? '#186246' : val >= 3 ? '#856404' : '#6c757d';
    return `<div class="dim"><div class="dim-label">${label}</div><div class="dim-val" style="color:${color}">${val}</div></div>`;
  }).join('');
  const total = s.total || 0;
  return `
    <div class="card idea-card">
      <div class="idea-header">
        <div class="idea-title"><a href="${escapeHtml(idea.url)}" target="_blank" rel="noopener">${escapeHtml(idea.title)}</a></div>
        <span class="badge ${idea.recommendation}">${REC_LABELS[idea.recommendation] || idea.recommendation || ''}</span>
      </div>
      <div style="display:flex;align-items:baseline;gap:8px">
        <span class="score-total">${total}</span><span class="score-max">/ 25</span>
        <span style="font-size:12px;color:var(--muted)">${escapeHtml(idea.date || '')}</span>
      </div>
      <div class="score-bar">${dims}</div>
      <div class="angle">${escapeHtml(idea.suggested_angle || '')}</div>
      <div class="idea-meta">
        <span class="tag">${escapeHtml(idea.content_line || '')}</span>
        <span>来源: ${escapeHtml(idea.source || '')}</span>
      </div>
    </div>`;
}

function renderDateFilter(dates) {
  const f = rootEl.querySelector('#dateFilter');
  let h = `<button class="date-btn ${state.activeDate === 'all' ? 'active' : ''}" data-date="all">全部</button>`;
  for (const d of dates) {
    h += `<button class="date-btn ${state.activeDate === d ? 'active' : ''}" data-date="${escapeHtml(d)}">${escapeHtml(d)}</button>`;
  }
  f.innerHTML = h;
  f.querySelectorAll('.date-btn').forEach((b) => {
    b.addEventListener('click', () => setDate(b.getAttribute('data-date')));
  });
}

function renderIdeas(ideas) {
  const list = rootEl.querySelector('#ideasList');
  if (!ideas || !ideas.length) {
    list.innerHTML = '<div class="empty">该日期暂无选题推荐</div>';
    return;
  }
  const groups = { strong: [], moderate: [], weak: [] };
  ideas.forEach((i) => (groups[i.recommendation] || groups.weak).push(i));
  let h = '';
  if (groups.strong.length)   h += '<div class="section-label">强烈推荐</div>' + groups.strong.map(renderIdea).join('');
  if (groups.moderate.length) h += '<div class="section-label">值得考虑</div>' + groups.moderate.map(renderIdea).join('');
  if (groups.weak.length)     h += '<div class="section-label">优先级低</div>' + groups.weak.map(renderIdea).join('');
  list.innerHTML = h;
}

function setDate(d) {
  state.activeDate = d;
  if (!state.allData) return;
  renderDateFilter(state.allData.dates || []);
  const filtered = state.activeDate === 'all'
    ? state.allData.ideas
    : (state.allData.ideas || []).filter((i) => i.date === state.activeDate);
  renderIdeas(filtered);
}

async function refresh() {
  try {
    state.allData = await api.ideas();
    renderDateFilter(state.allData.dates || []);
    renderIdeas(state.allData.ideas || []);
    rootEl.querySelector('#genMeta').textContent =
      `更新时间: ${state.allData.generated_at || '未知'} | 保留最近7天`;
  } catch (e) {
    rootEl.querySelector('#ideasList').innerHTML = '<div class="empty">加载失败</div>';
  }
}

export async function mount(root) {
  ensureCss('/static/css/ideas.css');
  rootEl = root;
  rootEl.innerHTML = await loadHtmlFragment('/static/html/ideas.html');
  state = { allData: null, activeDate: 'all' };
  await refresh();
}

export function unmount() {
  rootEl = null;
  state = { allData: null, activeDate: 'all' };
}
