---
id: ep.20260408T061200Z.blog.writing-platform-build
task_id: task.blog.writing-platform
domain: blog
title: Build Writing Platform with draft collaboration system
objective: Replace static GitHub Pages with a full writing platform featuring Ideas + Drafts tabs, enabling human to edit drafts in browser.
status: completed
last_edited_at: 2026-04-08
---

## Objective

Human requested a draft collaboration system: static GitHub Pages is too limited, need a server-side app where I can post article drafts and human can view/edit them in a Markdown editor. Domain writing-platform.tom-blogs.top already pointed to this server.

## Context Snapshot

- Prior: tom-writing-ideas was a static GitHub Pages site with ideas.json + index.html
- Server already runs Caddy on ports 80/443 with one site (agent-forge.tom-blogs.top)
- Existing ideas page had date filtering, 5-dimension scoring cards, recommendation levels

## Actions Taken

- Built FastAPI backend (app.py) with: drafts CRUD API, ideas API, frontend serving
- Built platform.html: dual-tab SPA (Ideas + Drafts), integrated EasyMDE Markdown editor
- Draft data model: JSON index + individual .md files in data/drafts/
- Draft statuses: draft → review → approved → published
- Created systemd service (writing-platform.service) on port 8765
- Added writing-platform.tom-blogs.top to Caddyfile, reloaded Caddy
- Set old index.html to redirect to new platform
- Updated Blog Publishing SOP in CLAUDE.md to use draft box workflow
- Pushed all changes to tom-writing-ideas repo

## Key Evidence

- Caddy was already running (not nginx) — discovered via `ps aux`
- All APIs verified working: create, get, update, delete drafts
- Platform accessible at https://writing-platform.tom-blogs.top (HTTP 200)

## Outcome

- Writing Platform live and functional
- New SOP: write article → POST to draft box → human edits in browser → human approves → publish
- Service is persistent (systemd, enabled on boot)

## Reflection

- Checking existing infra before assuming (Caddy vs nginx) saved time
- Single HTML file with CDN-loaded EasyMDE keeps deployment simple — no build step needed
- The draft collaboration model is much better than passing full articles through mailbox

## Follow-up Actions

- First real draft workflow test when human requests next article
- May need to add auth/password protection if platform is public-facing
