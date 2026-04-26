---
id: ep.20260413T035500Z.blog.data-analytics-monitoring-design
task_id: task.blog.data-analytics-monitoring
domain: blog
title: Design plan for tom-blogs.top data analytics and monitoring
objective: Produce a complete design plan for monitoring and analytics of tom-blogs.top, focusing on solving the indexing problem (only homepage + About indexed).
status: completed
last_edited_at: 2026-04-13
---

## Objective

Human discovered only homepage and About page are indexed by Google despite having 14+ articles. Need a complete design plan for:
1. Diagnosing and fixing the indexing problem
2. Setting up ongoing data analytics monitoring
3. Specifying what human needs to set up, what APIs to use, what analysis to do

## Context Snapshot

- Blog: Hexo + Fluid theme, deployed via GitHub + Vercel at https://www.tom-blogs.top/
- Sitemap exists at /sitemap.xml with 38 URLs (articles + tag/category pages)
- robots.txt is permissive (Allow: /)
- Google verification file exists (googleb2237a40245298eb.html) — so Search Console may already be partially set up
- No noindex/nofollow tags on any pages
- No x-robots-tag response headers
- Canonical tags are correct
- No Vercel config blocking crawling
- 14 articles across 4 categories, published Jan-Apr 2026

## Design Plan

### Phase 1: Google Search Console（需要 human 操作）

目的：这是诊断和解决索引问题的核心工具

**Human 需要做的：**
1. 登录 Google Search Console (https://search.google.com/search-console)
2. 确认 www.tom-blogs.top 已添加为属性（Google verification file 已存在，说明可能已部分设置）
3. 在 Search Console 中做以下操作并把结果告诉我：
   - 打开「网页索引编制」报告 — 看哪些页面已编入索引、哪些未编入、未编入的原因是什么
   - 打开「Sitemap」— 确认 sitemap 已提交，如果没有则提交 https://www.tom-blogs.top/sitemap.xml
   - 打开「网址检查」— 逐一检查几个未索引的文章 URL，看 Google 给出的具体原因（已发现未编入索引？已抓取未编入索引？被 noindex 排除？）
   - 对未编入索引的页面点「请求编入索引」

**我可以分析的：**
- 收到 Search Console 数据后，分析索引失败模式（是发现问题还是质量问题）
- 检查是否需要增加内部链接密度、改善页面结构化数据

**可能的索引失败原因（按可能性排序）：**
1. **已发现 - 尚未编入索引**：Google 知道这些 URL 但还没爬。新站常见，需要手动请求索引 + 等待
2. **已抓取 - 目前未编入索引**：Google 爬了但觉得内容质量/独特性不够，暂时不收录
3. **Sitemap 未提交**：Google 可能只通过首页发现了 About 链接
4. **内部链接不足**：首页只展示最新几篇，老文章缺少入口

### Phase 2: 流量分析工具

目的：了解访客来源、行为、热门内容

**方案A：Google Analytics 4（推荐，功能最全）**
- Human 需要：创建 GA4 属性，获取 Measurement ID (G-XXXXXXX)
- 我来做：在 Hexo 的 _config.fluid.yml 中配置 GA tracking code
- 数据：页面浏览量、用户来源、停留时间、跳出率、地理分布
- API：GA4 Data API (https://developers.google.com/analytics/devguides/reporting/data/v1) — 可以用来自动拉取数据做分析

**方案B：Vercel Analytics（最简单，但数据有限）**
- Human 需要：在 Vercel 项目设置中开启 Analytics（可能需要 Pro 计划）
- 数据：页面访问量、访客数、来源国家
- 局限：没有 API 可以程序化访问，数据维度少

**方案C：Plausible / Umami（隐私友好，自托管可选）**
- 优点：轻量、无 cookie、GDPR 友好
- 缺点：需要额外部署或付费 SaaS

**我的建议：GA4 + Google Search Console 组合**
- Search Console 管搜索表现（收录、排名、点击率）
- GA4 管站内行为（哪些文章最受欢迎、用户路径、停留时间）

### Phase 3: 自动化监控 Pipeline

目的：定期自动拉取数据，生成分析报告

**数据源和 API：**

| 数据源 | API | 能获取什么 | 认证方式 |
|--------|-----|-----------|---------|
| Google Search Console | Search Console API v3 | 索引状态、搜索查询、点击量、展示量、平均排名 | OAuth2 / Service Account |
| Google Analytics 4 | GA4 Data API | 页面浏览量、用户数、来源渠道、设备分布 | OAuth2 / Service Account |
| Sitemap | 直接 HTTP 请求 | URL 数量、更新频率 | 无需认证 |

**Human 需要打通的：**
1. 创建 Google Cloud 项目
2. 启用 Search Console API 和 GA4 Data API
3. 创建 Service Account，下载 JSON 密钥文件放到服务器
4. 在 Search Console 和 GA4 中给 Service Account 授权
5. 把密钥路径告诉我

**我来做的：**
1. 写一个 Python 监控脚本（analytics_monitor.py）：
   - 定期调用 Search Console API 获取索引状态和搜索表现
   - 定期调用 GA4 API 获取流量数据
   - 生成结构化报告存入 Memory/knowledge/
   - 检测异常（索引数下降、流量突降）时通过 mailbox 告警

2. 数据分析维度：
   - **索引健康度**：已索引页面数 / 总页面数，索引率变化趋势
   - **搜索表现**：每篇文章的展示量、点击量、平均排名、CTR
   - **流量分析**：总 PV/UV 趋势、来源渠道分布（搜索 vs 直接 vs 社交）、热门文章 Top 10
   - **内容 ROI**：每篇文章的搜索流量贡献，找出高展示低点击的优化机会（标题/description 优化）
   - **SEO 机会**：哪些查询词排在第 5-20 名（有优化空间），哪些文章缺少目标关键词

3. 报告频率：
   - 周报：关键指标汇总，通过 mailbox 发送
   - 实时告警：索引数下降、流量异常时立即通知

### Phase 4: 即时可做的优化（不需要等 API 打通）

1. **提交 Sitemap**：如果 Search Console 中还没提交 sitemap，立即提交
2. **增加内部链接**：确保每篇文章都有至少 1-2 个指向其他文章的链接（已在做）
3. **添加结构化数据**：给文章页面加 JSON-LD 结构化数据（Article schema），帮助 Google 理解内容
4. **首页优化**：确认首页列出所有文章而非只显示最新几篇，让 Google 能通过首页发现所有内容
5. **Bing Webmaster Tools**：顺便提交到 Bing，增加搜索引擎覆盖

## 下一步行动

1. Human 先去 Google Search Console 查看索引状态并反馈具体原因
2. Human 决定选哪个流量分析方案（GA4 推荐）
3. Human 创建 Google Cloud 项目 + Service Account 并打通 API 权限
4. 我开始写监控脚本和搭建数据 pipeline
5. 同时我可以先做 Phase 4 中不需要 API 的即时优化
