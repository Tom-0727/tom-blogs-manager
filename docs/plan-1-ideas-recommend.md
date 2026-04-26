# 改动设计 1：Ideas 推送改造（scorer.py → 推荐 subagent）

## 1. 背景

Ideas 推送是三块业务里的「上游」。当前实现里，AI-Informer 推过来的资讯条目通过 `writing-ideas-app/scorer.py` 用 hardcode 的五维评分常量做筛选，再合并进 `data/ideas.json` 喂给 ideas 面板。问题是：硬筛规则一旦写死，就很难随 Tom 偏好的演化、随北极星（影响力 / 浏览量）的反馈持续迭代。

改造思路：把「筛选与排序」这件事从一段定值脚本搬到一个专门的 subagent，让"判断逻辑"由提示词（可读 / 可改 / 可注入新偏好）承载，而不是常量。

## 2. 保留

- 输入端：AI-Informer 主动把整理好的资讯条目写进 `mailbox/agent.AI-Informer.jsonl`，这条入口不变。
- 推送形式：仍然走 writing-ideas-app 的 ideas 面板（`#ideas`）让 Tom 浏览选择。
- 前端契约：前端依然调 `GET /api/ideas` 拉推荐列表，端点路径不变（实现内部改成扫新数据布局）。

## 3. 改造方案

### 3.1 替换

彻底退役 `writing-ideas-app/scorer.py`：实施时直接从仓库删除，不保留为兜底。subagent 失败就当次失败，由下一次触发点重跑；不引入「subagent 失败 → 退回脚本筛选」这种双路径，避免规则两边漂移。

### 3.2 新增 subagent

在 `.claude/agents/` 下增加一个 subagent（暂命名 `ideas-recommender.md`，参照该目录下既有 `episode-executor.md` 等格式）。提示词显式注入：

- Tom 偏好：完整内嵌在 subagent 提示词里（语气、选题倾向、需避免的主题、五维筛选措辞）。落地时把 `Memory/knowledge/factual/factual--blog--writing-style-profile.md` 的内容一次性迁入提示词，并删除原 knowledge 文件——不保留外部依赖，避免「提示词 vs knowledge 文件」两份偏好长期不一致。
- 与北极星一致的筛选维度：受众覆盖、传播潜力、独特性、时效性、系列化潜力（沿用现有五维框架，但措辞由提示词承载，可演化）。
- 历史去重上下文：只用「已写文章列表 + 已推荐 ideas 列表」两个集合。不引入「已弃选题」——当前没有任何代码或机制能可靠记录 Tom 弃过哪些选题，强行加只会变成噪声或误判。

### 3.3 调用契约

主 agent 拉起 `ideas-recommender` 时，明确告诉它：

- 读哪里：
  - AI-Informer 最新写进 `mailbox/agent.AI-Informer.jsonl` 的资讯条目。
  - 历史去重信息：调用一个新脚本 `scripts/list_known_topics.py` 拿到「已写文章 + 已推荐 ideas」两个清单。脚本内部统一从 Hexo 仓库 `tom-ai-lab-blogs/source/_posts/` 与 `writing-ideas-app/data/ideas/` 目录读取并去重，subagent 不直接扫多个数据源。
  - Tom 偏好：内嵌在 subagent 提示词里，不再外读任何 knowledge 文件。
- 写哪里：
  - 不再写单文件 `data/ideas.json`。新数据布局按月/日分层：`writing-ideas-app/data/ideas/YYYYMM/DD.json`（YYYYMM = 年月，DD = 日，例如 `data/ideas/202604/26.json`）。每次推荐生成 / 追加到当天对应的 JSON 文件。
  - 后端 `GET /api/ideas` 端点从「直读单文件」改为「扫 `data/ideas/` 下所有月份目录、按日期倒序聚合返回」。前端只调这个端点，不感知文件布局。

## 4. 与 CLAUDE.md 的耦合点

CLAUDE.md 新增一条规则（措辞落地时定）：当 mailbox 收到 AI-Informer 的新资讯写入、或 Tom 显式要求做选题筛选时，主 agent 拉起 `ideas-recommender` subagent 完成筛选并写入对应当天的 `data/ideas/YYYYMM/DD.json`，主 agent 自身不直接做评分判断。

## 5. 暂不做

- 给 AI-Informer 的反馈闭环本期不实现。
- 不做 ideas 评分历史可视化（现有面板已经按分数分组）。

