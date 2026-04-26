// api.js — central fetch wrapper with consistent error handling.

async function _request(method, path, body) {
  const opts = { method, headers: {} };
  if (body !== undefined) {
    opts.headers['Content-Type'] = 'application/json';
    opts.body = JSON.stringify(body);
  }
  const resp = await fetch(path, opts);
  let payload = null;
  try {
    payload = await resp.json();
  } catch (_) {
    payload = null;
  }
  if (!resp.ok) {
    const detail = payload && (payload.detail || payload.message || JSON.stringify(payload));
    const err = new Error(`${resp.status} ${resp.statusText}${detail ? ': ' + detail : ''}`);
    err.status = resp.status;
    err.payload = payload;
    throw err;
  }
  return payload;
}

export const api = {
  get:   (path)        => _request('GET',    path),
  post:  (path, body)  => _request('POST',   path, body || {}),
  put:   (path, body)  => _request('PUT',    path, body || {}),
  del:   (path)        => _request('DELETE', path),

  // ── Ideas ──
  ideas:    () => _request('GET', '/api/ideas'),

  // ── Drafts ──
  drafts:        () => _request('GET',    '/api/drafts'),
  draft:    (id) => _request('GET',    `/api/drafts/${encodeURIComponent(id)}`),
  draftCreate:   (body) => _request('POST',   '/api/drafts', body),
  draftUpdate:   (id, body) => _request('PUT',    `/api/drafts/${encodeURIComponent(id)}`, body),
  draftDelete:   (id) => _request('DELETE', `/api/drafts/${encodeURIComponent(id)}`),

  // ── Writings ──
  writings:           () => _request('GET',    '/api/writings'),
  writing:       (slug) => _request('GET',    `/api/writings/${encodeURIComponent(slug)}`),
  writingCreate: (body) => _request('POST',   '/api/writings', body),
  writingDelete: (slug) => _request('DELETE', `/api/writings/${encodeURIComponent(slug)}`),
  writingStageWrite: (slug, name, content) =>
    _request('PUT', `/api/writings/${encodeURIComponent(slug)}/stage/${encodeURIComponent(name)}`, { content }),
  writingFeedback: (slug, text, stage) =>
    _request('POST', `/api/writings/${encodeURIComponent(slug)}/feedback`, { text, stage: stage || null }),
  writingApprove: (slug, stage) =>
    _request('POST', `/api/writings/${encodeURIComponent(slug)}/approve`, { stage }),
  writingPublish: (slug, target_dir) =>
    _request('POST', `/api/writings/${encodeURIComponent(slug)}/publish`, { target_dir: target_dir || null }),
  writingMarkRead: (slug) =>
    _request('POST', `/api/writings/${encodeURIComponent(slug)}/feedback-cursor`, {}),
};
