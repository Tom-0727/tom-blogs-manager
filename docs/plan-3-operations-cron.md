# 改动设计 3：博客运营周度数据复盘

## 1. 背景

当前博客运营动作（数据采集、SEO 周报、分发建议）主要是「按 Tom 触发」执行的。要让北极星（影响力 / 浏览量）有持续推力，第一步是把「周度数据复盘」这件最基础的事改成定期任务，让 agent 在主动模式下自走，并把结论以低频汇总送给 Tom。其他更复杂的运营动作（发布后即时分发、双周整理、月度汇总等）暂不做，留给后续增量。

数据采集底层（Search Console / GA4 / URL Inspection）的调用方式不变；本方案动三件事：触发节奏、输出形态、以及「这套能力的承载位置」。

## 2. 实现承载形态：作为 subagent，不留根目录业务脚本

新增一个私有 subagent `blog-weekly-reporter`，在 `.claude/agents/blog-weekly-reporter.md` 落位，与现有 `episode-executor.md`、`evaluator.md` 等同级。承载形态参照 plan-1 中 `ideas-recommender` 的设计——判断逻辑由提示词承载（可读、可改、可注入新偏好），而不是写死在脚本常量里。

subagent 提示词内嵌：

- 周报核心判断逻辑：哪些 URL 应进收录清单、哪些文章本周值得对外分发、分发建议如何拟（hook、改写标题、渠道建议）。
- Tom 的偏好与北极星指标（影响力 / 浏览量）对齐的措辞、判断口径。
- 周报模板（标题、正文结构、两个清单的格式）。

底层数据采集脚本的处置：

- 现有 `analytics/monitor.py`（Search Console / GA4 采集封装）迁到 `scripts/analytics/monitor.py` 作为业务工具脚本，组织方式与 plan-1 中 `scripts/list_known_topics.py` 一致——仓库根的 `scripts/` 是统一的通用脚本目录，按业务分子目录（analytics/、ideas/ 等）。subagent 在提示词里指引调用，不自己重写 API 调用代码。
- 现有 `analytics/weekly_report.py`（周报脚本）整体退役、删除——它原来承担的「出周报」职责由 subagent 提示词替代，不保留为兜底。subagent 失败就当次失败、下次重跑，不引入「subagent 失败 → 退回脚本生成」这种双路径，避免规则两边漂移（与 plan-1 退役 scorer.py 的处理对齐）。
- 迁移完成后仓库根目录的 `analytics/` 目录整体删除。
- `.secrets/tom-blogs-sa.json`（service account 凭证）位置不变，属于全局凭证、不进 subagent 也不进 scripts/。

## 3. 周度数据复盘任务

每周一上午（本机时区，即新加坡时间）由 `scheduled_tasks.json` 触发，主 agent 拉起 `blog-weekly-reporter` subagent；subagent 调用 `scripts/analytics/monitor.py` 拿原始数据，按提示词内嵌逻辑产出周报，通过 mailbox 发给 Tom，单条消息内附两个清单：

- 已提交收录清单：subagent 自动通过 Search Console 的 indexing API 为本周新发现、未被 Google 索引的文章 URL 提交收录请求，周报里附已提交列表告知 Tom，不需要 Tom 手动到 Search Console 操作。
- 分发建议清单：本周值得对外推的文章 + 推荐渠道（Twitter / 知乎 / 即刻 / 社群）+ 建议 hook 与改写标题。

## 4. 任务承载方式

通过 `scheduled_tasks.json` 注册一个时间触发器（周一上午，本机=新加坡时区），到期时主 agent 拉起 `blog-weekly-reporter` subagent 完成整套动作（拉数据 → 自动提交 indexing API → 整理周报 → 发 mailbox）。`scheduled_tasks.json` 是固有机制，沿用现有 schema 与约定，不为本方案改字段。

## 5. 不动

- Search Console、GA4、URL Inspection 的调用方式（封装在迁到 `scripts/analytics/monitor.py` 内部，逻辑不动）。
- service account 配置（`.secrets/tom-blogs-sa.json`）。

注意：原 `analytics/weekly_report.py` 里的「周报生成」逻辑不属于「不动」——它由 subagent 提示词重写承载、原脚本退役。

## 6. 与 CLAUDE.md 的耦合点

CLAUDE.md 新增一条规则（措辞落地时定）：当 `scheduled_tasks.json` 中「周度数据复盘」触发器到期时，主 agent 拉起 `blog-weekly-reporter` subagent 完成周报生成与 mailbox 报告，主 agent 自身不直接做周报判断。与 plan-1 中「主 agent 拉起 ideas-recommender 完成筛选」的耦合方式对齐。

## 7. v1 故意不做

- 发布后即时分发建议任务（依赖方案 2 的 publish 端点，先不挂钩子）。
- 双周历史 ideas 排序、低 CTR 页面 title / description 改写候选。
- 月度浏览量 / Top 文章 / 关键词机会汇总。
- 异常阈值告警与连续多次跑结果对比。

这些动作在「最基础的周度复盘」跑通、Tom 看到周报实际能驱动决策之后再决定是否补。补的时候作为同一 subagent 的提示词扩展、或新增专门的 subagent，不再在仓库根目录新建业务目录或业务脚本。

