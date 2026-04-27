---
id: ep.20260427T024000Z.platform.cleanup-and-fixes
task_id: task.platform.post-launch-cleanup
domain: platform
title: writing-ideas-app post-launch cleanup — drop drafts, stage-tabs UI, fix unread cursor
status: completed
eval_rounds: 0
last_edited_at: 2026-04-27
---

## Objective

Address Tom's three post-launch issues with the writing-ideas-app:
1. Delete the legacy 「草稿箱」 tab — its function is now subsumed by 「写作」.
2. Restructure the writings list view: stage cards as columns is too sparse; switch to one sub-tab per stage with a single card grid.
3. Fix the unread badge bug: it currently bumps when Tom himself leaves feedback (then clears when he opens the detail), so the agent never sees the signal.

## Context Snapshot

- All three plans (ideas-recommender, writings flow, weekly cron) are live as of 2026-04-26.
- Tom's feedback came in as one mailbox message (mail.20260427T023654Z.001).
- Drafts directory has only 2 md files, both are duplicates of articles already published in tom-ai-lab-blogs — confirmed safe to delete.

## Actions Taken

### t1 — Drop drafts entirely
- Verified `data/drafts/{20260415T064442Z-d8dafc.md, 20260412T135054Z-090004.md}` are byte-identical to the published Hexo posts.
- Removed from `app.py`: `/api/drafts*` routes, `DraftCreate/DraftUpdate` models, `_load_index/_save_index/_draft_path` helpers, `DRAFTS_DIR/DRAFTS_INDEX` constants and mkdir.
- Removed `static/js/tabs/drafts.js`, `static/css/drafts.css`, `static/html/drafts.html`.
- `main.js` TABS map no longer registers drafts; `api.js` drops `draft*` methods.
- `platform.html` tab bar has only 「选题推荐」 and 「写作」 now.
- Deleted `data/drafts/` and `data/drafts-index.json`.

### t2 — Stage sub-tabs on writings list
- New HTML: `#stageSubtabs` + single `#writingsGrid` (replacing the 5-column `.stage-columns`).
- New CSS: `.stage-subtabs / .stage-subtab-btn / .writings-grid` (pill-shaped sub-tab buttons with a count chip and a pending dot).
- `tabs/writings.js` now renders one card grid filtered by `activeStage`. Default stage selection prefers stages with agent-pending feedback, otherwise the first non-published stage with cards.
- Hash routing: writings tab uses `#writings/<stage>` so refreshes restore the active stage; main.js's `tabFromHash()` strips the sub-route segment so the top-level tab still resolves.

### t3 — Unread cursor semantics fix
- Schema change in `status.json`: dropped `feedback_cursor`; the agent-side cursor is now derived from `stage_ts[current_stage]`.
- New helper `_agent_pending_feedback(status, feedback)`: returns feedback where `stage == current_stage AND ts > stage_ts[current_stage]`.
- `_build_writing_meta_card` exposes `agent_pending_feedback: N` (replacing `unread_feedback`).
- `GET /api/writings/{slug}` annotates each feedback entry with `agent_pending: bool`.
- Removed `POST /api/writings/{slug}/feedback-cursor` and the `writingMarkRead` API client; writings.js no longer calls mark-read on detail open.
- main.js badge poller switched to `agent_pending_feedback`.

### Verification
- /tmp/reg.py runs 6 scenarios end-to-end:
  1. After Tom leaves feedback → pending=1 (was the bug; used to be 0 after view).
  2. Each feedback entry has `agent_pending: true`.
  3. After agent writes outline → idea-stage feedback drops out of current count (pending=0).
  4. Outline-stage feedback then bumps pending=1.
  5. Agent revising outline (PUT /stage/outline) clears pending=0.
  6. Tom viewing detail does NOT clear pending (no auto-mark-read).
- `scan_writings.py` correctly identifies post-feedback outline writing as `revise_outline`.
- HTTP smoke checks: `/api/drafts → 404`, `/api/writings → 200`, `/api/writings/foo/feedback-cursor → 404`, `/static/css/drafts.css → 404`, `/static/html/writings.html → 200`. Frontend serves only 2 tabs ("草稿箱" string count = 0).

## Outcome

- Cleanup complete; writings flow is the only writing surface now.
- Stage sub-tabs make 5 stages legible at a glance with per-stage pending dots.
- Unread badge semantics now match what Tom expected: the dot reflects "agent has feedback to apply", not "human hasn't viewed yet".

## Reflection

- Renaming `unread_feedback` → `agent_pending_feedback` makes the field's meaning unambiguous, which is the better design even before the bug surfaced.
- main.js routing had a latent bug — `tabFromHash` returned DEFAULT_TAB on any sub-route. The stage-tabs feature surfaced it; fix was a one-liner.
