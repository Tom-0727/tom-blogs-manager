---
id: ep.20260406T205000Z.blog.writing-ideas-webapp
task_id: task.blog.writing-ideas-app
domain: blog
title: 构建写作选题推荐Web App
objective: 开发一个Web App，自动从AI-Informer日报中评估和推荐高价值写作主题
status: active
last_edited_at: 2026-04-06
---

## Objective

根据human指示，建设一个独立repo，实现web app推送写作idea给human。

## Context Snapshot

- Human指示：不用等选题回复，最高优先级是优化AI-Informer + 建写作idea Web App
- 已有选题评估框架（kn.blog.conceptual.topic-recommendation-framework）
- AI-Informer已接通，数据格式已知（filtered.json）

## Actions Taken

1. 创建writing-ideas-app目录
2. 开发scorer.py：
   - 实现五维评分逻辑（基于关键词匹配和规则）
   - 定义Tom的专业优势域和弱域关键词集
   - 自动分类内容线、生成建议写作角度
   - 输出与手动评估一致的结果
3. 开发server.py：
   - 单文件Web服务器（仿现有web_ui_server.py风格）
   - 美观的Web界面，展示评分卡片、五维分项、建议角度
   - /api/ideas和/api/refresh两个API端点
4. 本地测试通过，API返回正确数据
5. Git init并提交
6. 无法创建GitHub repo（缺少API Token），已通知human帮忙创建

## Key Evidence

- 评分引擎结果与手动评估一致：OpenClaw 22/25, Solo Founder 20/25, 低价值项12/25
- Human要求GitHub Pages部署，重构为纯静态站点
- Repo: git@github.com:Tom-0727/tom-writing-ideas.git

## Outcome

- 代码已推送至GitHub（Tom-0727/tom-writing-ideas）
- 架构：scorer.py生成data/ideas.json → index.html静态读取 → GitHub Pages部署
- 等待human在GitHub Settings中开启Pages
- Status: completed

## Reflection

- 最初设计为Python web server，human明确要GitHub Pages后快速重构为静态站点
- 纯前端方案更简单，无需服务器维护
- 后续更新流程：收到新日报 → 运行scorer.py → git push → 页面自动更新

## Follow-up Actions

- 每次收到AI-Informer新日报时自动运行scorer.py并push更新
- 考虑在heartbeat中集成自动更新逻辑
