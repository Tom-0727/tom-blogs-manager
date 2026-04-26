---
name: blog-writer
description: Produce publication-ready blog articles for tom-ai-lab-blogs in Tom's voice -- covers research synthesis, Hexo frontmatter, tag/category selection, structure templates, and the quality bar. Use whenever Tom-Blogs-Manager needs to draft, expand, or polish a full article from a brief, an outline, or a research bundle (phrases like "写一篇博客", "出稿", "把这个研究写成文章", "扩成正式稿"). Do not use for idea generation, topic ranking, scheduling, or short social-style posts -- those have their own flows.
---

# blog-writer

Turn a topic + research bundle into a publication-ready article for `tom-ai-lab-blogs`. This skill carries the workflow and the quality bar; the actual style profile and tag taxonomy live as knowledge notes so the file stays lean and the source of truth stays single.

## Inputs the caller must provide

- **Topic and brief** -- what the article is about, the angle, Tom's personal experience or core viewpoint.
- **Research results** -- key facts, quotes, or links from primary sources (Anthropic blog, paper, repo docs, industry report, etc.).
- **Outline (optional)** -- if already confirmed by human, follow it exactly without restructuring.

If any of the above is missing or thin, surface the gap to the caller before writing. Do not invent material to fill it.

## Workflow

1. **Load voice and taxonomy.** Read both knowledge notes in full before drafting -- the prose without these reads ends up generic:
   - `Memory/knowledge/factual/factual--blog--writing-style-profile.md`
   - `Memory/knowledge/factual/factual--blog--tag-taxonomy.md`

2. **Research, then write -- never the other way.** Drafting from memory alone is the fastest way to produce a forgettable post. At minimum:
   - Read the primary source the topic centers on.
   - Skim 1-2 related existing posts under `tom-ai-lab-blogs/source/_posts/` for continuity and cross-linking.
   - Extract 3-5 concrete facts or quotes that will land in the article as evidence.

3. **Pick a structure template** based on the article's intent (see below). Adapt to the material -- do not copy the template mechanically.

4. **Draft in Tom's voice.** Voice over coverage: one or two sharp points made well beats an exhaustive enumeration.

5. **Self-check against the quality checklist** before saving.

6. **Save and report back.** Write to the correct path (see Output), then return the file path plus a one-paragraph summary of choices made -- which template, which tags, which sources cited, and any spots where the draft is still rough.

## Hexo frontmatter template

Use exactly these fields. Do not add fields the theme does not consume.

```yaml
---
title: "文章标题"
date: YYYY-MM-DD HH:mm:ss
updated: YYYY-MM-DD HH:mm:ss
tags: [tag-1, tag-2, tag-3]
categories: [Category Name]
description: "100-160 字中文 SEO 描述，包含核心关键词，概括文章价值主张。"
---
```

- `categories` -- pick exactly one human-readable name: `ResearcherZero` | `Agent Engineering` | `Agent Product` | `Demo`. The on-disk folder uses the kebab-case form (see Output).
- `tags` -- 2-5 lowercase kebab-case tags from the approved taxonomy. Do not invent new tags without first updating the taxonomy note.
- `date` / `updated` -- the moment of writing. If scheduled for later publication, confirm with human first.

## Article structure templates

### Template A -- Product / Project introduction
1. Problem or pain point (why this matters, ideally personal)
2. What I built / what I am using
3. Core design decisions (2-3 with rationale, not a feature list)
4. Results or current status (honest, including what is still rough)
5. What is next + invitation

### Template B -- Architecture / Design deep dive
1. Context shift or realization (personal narrative, not abstract)
2. Problem decomposition (2-4 sub-problems)
3. Solution architecture, contrasted with at least one alternative
4. Implementation highlights (the parts a peer would actually want to see)
5. Honest limitations + future direction

### Template C -- Industry insight / Opinion
1. Hook: event, trend, or personal experience
2. Core thesis stated early (one clear opinion)
3. 2-3 supporting arguments grounded in research
4. Counterargument or nuance (intellectual honesty is part of the style here)
5. Synthesis and forward-looking conclusion

## Output

- **Length** -- 1500-2500 字 (Chinese characters + retained English terms).
- **File path** -- `tom-ai-lab-blogs/source/_posts/<category-folder>/<slug>.md`
  - Category folders on disk: `researcher-zero/`, `agent-engineering/`, `agent-product/`, `demos/`.
  - Slug: lowercase English kebab-case, short and stable.
- **Internal link** -- include at least one link to a related existing post when continuity exists.
- **External links** -- every cited source must be linked.
- **Bar** -- human should be able to approve the draft without substantial edits. If you are not at that bar, say so in the return summary rather than pretending.

## Quality checklist

Run through this before declaring done:

- Frontmatter complete; exactly one category; 2-5 tags from approved taxonomy.
- Opening hooks the reader within the first 2 sentences (use one of the two opening modes from the style profile).
- Each section makes a point, not just describes.
- Bold only on key assertions, never for ordinary emphasis.
- Tom's voice -- first-person, pragmatic, occasional one-sentence paragraph for rhythm, double-dash `--` for asides (not em dash).
- At least one personal experience or opinion per major section.
- Conclusion is forward-looking, not a recap.
- All external sources linked; internal cross-link present if continuity exists.
- No invented facts or statistics -- every claim traces back to a research note.
