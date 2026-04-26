// tabs/writings.js — Writings tab module (state-machine cards + detail view + feedback flow).

import { api } from '../api.js';
import { ensureCss, escapeHtml, fmtTime, loadHtmlFragment, toast } from '../ui.js';

const STAGE_ORDER = ['idea', 'outline', 'draft', 'approved', 'published'];
const STAGE_LABELS = {
  idea: 'idea (等待 agent 出大纲)',
  outline: '大纲 (待你 approve)',
  draft: '草稿 (待你 approve)',
  approved: '已通过 (等待发布)',
  published: '已发布',
};
const STAGE_BADGE_LABEL = {
  idea: 'idea',
  outline: 'outline',
  draft: 'draft',
  approved: 'approved',
  published: 'published',
};

let rootEl = null;
let currentSlug = null;
let currentDetail = null;
let currentStageTab = null; // which stage's content is shown in detail view

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

function renderStageCards(writings) {
  const cols = STAGE_ORDER.map((stage) => {
    const items = writings.filter((w) => w.stage === stage);
    const cards = items.map((w) => `
      <div class="writing-card" data-slug="${escapeHtml(w.slug)}">
        ${w.unread_feedback > 0 ? '<span class="unread-dot" title="有未读反馈"></span>' : ''}
        <div class="writing-card-title">${escapeHtml(w.title)}</div>
        <div class="writing-card-meta">
          <span>${fmtTime(w.updated_at)}</span>
          <span>${w.unread_feedback > 0 ? `${w.unread_feedback} 条未读` : ''}</span>
        </div>
      </div>
    `).join('');
    return `
      <div class="stage-col">
        <div class="stage-col-header">
          <span>${STAGE_LABELS[stage]}</span>
          <span class="stage-col-count">${items.length}</span>
        </div>
        ${cards || '<div class="meta" style="font-size:12px;padding:6px 4px;">空</div>'}
      </div>
    `;
  }).join('');
  rootEl.querySelector('#stageColumns').innerHTML = cols;
  rootEl.querySelectorAll('.writing-card').forEach((c) => {
    c.addEventListener('click', () => openWriting(c.getAttribute('data-slug')));
  });
}

async function loadList() {
  try {
    const data = await api.writings();
    const writings = data.writings || [];
    rootEl.querySelector('#writingsCount').textContent =
      `共 ${writings.length} 篇 | 未读反馈 ${writings.reduce((s, w) => s + (w.unread_feedback || 0), 0)} 条`;
    renderStageCards(writings);
  } catch (e) {
    rootEl.querySelector('#stageColumns').innerHTML = '<div class="empty">加载失败</div>';
  }
}

async function openWriting(slug) {
  try {
    currentDetail = await api.writing(slug);
    currentSlug = slug;
    showDetail();
    renderDetail();
    // Mark feedback as read on view
    try { await api.writingMarkRead(slug); } catch (_) { /* non-blocking */ }
  } catch (e) {
    toast('打开失败：' + (e.message || ''));
  }
}

function renderDetail() {
  const d = currentDetail;
  rootEl.querySelector('#detailTitle').textContent = (d.meta && d.meta.title) || d.slug;
  const stage = (d.status && d.status.stage) || 'idea';
  const stageBadge = `<span class="writing-stage-badge ${stage}">${STAGE_BADGE_LABEL[stage] || stage}</span>`;
  const tags = (d.meta && d.meta.tags) || [];
  const cat = (d.meta && d.meta.category) || '';
  const tagsHtml = tags.map((t) => `<span class="tag">${escapeHtml(t)}</span>`).join(' ');
  const lastErr = (d.status && d.status.last_error) ? `<span style="color:var(--danger-fg);margin-left:8px">⚠ ${escapeHtml(d.status.last_error)}</span>` : '';
  rootEl.querySelector('#detailMeta').innerHTML =
    `${stageBadge}${cat ? `<span class="tag">${escapeHtml(cat)}</span> ` : ''}${tagsHtml}${lastErr}`;

  // Stage tabs
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

  // Feedback list (newest first)
  const fb = (d.feedback || []).slice().reverse();
  rootEl.querySelector('#feedbackList').innerHTML = fb.map((f) => `
    <div class="feedback-item ${f.unread ? 'unread' : ''}">
      <div class="feedback-item-meta">
        <span>${escapeHtml(f.stage || '')}</span>
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
  // Infer target subdir from the active category-to-folder mapping; fallback to none
  const cat = (currentDetail.meta && currentDetail.meta.category) || '';
  const map = {
    'Agent Engineering': 'agent-engineering',
    'Agent Product': 'agent-product',
    'ResearcherZero': 'researcher-zero',
    'Demo': 'demos',
  };
  const sub = map[cat] || prompt('发布到哪个子目录？(例如 agent-engineering, 留空则放在 _posts 根目录)', '') || '';
  if (sub === null) return;
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
    await loadList();
  } catch (e) {
    toast('删除失败：' + (e.message || ''));
  }
}

// New writing modal
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
    await loadList();
    await openWriting(meta.slug);
  } catch (e) {
    toast('创建失败：' + (e.message || ''));
  }
}

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
  await loadList();
}

export function unmount() {
  rootEl = null;
  currentSlug = null;
  currentDetail = null;
  currentStageTab = null;
}
