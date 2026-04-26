"""Writing Platform — FastAPI backend for Ideas + Drafts + Writings collaboration."""
import json
import os
import re
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

APP_DIR = Path(__file__).parent
STATIC_DIR = APP_DIR / "static"
DATA_DIR = APP_DIR / "data"
DRAFTS_DIR = DATA_DIR / "drafts"
DRAFTS_INDEX = DATA_DIR / "drafts-index.json"
IDEAS_ROOT = DATA_DIR / "ideas"
WRITINGS_ROOT = DATA_DIR / "writings"

# Hexo posts directory for publish action
HEXO_POSTS_DIR = APP_DIR.parent / "tom-ai-lab-blogs" / "source" / "_posts"

DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
IDEAS_ROOT.mkdir(parents=True, exist_ok=True)
WRITINGS_ROOT.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Tom Writing Platform")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount /static for the modular frontend
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ── Draft helpers ──────────────────────────────────────────────

def _load_index() -> list[dict]:
    if DRAFTS_INDEX.exists():
        return json.loads(DRAFTS_INDEX.read_text(encoding="utf-8"))
    return []


def _save_index(index: list[dict]):
    DRAFTS_INDEX.write_text(
        json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _draft_path(draft_id: str) -> Path:
    return DRAFTS_DIR / f"{draft_id}.md"


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ── Pydantic models ───────────────────────────────────────────

class DraftCreate(BaseModel):
    title: str
    content: str = ""
    status: str = "draft"  # draft | review | approved | published


class DraftUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    status: Optional[str] = None


# ── API: Drafts ────────────────────────────────────────────────

@app.get("/api/drafts")
def list_drafts():
    index = _load_index()
    return {"drafts": index}


@app.post("/api/drafts")
def create_draft(body: DraftCreate):
    draft_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:6]
    now = _now_iso()
    meta = {
        "id": draft_id,
        "title": body.title,
        "status": body.status,
        "created_at": now,
        "updated_at": now,
    }
    # Save content
    _draft_path(draft_id).write_text(body.content, encoding="utf-8")
    # Update index
    index = _load_index()
    index.insert(0, meta)
    _save_index(index)
    return meta


@app.get("/api/drafts/{draft_id}")
def get_draft(draft_id: str):
    index = _load_index()
    meta = next((d for d in index if d["id"] == draft_id), None)
    if not meta:
        raise HTTPException(404, "Draft not found")
    path = _draft_path(draft_id)
    content = path.read_text(encoding="utf-8") if path.exists() else ""
    return {**meta, "content": content}


@app.put("/api/drafts/{draft_id}")
def update_draft(draft_id: str, body: DraftUpdate):
    index = _load_index()
    meta = next((d for d in index if d["id"] == draft_id), None)
    if not meta:
        raise HTTPException(404, "Draft not found")
    if body.title is not None:
        meta["title"] = body.title
    if body.status is not None:
        meta["status"] = body.status
    if body.content is not None:
        _draft_path(draft_id).write_text(body.content, encoding="utf-8")
    meta["updated_at"] = _now_iso()
    _save_index(index)
    return meta


@app.delete("/api/drafts/{draft_id}")
def delete_draft(draft_id: str):
    index = _load_index()
    new_index = [d for d in index if d["id"] != draft_id]
    if len(new_index) == len(index):
        raise HTTPException(404, "Draft not found")
    _save_index(new_index)
    path = _draft_path(draft_id)
    if path.exists():
        path.unlink()
    return {"ok": True}


# ── API: Ideas ─────────────────────────────────────────────────

def _scan_ideas_files():
    """Walk data/ideas/YYYYMM/DD.json and return (day_files, latest_generated_at)."""
    day_files: list[tuple[str, Path]] = []
    if not IDEAS_ROOT.exists():
        return day_files, ""
    for month_dir in sorted(IDEAS_ROOT.iterdir()):
        if not month_dir.is_dir() or not month_dir.name.isdigit():
            continue
        ym = month_dir.name  # YYYYMM
        if len(ym) != 6:
            continue
        for day_file in sorted(month_dir.iterdir()):
            if not day_file.is_file() or day_file.suffix != ".json":
                continue
            stem = day_file.stem
            if not (len(stem) == 2 and stem.isdigit()):
                continue
            iso_date = f"{ym[:4]}-{ym[4:]}-{stem}"
            day_files.append((iso_date, day_file))
    return day_files, ""


@app.get("/api/ideas")
def get_ideas():
    day_files, _ = _scan_ideas_files()
    all_ideas: list[dict] = []
    seen_urls: set[str] = set()
    dates: list[str] = []
    latest_generated_at = ""
    for iso_date, p in day_files:
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        gen = data.get("generated_at", "")
        if gen and gen > latest_generated_at:
            latest_generated_at = gen
        ideas = data.get("ideas", []) if isinstance(data, dict) else []
        if not isinstance(ideas, list):
            continue
        kept = 0
        for it in ideas:
            if not isinstance(it, dict):
                continue
            it = {**it, "date": it.get("date") or iso_date}
            url = it.get("url") or f"__noid__:{iso_date}:{it.get('title','')}"
            if url in seen_urls:
                continue
            seen_urls.add(url)
            all_ideas.append(it)
            kept += 1
        if kept > 0 and iso_date not in dates:
            dates.append(iso_date)
    # Sort: by date desc, then total score desc
    def _sort_key(it: dict):
        d = it.get("date", "")
        scores = it.get("scores") or {}
        total = scores.get("total", 0) if isinstance(scores, dict) else 0
        return (-_date_int(d), -int(total or 0))
    all_ideas.sort(key=_sort_key)
    dates.sort(reverse=True)
    return {
        "generated_at": latest_generated_at,
        "dates": dates,
        "ideas": all_ideas,
    }


def _date_int(s: str) -> int:
    try:
        return int(s.replace("-", ""))
    except Exception:
        return 0


# ── Writings (agent-driven writing flow) ───────────────────────

VALID_STAGES = ("idea", "outline", "draft", "approved", "published")
APPROVABLE_STAGES = ("outline", "draft")
WRITABLE_STAGES = ("idea", "outline", "draft")
SLUG_RE = re.compile(r"[^a-z0-9\-]+")


def _slugify(title: str) -> str:
    s = title.strip().lower()
    # Replace whitespace with -
    s = re.sub(r"\s+", "-", s)
    # Strip non [a-z0-9-]
    s = SLUG_RE.sub("", s)
    s = re.sub(r"-+", "-", s).strip("-")
    if not s:
        s = "writing"
    return s[:60]


def _writing_dir(slug: str) -> Path:
    return WRITINGS_ROOT / slug


def _allocate_slug(base: str) -> str:
    candidate = base
    n = 2
    while _writing_dir(candidate).exists():
        candidate = f"{base}-{n}"
        n += 1
    return candidate


def _read_status(slug: str) -> dict:
    p = _writing_dir(slug) / "status.json"
    if not p.exists():
        raise HTTPException(404, "Writing not found")
    return json.loads(p.read_text(encoding="utf-8"))


def _write_status(slug: str, status: dict):
    p = _writing_dir(slug) / "status.json"
    tmp = p.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, p)


def _read_meta(slug: str) -> dict:
    p = _writing_dir(slug) / "meta.json"
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def _write_meta(slug: str, meta: dict):
    p = _writing_dir(slug) / "meta.json"
    tmp = p.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, p)


def _read_feedback(slug: str) -> list[dict]:
    p = _writing_dir(slug) / "feedback.jsonl"
    if not p.exists():
        return []
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except Exception:
            continue
    return out


def _append_feedback(slug: str, entry: dict):
    p = _writing_dir(slug) / "feedback.jsonl"
    line = json.dumps(entry, ensure_ascii=False) + "\n"
    with open(p, "a", encoding="utf-8") as f:
        f.write(line)


def _stage_path(slug: str, stage: str) -> Path:
    return _writing_dir(slug) / f"{stage}.md"


def _read_stage(slug: str, stage: str) -> str:
    p = _stage_path(slug, stage)
    return p.read_text(encoding="utf-8") if p.exists() else ""


def _write_stage(slug: str, stage: str, content: str):
    p = _stage_path(slug, stage)
    tmp = p.with_suffix(".md.tmp")
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, p)


def _build_writing_meta_card(slug: str, status: dict, meta: dict) -> dict:
    """Compact card used by the list endpoint."""
    feedback = _read_feedback(slug)
    cursor = status.get("feedback_cursor") or ""
    unread = sum(1 for f in feedback if (f.get("ts") or "") > cursor)
    stage = status.get("stage", "idea")
    last_ts = ""
    for s in VALID_STAGES:
        ts = (status.get("stage_ts") or {}).get(s, "")
        if ts and ts > last_ts:
            last_ts = ts
    return {
        "slug": slug,
        "title": meta.get("title") or slug,
        "stage": stage,
        "updated_at": last_ts,
        "unread_feedback": unread,
        "tags": meta.get("tags") or [],
        "category": meta.get("category") or "",
    }


# ── Pydantic models — Writings ─────────────────────────────────

class WritingCreate(BaseModel):
    title: str
    idea: str = ""
    reference_link: Optional[str] = None


class StageWrite(BaseModel):
    content: str


class FeedbackAdd(BaseModel):
    text: str
    stage: Optional[str] = None  # if omitted, server uses current stage


class ApproveBody(BaseModel):
    stage: str  # required: must match current stage of the writing


class PublishBody(BaseModel):
    target_dir: Optional[str] = None  # subdir under tom-ai-lab-blogs/source/_posts/, e.g. "agent-engineering"


# ── API: Writings ──────────────────────────────────────────────

@app.post("/api/writings")
def create_writing(body: WritingCreate):
    if not body.title.strip():
        raise HTTPException(400, "title is required")
    base = _slugify(body.title)
    slug = _allocate_slug(base)
    wdir = _writing_dir(slug)
    wdir.mkdir(parents=True, exist_ok=True)

    now = _now_iso()
    # Initial idea content
    idea_text = body.idea.strip()
    if body.reference_link:
        idea_text = f"{idea_text}\n\n参考链接: {body.reference_link}".strip()
    _write_stage(slug, "idea", idea_text)

    status = {
        "stage": "idea",
        "stage_ts": {"idea": now},
        "approve_ts": {},
        "feedback_cursor": "",
        "last_error": None,
    }
    _write_status(slug, status)

    meta = {
        "title": body.title.strip(),
        "tags": [],
        "category": "",
        "reference_link": body.reference_link or "",
        "created_at": now,
    }
    _write_meta(slug, meta)

    return _build_writing_meta_card(slug, status, meta)


@app.get("/api/writings")
def list_writings():
    if not WRITINGS_ROOT.exists():
        return {"writings": []}
    cards = []
    for sub in sorted(WRITINGS_ROOT.iterdir()):
        if not sub.is_dir():
            continue
        slug = sub.name
        try:
            status = _read_status(slug)
            meta = _read_meta(slug)
        except Exception:
            continue
        cards.append(_build_writing_meta_card(slug, status, meta))
    # Sort: most-recently-updated first, but show non-published before published
    def _sort_key(c):
        is_published = 1 if c["stage"] == "published" else 0
        return (is_published, "" if not c["updated_at"] else -_iso_int(c["updated_at"]))
    cards.sort(key=_sort_key)
    return {"writings": cards}


def _iso_int(iso: str) -> int:
    try:
        return int(re.sub(r"\D", "", iso)[:14] or 0)
    except Exception:
        return 0


@app.get("/api/writings/{slug}")
def get_writing(slug: str):
    status = _read_status(slug)
    meta = _read_meta(slug)
    feedback = _read_feedback(slug)
    cursor = status.get("feedback_cursor") or ""
    for f in feedback:
        f["unread"] = (f.get("ts") or "") > cursor
    return {
        "slug": slug,
        "status": status,
        "meta": meta,
        "feedback": feedback,
        "stages": {s: _read_stage(slug, s) for s in WRITABLE_STAGES if _stage_path(slug, s).exists()},
    }


@app.put("/api/writings/{slug}/stage/{name}")
def write_stage(slug: str, name: str, body: StageWrite):
    if name not in WRITABLE_STAGES:
        raise HTTPException(400, f"invalid stage: {name}")
    status = _read_status(slug)
    _write_stage(slug, name, body.content)
    now = _now_iso()
    status.setdefault("stage_ts", {})[name] = now
    # If agent wrote outline/draft, advance current stage to that name
    # (only forward; never regress current stage on a write to an earlier one)
    cur = status.get("stage", "idea")
    if VALID_STAGES.index(name) > VALID_STAGES.index(cur):
        status["stage"] = name
    _write_status(slug, status)
    return {"ok": True, "stage": status["stage"], "wrote": name, "updated_at": now}


@app.post("/api/writings/{slug}/feedback")
def add_feedback(slug: str, body: FeedbackAdd):
    text = (body.text or "").strip()
    if not text:
        raise HTTPException(400, "text is required")
    status = _read_status(slug)
    stage = body.stage or status.get("stage", "idea")
    entry = {"ts": _now_iso(), "stage": stage, "text": text}
    _append_feedback(slug, entry)
    return {"ok": True, "feedback": entry}


@app.post("/api/writings/{slug}/approve")
def approve_writing(slug: str, body: ApproveBody):
    status = _read_status(slug)
    if status.get("stage") != body.stage:
        raise HTTPException(409, f"current stage is {status.get('stage')}, cannot approve {body.stage}")
    if body.stage not in APPROVABLE_STAGES:
        raise HTTPException(400, f"stage {body.stage} is not approvable (only outline/draft)")
    now = _now_iso()
    status.setdefault("approve_ts", {})[body.stage] = now
    # Approving outline → status stays at outline (agent reads approve_ts to decide draft)
    # Approving draft → status advances to approved
    if body.stage == "draft":
        status["stage"] = "approved"
        status.setdefault("stage_ts", {})["approved"] = now
    _write_status(slug, status)
    return {"ok": True, "stage": status["stage"], "approve_ts": status["approve_ts"]}


@app.post("/api/writings/{slug}/publish")
def publish_writing(slug: str, body: PublishBody):
    status = _read_status(slug)
    if status.get("stage") != "approved":
        raise HTTPException(409, f"writing is in stage {status.get('stage')}, must be 'approved' to publish")
    draft_path = _stage_path(slug, "draft")
    if not draft_path.exists():
        raise HTTPException(400, "draft.md is missing")

    target_subdir = (body.target_dir or "").strip().strip("/")
    target_root = HEXO_POSTS_DIR / target_subdir if target_subdir else HEXO_POSTS_DIR
    try:
        target_root.mkdir(parents=True, exist_ok=True)
        target_file = target_root / f"{slug}.md"
        shutil.copyfile(str(draft_path), str(target_file))
    except Exception as e:
        # Rollback to approved + record error for next-heartbeat retry
        status["last_error"] = f"publish_failed: {e}"
        _write_status(slug, status)
        raise HTTPException(500, f"publish failed: {e}")

    now = _now_iso()
    status["stage"] = "published"
    status.setdefault("stage_ts", {})["published"] = now
    status["last_error"] = None
    status["published_path"] = str(target_file.relative_to(APP_DIR.parent))
    _write_status(slug, status)
    return {"ok": True, "stage": "published", "published_path": status["published_path"]}


@app.post("/api/writings/{slug}/feedback-cursor")
def update_feedback_cursor(slug: str):
    """Mark all feedback as read up to now (used when Tom views the writing)."""
    status = _read_status(slug)
    status["feedback_cursor"] = _now_iso()
    _write_status(slug, status)
    return {"ok": True, "feedback_cursor": status["feedback_cursor"]}


@app.delete("/api/writings/{slug}")
def delete_writing(slug: str):
    wdir = _writing_dir(slug)
    if not wdir.exists():
        raise HTTPException(404, "Writing not found")
    shutil.rmtree(str(wdir))
    return {"ok": True}


# ── Frontend ───────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
def serve_index():
    return (APP_DIR / "platform.html").read_text(encoding="utf-8")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8765)
