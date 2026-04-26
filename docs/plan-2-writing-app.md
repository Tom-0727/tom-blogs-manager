# 改动设计 2：写作业务交互重构 + writing-ideas-app 重设计

## 1. 背景：当前栈与短板

当前 writing-ideas-app 的栈：FastAPI（`app.py`，端口 8765）+ 单文件 SPA（`platform.html`，约 440 行原生 JS）+ JSON 文件存储。Agent 通过写 `data/ideas/YYYYMM/DD.json`（方案 1 改造后的目录布局）、调用 `POST /api/drafts` 与前端交互；前端通过 fetch 拉 `/api/ideas`、`/api/drafts` 渲染。两个 Tab：选题推荐、草稿箱。

要把现在「Tom 选题后由 agent 被动接手」的交互改成「Tom 在面板抛 idea、agent 在 heartbeat 后链路自驱推进」，三个短板必须先补：

- 数据模型扁平：drafts 是「单条记录 + 单文件正文 + 一个 status」，承载不了同一篇写作走过多个阶段（idea / 大纲 / 草稿）+ 多次反馈这种结构。
- 前端没有写作承载点：两个 Tab 都没有「新增 idea」入口、没有阶段视图、没有反馈流。
- agent 与前端没有稳定契约：agent 后链路推进的前提是后端先把目录布局、状态机、approve / 反馈接口固定下来。

结论：实施新交互之前，先做一轮 writing-ideas-app 的局部重设计；不换框架、不引入构建工具，沿用 FastAPI + 原生 JS + JSON 文件，但加一组新接口、加一个新 Tab、加一套新数据布局。

## 2. 保留

- 整体流水线：大纲 → 出稿 → review → 发布。
- `blog-writer` skill、Hexo frontmatter、tag 体系、Tom 的语气偏好。
- 草稿在线编辑体验：EasyMDE 编辑器迁移到新 Tab 内复用。
- 单文件 SPA + JSON 文件存储这条简单路线。
- 已有的 `data/drafts/` 目录保留给历史草稿，不强制迁移。

## 3. 新数据布局：每篇写作 = 一个目录

`writing-ideas-app/data/writings/<slug>/` 下：

- `idea.md`：Tom 输入的原始意图（标题 + 一两句方向，可选参考链接）。
- `outline.md`：agent 产出的大纲（仅在进入 outline 阶段后存在）。
- `draft.md`：agent 产出的正文草稿（仅在进入 draft 阶段后存在）。
- `status.json`：当前阶段值 + 各阶段时间戳 + agent 已读反馈游标 + 各阶段 approve 时间戳。
- `feedback.jsonl`：Tom 留下的反馈，按时间追加，每条 `{ts, stage, text}`。
- `meta.json`：tags、category、计划字数等结构化字段（agent 与前端共同维护）。

slug 由后端在「新增」时基于标题生成（拼音 / 英文化 + 时间戳后缀），保证唯一。

## 4. 后端：新增 /api/writings 一组接口

在 `app.py` 增一组端点：

- `POST /api/writings`：Tom 点「新增」时调用，body 含 title + 初始 idea；后端创建目录、写 `idea.md` 与初始 `status.json`。
- `GET /api/writings`：列表，仅返回卡片渲染所需的 meta（slug、title、status、updated_at、未读反馈数）。
- `GET /api/writings/{slug}`：单篇，含当前阶段产物正文 + status + 反馈列表。
- `PUT /api/writings/{slug}/stage/{name}`：更新某阶段产物正文（agent 写 outline / draft 用，前端 EasyMDE 改稿也用）。
- `POST /api/writings/{slug}/feedback`：追加一条反馈到 `feedback.jsonl`。
- `POST /api/writings/{slug}/approve`：标记当前阶段被 Tom 通过，状态机往下走一格。
- `POST /api/writings/{slug}/publish`：agent 调用，把 `draft.md` 转 Hexo 博文落到 `tom-ai-lab-blogs/source/_posts/...`，状态转 `published`。

接口故意做成显式动作（approve / publish 单独端点），不让 Tom 通过改 status 字段推进流程，避免误触。

## 5. 前端：按 Tab 模块化（不引入构建工具）

不止是新增一个 Tab，要借这次改动把 `platform.html` 从「单文件塞所有」改成按 Tab 模块化的组织方式，避免后续每加一个 Tab 都让中央文件继续膨胀。

### 5.1 新目录结构

```
writing-ideas-app/
  platform.html                # 只剩外壳：顶部 Tab bar + <main id="content">
  static/
    css/
      base.css                 # CSS 变量、整体布局、Tab bar 样式
      ideas.css
      drafts.css
      writings.css
    js/
      main.js                  # Tab 路由 + 懒加载片段 + 挂载 / 卸载
      api.js                   # fetch 封装（getJson / postJson + 统一错误处理）
      ui.js                    # 通用工具（日期格式、markdown 渲染、弹窗等）
      tabs/
        ideas.js               # export { mount, unmount }
        drafts.js
        writings.js
    html/
      ideas.html               # 该 Tab 的 DOM 片段
      drafts.html
      writings.html
```

`platform.html` 用原生 ES Module 引一个 main.js：`<script type="module" src="/static/js/main.js"></script>`。FastAPI 通过 `app.mount("/static", StaticFiles(...))` 提供静态资源，不引入 Node.js 工具链、不做构建步骤。

### 5.2 模块契约

每个 Tab 模块导出统一接口：
- `mount(rootEl)`：拉对应 html 片段插入 `rootEl`、按需懒加载该 Tab 的 css、绑定事件、初次拉数据。
- `unmount()`：清理事件订阅、定时器、内存中的状态。

main.js 负责 Tab 切换：监听 hash 变化（`#ideas` / `#drafts` / `#writings`），切到新 Tab 时先调上一个 Tab 的 `unmount`、再 `import` 目标 Tab 模块并 `mount` 到 `<main id="content">`。

api.js 集中所有 fetch：所有 Tab 通过它访问后端，便于统一处理 base URL、错误提示、loading 态。ui.js 集中通用 UI 工具，避免每个 Tab 重复造轮子。

### 5.3 写作 Tab 的功能（落在 `tabs/writings.js` + `html/writings.html` + `css/writings.css`）

- 顶部一个「新增」按钮 → 弹出表单（title、初始想法 textarea、可选参考链接） → 调 `POST /api/writings`。
- 主体按状态分栏（idea / outline / draft / approved），每篇写作一张卡片，卡片含：标题、当前阶段、最近一次更新时间、未读反馈数。
- 点击卡片展开为详情视图：左侧是当前阶段产物（idea / outline 用只读 markdown 渲染，draft 用 EasyMDE）；右侧是反馈面板，包含「approve 当前阶段」按钮、「留反馈」输入框、历史反馈列表（按时间倒序）。

### 5.4 既有两个 Tab 的迁移

ideas 与 drafts 按相同契约迁出 `platform.html`，分别放进 `tabs/ideas.js + html/ideas.html + css/ideas.css`、`tabs/drafts.js + html/drafts.html + css/drafts.css`。功能不动，仅做位置与格式重组。这一步与写作 Tab 实现并行做。完成后 `platform.html` 只剩 Tab bar + 主区骨架，预计 50 行以内。

## 6. 状态机

```
idea ──agent写outline──▶ outline ──Tom approve──▶ draft ──Tom approve──▶ approved ──agent发布──▶ published
                              ▲                       ▲
                              └── Tom 留反馈 ──────────┘  （任意阶段可追加，不改 status）
```

agent 永远只看 `status.json` + `feedback.jsonl` 这两个文件判断下一步；前端永远只通过 approve / 反馈端点表达意图。两边通过文件解耦，写作流程不走 mailbox。

## 7. 与 CLAUDE.md 的耦合点

heartbeat 是 runtime 的内在唤醒机制，本方案不修改它；只在 CLAUDE.md 增加规则，让 agent 在 heartbeat 唤醒时跑这套适配逻辑。

要在 CLAUDE.md 增加的规则（v1）：

- 每次 heartbeat 唤醒时，跑 `writing-ideas-app/scripts/scan_writings.py`（待新增），列出所有 status ≠ `published` 的 writing 子目录。
- 对每条 writing 按 status 分支处理：
  - `idea`：调 `blog-writer` 产 outline → 写入 `outline.md` → status 转 `outline`。
  - `outline` 且最近一次 approve 时间戳 ≥ outline 写入时间：调 `blog-writer` 产 draft → 写入 `draft.md` → status 转 `draft`。
  - `draft` 且 `feedback.jsonl` 有新增（按 status.json 中游标判断）：把新反馈合并进 draft，重写 `draft.md`，更新游标，status 不变。
  - `draft` 且最近一次 approve 时间戳 ≥ draft 最近一次写入时间：status 转 `approved`，调 `POST /api/writings/{slug}/publish`。
- 优先级低于 mailbox 紧急消息处理。
- 单次 heartbeat 内的并发策略（串行 / 上限）由 Section 10 待对齐项确定。

## 8. 落地顺序

1. 后端：在 `app.py` 加 `/api/writings` 一组端点 + `data/writings/` 目录契约（不动现有 ideas / drafts 路径）。
2. 前端：先按第 5 节的目录结构搭外壳（`platform.html` 瘦身、main.js 路由、api.js / ui.js 共用层），把 ideas / drafts 两个 Tab 迁过去；再实现写作 Tab，跑通新增、列表、单篇查看、approve、留反馈、阶段产物展示这几个动作。
3. agent 侧：写 `scan_writings.py` + 在 CLAUDE.md 加 heartbeat 扫描规则；用一个 demo 写作（Tom 抛 idea → agent 出大纲 → Tom approve → agent 出草稿 → Tom 反复反馈 → Tom approve → 发布）跑端到端。
4. 端到端跑通后，再决定是否补「分发建议面板」「移动端样式」等下一档增量。

## 9. v1 故意不做

- 不换前端框架、不引入构建工具、不做组件库。
- 不引入数据库、不做并发写保护——单 agent + 单 Tom，靠文件写入顺序兜底。
- 不识别「模糊认可」，只认显式 approve 端点。
- 不做版本分支 / 多稿对比 / 协同编辑。
- 不做移动端推送通知。

## 10. 待对齐细节（动代码前必须先讨论）

数据 / 状态机：
- `status.json` 的 schema 要不要先固化到本文档（字段名、类型、是否可选）？
- 阶段产物（outline / draft）允许 agent 在 Tom approve 之前重写吗？v1 规则是「approve 时间戳 ≥ 阶段产物写入时间」才推进，但若 Tom 在 outline 阶段留反馈，agent 是该重写 outline 还是攒到 draft 阶段处理？
- `meta.json`（tags / category）由谁初始化？Tom 在「新增」时填？还是 agent 在出大纲时给候选？
- slug 冲突时如何降级（同标题二次「新增」）？

后端：
- approve 接口要不要带 stage 参数（防止 Tom 误 approve 到下一阶段）？
- publish 失败时 status 是回滚到 approved 还是停留在 published 并标 error？
- agent 写阶段产物用 `PUT /stage/{name}` 是否够，还是需要专门的 agent 端口（带认证）？

前端：
- 切到 writings Tab 时，未 approve 的 outline / draft 要不要给一个未读红点提醒？
- 反馈输入框：单行还是多行？支持 markdown 渲染吗？
