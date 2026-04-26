#!/usr/bin/env python3
"""List known topics for ideas-recommender deduplication.

Combines two sources:
  - Hexo posts in tom-ai-lab-blogs/source/_posts/ (already-written articles)
  - Recommended ideas in writing-ideas-app/data/ideas/YYYYMM/DD.json (already-recommended ideas)

Output: JSON to stdout with two arrays — `posts` and `ideas` — each entry has:
  {title, url(if any), slug, source_path}

Usage:
  uv run python scripts/list_known_topics.py
  uv run python scripts/list_known_topics.py --json   # same as default
  uv run python scripts/list_known_topics.py --titles # one title per line
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Iterator

REPO_ROOT = Path(__file__).resolve().parent.parent
POSTS_DIR = REPO_ROOT / "tom-ai-lab-blogs" / "source" / "_posts"
IDEAS_ROOT = REPO_ROOT / "writing-ideas-app" / "data" / "ideas"

# Match Hexo frontmatter "title:" line (handles quoted/unquoted, optional spaces)
TITLE_RE = re.compile(r'^title:\s*"?([^"\n]+?)"?\s*$', re.MULTILINE)


def _iter_post_files() -> Iterator[Path]:
    if not POSTS_DIR.exists():
        return
    for p in POSTS_DIR.rglob("*.md"):
        yield p


def collect_posts() -> list[dict]:
    out = []
    for p in _iter_post_files():
        try:
            text = p.read_text(encoding="utf-8")
        except Exception:
            continue
        m = TITLE_RE.search(text)
        title = m.group(1).strip() if m else p.stem
        out.append(
            {
                "title": title,
                "slug": p.stem,
                "source_path": str(p.relative_to(REPO_ROOT)),
            }
        )
    return out


def _iter_idea_files() -> Iterator[Path]:
    if not IDEAS_ROOT.exists():
        return
    # data/ideas/YYYYMM/DD.json
    for month_dir in sorted(IDEAS_ROOT.iterdir()):
        if not month_dir.is_dir():
            continue
        for day_file in sorted(month_dir.iterdir()):
            if day_file.is_file() and day_file.suffix == ".json":
                yield day_file


def collect_ideas() -> list[dict]:
    out = []
    for f in _iter_idea_files():
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        ideas = data.get("ideas") if isinstance(data, dict) else data
        if not isinstance(ideas, list):
            continue
        rel = str(f.relative_to(REPO_ROOT))
        for it in ideas:
            if not isinstance(it, dict):
                continue
            out.append(
                {
                    "title": it.get("title", ""),
                    "url": it.get("url", ""),
                    "source_path": rel,
                }
            )
    return out


def build() -> dict:
    return {"posts": collect_posts(), "ideas": collect_ideas()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--titles", action="store_true", help="Print one title per line")
    args = parser.parse_args()

    data = build()
    if args.titles:
        for p in data["posts"]:
            print(f"[post] {p['title']}")
        for i in data["ideas"]:
            print(f"[idea] {i['title']}")
        return
    print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
