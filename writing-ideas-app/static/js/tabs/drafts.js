// tabs/drafts.js — Drafts tab module (in-line editor + list).

import { api } from '../api.js';
import { ensureCss, escapeHtml, fmtTime, loadHtmlFragment, toast } from '../ui.js';

const STATUS_LABELS = { draft: '草稿中', review: '待审阅', approved: '已通过', published: '已发布' };

let rootEl = null;
let easyMDE = null;
let currentId = null;

function showList() {
  rootEl.querySelector('#draftsListView').style.display = 'block';
  rootEl.querySelector('#draftsEditorView').style.display = 'none';
  if (easyMDE) { easyMDE.toTextArea(); easyMDE = null; }
  currentId = null;
}

function showEditor() {
  rootEl.querySelector('#draftsListView').style.display = 'none';
  rootEl.querySelector('#draftsEditorView').style.display = 'block';
}

async function loadList() {
  try {
    const data = await api.drafts();
    const drafts = data.drafts || [];
    rootEl.querySelector('#draftCount').textContent = `共 ${drafts.length} 篇草稿`;
    if (!drafts.length) {
      rootEl.querySelector('#draftsList').innerHTML =
        '<div class="empty">暂无草稿<br/><span style="font-size:13px;color:var(--muted)">Tom-Blogs-Manager 写完文章后会出现在这里</span></div>';
      return;
    }
    rootEl.querySelector('#draftsList').innerHTML = drafts.map((d) => `
      <div class="card draft-card" data-id="${escapeHtml(d.id)}">
        <div class="draft-header">
          <div class="draft-title">${escapeHtml(d.title)}</div>
          <span class="status-badge ${escapeHtml(d.status)}">${STATUS_LABELS[d.status] || d.status}</span>
        </div>
        <div class="draft-time">创建: ${fmtTime(d.created_at)} &nbsp;|&nbsp; 更新: ${fmtTime(d.updated_at)}</div>
      </div>
    `).join('');
    rootEl.querySelectorAll('.draft-card').forEach((c) => {
      c.addEventListener('click', () => openDraft(c.getAttribute('data-id')));
    });
  } catch (e) {
    rootEl.querySelector('#draftsList').innerHTML = '<div class="empty">加载失败</div>';
  }
}

async function openDraft(id) {
  try {
    const draft = await api.draft(id);
    currentId = id;
    rootEl.querySelector('#draftTitle').value = draft.title;
    rootEl.querySelector('#statusSelect').value = draft.status;
    rootEl.querySelector('#draftMeta').textContent = `创建: ${fmtTime(draft.created_at)} | 更新: ${fmtTime(draft.updated_at)}`;
    rootEl.querySelector('#saveStatus').textContent = '';
    showEditor();
    if (easyMDE) { easyMDE.toTextArea(); easyMDE = null; }
    easyMDE = new EasyMDE({
      element: rootEl.querySelector('#draftEditor'),
      initialValue: draft.content || '',
      spellChecker: false,
      autofocus: true,
      minHeight: '400px',
      placeholder: '在此编辑文章内容 (Markdown)...',
      status: ['lines', 'words'],
      toolbar: [
        'bold', 'italic', 'heading', '|',
        'quote', 'unordered-list', 'ordered-list', '|',
        'link', 'image', 'code', '|',
        'preview', 'side-by-side', 'fullscreen', '|',
        'guide',
      ],
      renderingConfig: { markedOptions: { breaks: true } },
    });
  } catch (e) {
    toast('打开草稿失败');
  }
}

async function saveDraft() {
  if (!currentId || !easyMDE) return;
  const body = {
    title: rootEl.querySelector('#draftTitle').value,
    content: easyMDE.value(),
    status: rootEl.querySelector('#statusSelect').value,
  };
  try {
    const meta = await api.draftUpdate(currentId, body);
    rootEl.querySelector('#draftMeta').textContent = `创建: ${fmtTime(meta.created_at)} | 更新: ${fmtTime(meta.updated_at)}`;
    rootEl.querySelector('#saveStatus').textContent = '已保存 ✓';
    setTimeout(() => { rootEl.querySelector('#saveStatus').textContent = ''; }, 2000);
  } catch (e) {
    rootEl.querySelector('#saveStatus').textContent = '保存失败';
  }
}

async function deleteDraft() {
  if (!currentId) return;
  if (!confirm('确定删除这篇草稿？')) return;
  try {
    await api.draftDelete(currentId);
    showList();
    await loadList();
  } catch (e) { toast('删除失败'); }
}

function bindEvents() {
  rootEl.querySelector('[data-action="back"]').addEventListener('click', () => {
    showList();
    loadList();
  });
  rootEl.querySelector('[data-action="save"]').addEventListener('click', saveDraft);
  rootEl.querySelector('[data-action="delete"]').addEventListener('click', deleteDraft);
  rootEl.querySelector('#statusSelect').addEventListener('change', saveDraft);
}

export async function mount(root) {
  ensureCss('/static/css/drafts.css');
  rootEl = root;
  rootEl.innerHTML = await loadHtmlFragment('/static/html/drafts.html');
  bindEvents();
  showList();
  await loadList();
}

export function unmount() {
  if (easyMDE) { easyMDE.toTextArea(); easyMDE = null; }
  rootEl = null;
  currentId = null;
}
