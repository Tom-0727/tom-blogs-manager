// tabs/writings.js — Writings tab module.
// List view: one sub-tab per stage; click to filter cards.
// Detail view: stage tabs + feedback panel; agent_pending field drives the badges.

import { api } from '../api.js';
import { ensureCss, escapeHtml, fmtTime, loadHtmlFragment, toast } from '../ui.js';

const STAGE_ORDER = ['idea', 'outline', 'draft', 'approved', 'published'];
const STAGE_LABELS = {
  idea: 'idea',
  outline: 'outline',
  draft: 'draft',
  approved: 'approved',
  published: 'published',
};
const STAGE_HINT = {
  idea: '等待 agent 出大纲',
  outline: '待你 approve',
  draft: '待你 approve',
  approved: '等待发布',
  published: '已发布',
};

let rootEl = null;
let allWritings = [];
let activeStage = null;
let currentSlug = null;
let currentDetail = null;
let currentStageTab = null;

function showList() {
  rootEl.querySelector('#writingsListView').style.display = 'block';
  rootEl.querySelector('#writingsDetailView').style.display = 'none';
  currentSlug = null;
  currentDetail = null;
  currentStageTab = null;
}

function showDetail() {
  rootEl.querySelector('#writingsListView').style.display = 'none';
  rootEl.querySelector('#writingsDetailView').style.display = 'block';
}

// ── List view ──────────────────────────────────────────────────

function _stageFromHash() {
  const h = (location.hash || '').replace(/^#/, '');
  // Expected format: writings/<stage> or writings
  const parts = h.split('/');
  if (parts[0] === 'writings' && parts[1] && STAGE_ORDER.includes(parts[1])) {
    return parts[1];
  }
  return null;
}

function _writeStageHash(stage) {
  const next = stage ? `#writings/${stage}` : '#writings';
  if (location.hash !== next) location.hash = next;
}

function _autoPickStage(writings) {
  // 1. If any stage has pending agent feedback, jump there.
  for (const s of STAGE_ORDER) {
    const items = writings.filter((w) => w.stage === s);
    if (items.some((w) => (w.agent_pending_feedback || 0) > 0)) return s;
  }
  // 2. Else first non-empty stage in order, ignoring published.
  for (const s of STAGE_ORDER) {
    if (s === 'published') continue;
    if (writings.some((w) => w.stage === s)) return s;
  }
  // 3. Default to idea.
  return 'idea';
}

function renderSubtabs() {
  const counts = Object.fromEntries(STAGE_ORDER.map((s) => [s, 0]));
  const pending = Object.fromEntries(STAGE_ORDER.map((s) => [s, 0]));
  for (const w of allWritings) {
    counts[w.stage] = (counts[w.stage] || 0) + 1;
    pending[w.stage] = (pending[w.stage] || 0) + (w.agent_pending_feedback || 0);
  }
  const html = STAGE_ORDER.map((s) => `
    <button class="stage-subtab-btn ${activeStage === s ? 'active' : ''}" data-stage="${s}">
      <span>${STAGE_LABELS[s]}</span>
      <span class="count">${counts[s] || 0}</span>
      ${pending[s] > 0 ? '<span class="pending-dot" title="agent 有未处理反馈"></span>' : ''}
    </button>
  `).join('');
  rootEl.querySelector('#stageSubtabs').innerHTML = html;
  rootEl.querySelectorAll('.stage-subtab-btn').forEach((b) => {
    b.addEventListener('click', () => {
      activeStage = b.getAttribute('data-stage');
      _writeStageHash(activeStage);
      renderSubtabs();
      renderGrid();
    });
  });
}

function renderGrid() {
  const grid = rootEl.querySelector('#writingsGrid');
  const items = allWritings.filter((w) => w.stage === activeStage);
  if (!items.length) {
    grid.innerHTML = `<div class="empty">${activeStage} 阶段当前没有 writing</div>`;
    return;
  }
  grid.innerHTML = items.map((w) => `
    <div class="writing-card" data-slug="${escapeHtml(w.slug)}">
      ${(w.agent_pending_feedback || 0) > 0
        ? `<span class="unread-dot" title="agent 有 ${w.agent_pending_feedback} 条未处理反馈"></span>` : ''}
      <div class="writing-card-title">${escapeHtml(w.title)}</div>
      <div class="writing-card-meta">
        <span>${fmtTime(w.updated_at)}</span>
        <span>${(w.agent_pending_feedback || 0) > 0
          ? `${w.agent_pending_feedback} 条待处理` : STAGE_HINT[w.stage] || ''}</span>
      </div>
    </div>
  `).join('');
  rootEl.querySelectorAll('.writing-card').forEach((c) => {
    c.addEventListener('click', () => openWriting(c.getAttribute('data-slug')));
  });
}

async function loadList() {
  try {
    const data = await api.writings();
    allWritings = data.writings || [];
    if (!activeStage) {
      activeStage = _stageFromHash() || _autoPickStage(allWritings);
      _writeStageHash(activeStage);
    }
    renderSubtabs();
    renderGrid();
  } catch (e) {
    rootEl.querySelector('#writingsGrid').innerHTML = '<div class="empty">加载失败</div>';
  }
}

// ── Detail view ────────────────────────────────────────────────

async function openWriting(slug) {
  try {
    currentDetail = await api.writing(slug);
    currentSlug = slug;
    showDetail();
    renderDetail();
  } catch (e) {
    toast('打开失败：' + (e.message || ''));
  }
}

function renderDetail() {
  const d = currentDetail;
  rootEl.querySelector('#detailTitle').textContent = (d.meta && d.meta.title) || d.slug;
  const stage = (d.status && d.status.stage) || 'idea';
  const stageBadge = `<span class="writing-stage-badge ${stage}">${STAGE_LABELS[stage] || stage}</span>`;
  const tags = (d.meta && d.meta.tags) || [];
  const cat = (d.meta && d.meta.category) || '';
  const tagsHtml = tags.map((t) => `<span class="tag">${escapeHtml(t)}</span>`).join(' ');
  const lastErr = (d.status && d.status.last_error)
    ? `<span style="color:var(--danger-fg);margin-left:8px">⚠ ${escapeHtml(d.status.last_error)}</span>` : '';
  rootEl.querySelector('#detailMeta').innerHTML =
    `${stageBadge}${cat ? `<span class="tag">${escapeHtml(cat)}</span> ` : ''}${tagsHtml}${lastErr}`;

  // Stage tabs (within the detail panel — show available product stages)
  const presentStages = ['idea', 'outline', 'draft'].filter((s) => (d.stages || {}).hasOwnProperty(s));
  if (!currentStageTab || !presentStages.includes(currentStageTab)) {
    currentStageTab = presentStages[presentStages.length - 1] || 'idea';
  }
  const tabsHtml = ['idea', 'outline', 'draft'].map((s) => {
    const exists = (d.stages || {}).hasOwnProperty(s);
    return `<button class="stage-tab-btn ${currentStageTab === s ? 'active' : ''}" data-stage="${s}" ${exists ? '' : 'disabled'}>${s}</button>`;
  }).join('');
  rootEl.querySelector('#stageTabs').innerHTML = tabsHtml;
  rootEl.querySelectorAll('.stage-tab-btn').forEach((b) => {
    b.addEventListener('click', () => {
      if (b.disabled) return;
      currentStageTab = b.getAttribute('data-stage');
      renderDetail();
    });
  });
  rootEl.querySelector('#stageContent').textContent = (d.stages || {})[currentStageTab] || '(空)';

  // Approve row
  const approveRow = rootEl.querySelector('#approveRow');
  approveRow.innerHTML = '';
  if (stage === 'outline') {
    approveRow.innerHTML = '<button class="btn btn-primary" data-approve="outline">通过 outline → 让 agent 写 draft</button>';
  } else if (stage === 'draft') {
    approveRow.innerHTML = '<button class="btn btn-primary" data-approve="draft">通过 draft → 进入 approved</button>';
  } else if (stage === 'approved') {
    approveRow.innerHTML = '<span class="meta">已通过，等待 agent 在下一次 heartbeat 发布。</span>';
  } else if (stage === 'published') {
    const path = d.status.published_path || '';
    approveRow.innerHTML = `<span class="meta">已发布于 ${escapeHtml(path)}</span>`;
  } else {
    approveRow.innerHTML = '<span class="meta">等待 agent 在下一次 heartbeat 出大纲。</span>';
  }
  approveRow.querySelectorAll('[data-approve]').forEach((b) => {
    b.addEventListener('click', () => approve(b.getAttribute('data-approve')));
  });

  // Publish button only when in approved
  const publishBtn = rootEl.querySelector('#publishBtn');
  publishBtn.style.display = (stage === 'approved') ? 'inline-block' : 'none';

  // Feedback list (newest first; agent_pending entries highlighted)
  const fb = (d.feedback || []).slice().reverse();
  rootEl.querySelector('#feedbackList').innerHTML = fb.map((f) => `
    <div class="feedback-item ${f.agent_pending ? 'unread' : ''}">
      <div class="feedback-item-meta">
        <span>${escapeHtml(f.stage || '')}${f.agent_pending ? ' · agent 待处理' : ''}</span>
        <span>${fmtTime(f.ts)}</span>
      </div>
      <div>${escapeHtml(f.text || '')}</div>
    </div>
  `).join('') || '<div class="meta" style="font-size:12px">暂无反馈</div>';
}

async function approve(stage) {
  try {
    await api.writingApprove(currentSlug, stage);
    toast('已通过 ' + stage);
    currentDetail = await api.writing(currentSlug);
    renderDetail();
  } catch (e) {
    toast('approve 失败：' + (e.message || ''));
  }
}

async function submitFeedback() {
  const ta = rootEl.querySelector('#feedbackInput');
  const text = ta.value.trim();
  if (!text) { toast('请输入反馈内容'); return; }
  try {
    await api.writingFeedback(currentSlug, text);
    ta.value = '';
    currentDetail = await api.writing(currentSlug);
    renderDetail();
    toast('反馈已记录');
  } catch (e) {
    toast('反馈失败：' + (e.message || ''));
  }
}

async function publishWriting() {
  const cat = (currentDetail.meta && currentDetail.meta.category) || '';
  const map = {
    'Agent Engineering': 'agent-engineering',
    'Agent Product': 'agent-product',
    'ResearcherZero': 'researcher-zero',
    'Demo': 'demos',
  };
  let sub = map[cat];
  if (sub === undefined) {
    sub = prompt('发布到哪个子目录？(例如 agent-engineering, 留空则放在 _posts 根目录)', '');
    if (sub === null) return; // cancelled
  }
  if (!confirm(`确认发布到 tom-ai-lab-blogs/source/_posts/${sub}/${currentSlug}.md ？`)) return;
  try {
    const out = await api.writingPublish(currentSlug, sub);
    toast('已发布：' + (out.published_path || ''));
    currentDetail = await api.writing(currentSlug);
    renderDetail();
    await loadList();
  } catch (e) {
    toast('发布失败：' + (e.message || ''));
  }
}

async function deleteWriting() {
  if (!confirm('删除这篇 writing？目录会被清空，无法恢复。')) return;
  try {
    await api.writingDelete(currentSlug);
    showList();
    activeStage = null; // re-pick after deletion
    await loadList();
  } catch (e) {
    toast('删除失败：' + (e.message || ''));
  }
}

// ── New writing modal ──────────────────────────────────────────

function openNewModal() {
  rootEl.querySelector('#newWritingModal').classList.add('show');
  rootEl.querySelector('#newTitle').focus();
}
function closeNewModal() {
  rootEl.querySelector('#newWritingModal').classList.remove('show');
  rootEl.querySelector('#newTitle').value = '';
  rootEl.querySelector('#newIdea').value = '';
  rootEl.querySelector('#newRef').value = '';
}
async function confirmNew() {
  const title = rootEl.querySelector('#newTitle').value.trim();
  const idea = rootEl.querySelector('#newIdea').value.trim();
  const ref = rootEl.querySelector('#newRef').value.trim();
  if (!title) { toast('请填写标题'); return; }
  try {
    const meta = await api.writingCreate({ title, idea, reference_link: ref || null });
    closeNewModal();
    activeStage = 'idea';
    _writeStageHash(activeStage);
    await loadList();
    await openWriting(meta.slug);
  } catch (e) {
    toast('创建失败：' + (e.message || ''));
  }
}

// ── Wiring ─────────────────────────────────────────────────────

function bindEvents() {
  rootEl.querySelector('[data-action="new"]').addEventListener('click', openNewModal);
  rootEl.querySelector('[data-action="back"]').addEventListener('click', () => {
    showList();
    loadList();
  });
  rootEl.querySelector('[data-action="delete"]').addEventListener('click', deleteWriting);
  rootEl.querySelector('[data-action="publish"]').addEventListener('click', publishWriting);
  rootEl.querySelector('[data-action="feedback"]').addEventListener('click', submitFeedback);
  // Modal
  const modal = rootEl.querySelector('#newWritingModal');
  modal.querySelector('[data-action="cancel"]').addEventListener('click', closeNewModal);
  modal.querySelector('[data-action="confirm"]').addEventListener('click', confirmNew);
  modal.addEventListener('click', (e) => { if (e.target === modal) closeNewModal(); });
}

export async function mount(root) {
  ensureCss('/static/css/writings.css');
  rootEl = root;
  rootEl.innerHTML = await loadHtmlFragment('/static/html/writings.html');
  bindEvents();
  showList();
  // Pre-pick from hash so a refresh on #writings/draft restores the right tab
  const hashStage = _stageFromHash();
  if (hashStage) activeStage = hashStage;
  await loadList();
}

export function unmount() {
  rootEl = null;
  allWritings = [];
  activeStage = null;
  currentSlug = null;
  currentDetail = null;
  currentStageTab = null;
}
