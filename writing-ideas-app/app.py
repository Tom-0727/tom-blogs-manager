"""Writing Platform — FastAPI backend for Ideas + Drafts collaboration."""
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

APP_DIR = Path(__file__).parent
DATA_DIR = APP_DIR / "data"
DRAFTS_DIR = DATA_DIR / "drafts"
DRAFTS_INDEX = DATA_DIR / "drafts-index.json"
IDEAS_ROOT = DATA_DIR / "ideas"

DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
IDEAS_ROOT.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Tom Writing Platform")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


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


# ── Frontend ───────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
def serve_index():
    return (APP_DIR / "platform.html").read_text(encoding="utf-8")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8765)
