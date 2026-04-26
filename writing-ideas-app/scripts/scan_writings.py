#!/usr/bin/env python3
"""scan_writings.py — list writings the heartbeat agent should act on.

The agent runs this on every heartbeat. It reads each `data/writings/<slug>/`
directory, computes the next required action based on `status.json` +
`feedback.jsonl`, and prints a JSON list to stdout. Status is never mutated
here; mutation is the agent's job (typically via the FastAPI endpoints).

Action types (the field `next_action`):
  - `write_outline`     stage == idea
  - `write_draft`       stage == outline AND approve_ts.outline >= stage_ts.outline
  - `revise_outline`    stage == outline AND has feedback newer than stage_ts.outline
  - `revise_draft`      stage == draft   AND has feedback newer than stage_ts.draft
  - `wait_outline_review`   stage == outline AND nothing new (waiting for Tom)
  - `wait_draft_review`     stage == draft   AND nothing new (waiting for Tom)
  - `publish`           stage == approved
  - `none`              stage == published OR no work needed

Output: a JSON list. Each entry:
  {
    "slug": "...",
    "title": "...",
    "stage": "...",
    "next_action": "...",
    "last_error": null | "...",
    "new_feedback_count": <int>,    // unread feedback for current stage
    "writing_dir": "<rel path>"
  }
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
WRITINGS_ROOT = REPO_ROOT / "writing-ideas-app" / "data" / "writings"


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except Exception:
            continue
    return out


def _decide_action(status: dict, feedback: list[dict]) -> tuple[str, int]:
    stage = status.get("stage", "idea")
    stage_ts = status.get("stage_ts") or {}
    approve_ts = status.get("approve_ts") or {}

    # Feedback newer than the current stage write-time, restricted to entries
    # whose `stage` matches the current stage (so old outline feedback doesn't
    # trigger work after the agent has moved on to draft).
    cur_write_ts = stage_ts.get(stage, "")
    new_for_stage = [
        f for f in feedback
        if (f.get("ts") or "") > cur_write_ts and (f.get("stage") or stage) == stage
    ]
    new_count = len(new_for_stage)

    if stage == "idea":
        return "write_outline", new_count

    if stage == "outline":
        outline_ts = stage_ts.get("outline", "")
        outline_approve = approve_ts.get("outline", "")
        if outline_approve and outline_approve >= outline_ts:
            return "write_draft", new_count
        if new_count > 0:
            return "revise_outline", new_count
        return "wait_outline_review", new_count

    if stage == "draft":
        draft_ts = stage_ts.get("draft", "")
        draft_approve = approve_ts.get("draft", "")
        if draft_approve and draft_approve >= draft_ts:
            # In our state machine approving draft transitions stage to
            # 'approved' on the server, so this branch is mostly a safety net.
            return "publish", new_count
        if new_count > 0:
            return "revise_draft", new_count
        return "wait_draft_review", new_count

    if stage == "approved":
        return "publish", new_count

    return "none", new_count


def main():
    if not WRITINGS_ROOT.exists():
        print("[]")
        return

    out = []
    for sub in sorted(WRITINGS_ROOT.iterdir()):
        if not sub.is_dir():
            continue
        status = _read_json(sub / "status.json")
        if not status:
            continue
        meta = _read_json(sub / "meta.json")
        feedback = _read_jsonl(sub / "feedback.jsonl")
        action, new_count = _decide_action(status, feedback)
        if action == "none":
            continue  # don't show fully-done writings to the heartbeat loop
        out.append({
            "slug": sub.name,
            "title": meta.get("title") or sub.name,
            "stage": status.get("stage", "idea"),
            "next_action": action,
            "last_error": status.get("last_error"),
            "new_feedback_count": new_count,
            "writing_dir": str(sub.relative_to(REPO_ROOT)),
        })
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
