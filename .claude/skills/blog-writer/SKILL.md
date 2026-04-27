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

1. **Apply voice (embedded below) and load tag taxonomy.** Read the tag taxonomy note in full before drafting -- the prose without it tends to over-tag or invent tags:
   - `Memory/knowledge/factual/factual--blog--tag-taxonomy.md`

   The voice profile lives inline in this skill (see Toms Voice Profile section below). Do not search for an external `writing-style-profile.md` -- that knowledge file was retired and the canonical voice profile is now this section.

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

## Toms Voice Profile (embedded; canonical)

This section was migrated from the retired `Memory/knowledge/factual/factual--blog--writing-style-profile.md` knowledge note. Re-read this every time you draft.

### 语言模式
- 中文为主体，英文技术术语大量保留不翻译（Claude Code、Agent、Context、Memory、Learning、Skills、LLM、RAG 等）
- 默认读者有技术背景，不做过度解释

### 开头模式
模式一 -- 从个人痛点 / 困境切入：
- 「每天都有大量的技术信息从各个平台涌现 -- GitHub Trending、Hacker News、Reddit、36Kr、虎嗅...」
- 「运营博客对于我这个还在职的人来讲，什么都是麻烦事」
- 「我有一个持续性的轻微焦虑：感觉自己错过了很多重要的东西。」

模式二 -- 从架构思考框架切入（系列文章常复用同一段 Introduction）：
- 「经过多个 Agent 项目的算法设计实践，我认为一个 Agent 的设计可以用 Context、Memory、Learning、Reasoning 这样的框架去展开思考。」

### 语气特征
- 半正式，介于技术博客和个人随笔之间
- 第一人称「我」频繁出现，强烈个人叙事感
- 口语化穿插技术讨论：「更难受的是」、「刷十条，有八条不相关」、「什么都是麻烦事」
- 坦诚承认局限和放弃
- 明确技术立场，不中立叙述

### 高频句式与过渡
- 长短句交替，节奏感强
- 破折号 `--` 高频用于补充说明或转折
- 冒号引出解释：「核心矛盾：...」「核心问题是：...」
- 引导性问句做段落过渡
- 「但是 / 但」引出转折（极高频）
- 「本质上」做抽象提升（10+ 次出现是常态）
- 「换句话说 / 也就是说」重新表述

### 观点表达句式
- 「我认为 / 我的理解是」
- 「这不是 X，而是 Y」 -- 对立强调
- 加粗强调核心判断
- 「原因很简单」直截了当

### 结尾模式
- 模式一 -- 总结性金句 + 预告下篇（架构系列）
- 模式二 -- 提炼哲学 / 原则性总结
- 模式三 -- 邀请式结尾「如果你也...，不妨 / 欢迎...」

### 反复出现的特征性短语（保留 15 条）
1. 「Human in the loop」 -- 全系列最高频概念
2. 「本质上」 -- 抽象提炼
3. 「核心问题是 / 核心矛盾 / 核心挑战」
4. 「AI 生命体」 -- 对 Agent 的独特拟人称呼
5. 「先让 X 跑起来，再让它变强」「先跑通闭环」
6. 「不追求 X，追求 Y」
7. 「换句话说」
8. 「说大不大，但...」
9. 「不是 X，而是 Y」
10. 「这就是...」
11. 「做了一段时间后我意识到」
12. 「有意为之的设计」
13. 「这里存在一个 X 的问题」
14. 「天然就是 / 天然适合」
15. 「务实 / 闭环 / 跑通 / 落地」

### 比喻习惯
- 把 Agent 拟人化为「生命体」「灵魂」
- 工人比喻解释 Context
- 大脑 / 记忆类比解释 Memory
- 偶尔引用「抽象之梯」（S.I.Hayakawa）

### 排版习惯
- H2 / H3 为主，标题中文 + 冒号 / 破折号
- blockquote 用于引导性问题和金句
- 表格用于对比分析（高频）
- 代码块用于目录结构，非大段代码
- `<u>下划线标记</u>` 用于列表项小标题（独特习惯）

### 词汇特征
- 务实类：务实、闭环、跑通、落地、工程落地
- 拟人类：生命体、灵魂、大脑、成长、认知
- 设计类：设计理念、设计哲学、架构优势
- 避免使用：从不使用「干货」「硬核」「保姆级」等流量化标题词

### 博客元信息
- 博主：Linfeng (Tom) Liu
- 身份：AI Agent Engineer
- 框架：Hexo + Fluid
- 部署：GitHub + Vercel → https://www.tom-blogs.top/
- 4 个一级分类：ResearcherZero、Agent Engineering、Agent Product、Demo
- 核心项目：ResearcherZero（AI 研究员 Agent）

