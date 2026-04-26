# Writing Platform

Tom-Blogs-Manager 的写作协同后台：选题推荐 + 草稿箱。

线上地址：https://writing-platform.tom-blogs.top （由 FastAPI 提供，systemd 服务名 `writing-platform.service`，监听 8765）。

`index.html` 仅作为旧 GitHub Pages 入口的兼容跳转，所有功能均在 FastAPI 服务上。

## 组成

- `scorer.py` — 离线评分脚本。从 ai-informer 找最新 digest，按五维打分并合并历史，输出 `data/ideas.json`。
- `app.py` — FastAPI 后端，提供草稿 CRUD（`/api/drafts`）与选题只读接口（`/api/ideas`），根路径返回 `platform.html`。
- `platform.html` — 单页 SPA，两个 tab：选题推荐 + 草稿箱（用 EasyMDE 编辑 Markdown）。
- `data/`
  - `ideas.json` — scorer 产出，供前端消费。
  - `drafts-index.json` — 草稿元数据索引。
  - `drafts/{id}.md` — 单篇草稿正文。

## 评分维度（每维 1–5，总分 25）

| 维度 | 说明 |
|------|------|
| 受众覆盖度 | 能触达多少类目标读者（技术同行 / 业务决策者 / 合作方） |
| 传播潜力 | 搜索引擎和社交媒体的传播性 |
| 作者独特性 | Tom 能否基于自身经验提供独特视角 |
| 时效性 | 发布窗口期 |
| 系列化潜力 | 能否展开为系列内容 |

总分约定：20+ 强烈推荐，15–19 值得考虑，<15 优先级低。所有打分规则集中在 `scorer.py` 顶部的常量区。

## 本地使用

```bash
# 重新生成选题数据
python scorer.py

# 启动后端（开发模式）
python app.py
# 访问 http://localhost:8765
```

## 草稿协同流程

1. Tom-Blogs-Manager 写完文章后，通过 `POST /api/drafts` 创建草稿（status=`review`）。
2. 人在 https://writing-platform.tom-blogs.top/#drafts 浏览器内审阅、编辑、保存。
3. 人通过 mailbox 告知通过后，agent 拉取最终内容、提交到 `tom-ai-lab-blogs` 仓库，并将草稿状态改为 `published`。
