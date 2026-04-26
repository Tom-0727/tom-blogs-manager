---
title: "Claude Code 做决策，Codex 做执行 -- 双 Provider Agent Harness 的调研与思考"
date: 2026-04-15 22:00:00
updated: 2026-04-15 22:00:00
tags: [agent-engineering, agent-architecture, claude-code]
categories: [Agent Engineering]
description: "调研 Claude Code 和 Codex 在 Agent Harness 中的角色分工 -- 一个做决策，一个做执行。从数据和实践出发，聊聊双 Provider 架构的可能性和局限。"
---

最近在做 Long-Run Agent Harness 的过程中，我一直在想一个问题：**一个 Agent 系统里，决策和执行是不是可以用不同的 Provider？**

实践中我注意到，Claude Code 在规划和判断上表现很好，但让它从头到尾把一个大任务全部执行完，Token 消耗确实比较大。而 Codex 在拿到明确 spec 之后的执行效率又很高。于是我做了一轮调研，想看看 **Claude Code 负责决策，Codex 负责执行** 这个思路是不是合理的。

## Claude Code：规划和判断上的优势

先看数据。Claude Code 在 agentic coding 方向上的指标确实不错：

| 指标 | 数据 |
|------|------|
| SWE-bench Verified | 80.8%（当前 SOTA） |
| Context Window | 1M tokens |
| 开发者偏好（15000 人调研） | 46% 首选 |
| 长链推理稳定性 | 优秀 |

在做架构判断、方案拆解、任务拆分这些偏决策的事情上，Claude Code 目前应该是最强的选择之一。它的长上下文理解和推理链条比较稳定，适合处理需要全局视角的工作。

不过一个比较现实的问题是，**Token 消耗比较大**。如果一个任务既需要想清楚怎么做，又需要逐行把代码写完，全交给 Claude Code 的话，成本会比较高。这也是我想看看能不能把执行层拆出去的一个动机。

## Codex：执行层的效率与前提

再看 Codex。它的定位和 Claude Code 不太一样 -- 更偏向一个**面向明确任务的执行引擎**。

| 指标 | 数据 |
|------|------|
| 成熟任务成功率 | 85-90% |
| 持续执行时长 | 最高 25 小时 |
| Token 消耗（vs Claude） | 约 1/3 到 1/4 |
| Terminal-Bench | 77.3% |

数据上看，Codex 在拿到明确 spec 后的执行效率和成本优势是比较明显的。

但这里有一个关键前提：**Codex 比较依赖结构化的 spec 文件。** 需要给它 `Prompt.md`、`Plan.md` 这类冻结好的任务描述，它才能发挥得好。如果任务本身是开放式的 -- 比如"这个模块该不该拆"、"这个方案怎么选" -- Codex 在这类需要架构判断的场景下表现就一般了。

换句话说，**任务越结构化、边界越清晰，Codex 的优势越明显；任务越开放，退化越明显。** 它不太适合做决策，但很适合执行别人做好的决策。

## 分工编排的思路

基于上面的观察，我觉得 Claude Code 和 Codex 之间存在一种比较自然的分工可能：

- **Claude Code 负责决策层** -- 做任务理解、方案拆解、风险预判，输出结构化的 Plan
- **Codex 负责执行层** -- 拿到 Plan 之后按 spec 高效执行，成本更低

这两者的能力边界确实比较互补。Claude Code 擅长的全局思考和判断，正好是 Codex 相对弱的地方；而 Codex 的执行效率和成本控制，又是 Claude Code 的短板。

不过也不是所有场景都能直接套这个模式。Codex 对 frozen spec 的依赖意味着，**决策层输出的质量直接影响执行层的效果。** 如果 Claude Code 给出的 Plan 有歧义或者遗漏，Codex 不太会帮你兜底 -- 它更倾向于忠实地按照 spec 执行。

另外，这两个 Provider 之间目前没有原生的协议层。状态同步、错误回传、中途修正这些，都需要在 Harness 层面自己处理。

## 我的判断

调研下来，"Claude Code 做决策 + Codex 做执行" 这个思路我觉得是有道理的，但需要一些前提条件。

核心在于 Codex 对开放式任务的决策能力确实比较弱，它需要一个好的决策层来给它喂结构化的输入。Claude Code 目前在这个位置上是比较合适的。但反过来说，这也对 Harness 本身的编排能力提出了要求 -- 怎么把 Claude Code 的判断转化成 Codex 能消费的 spec，这个环节比较关键。

务实地说，我目前还在跑通和验证的阶段。后续有更多落地经验了再做整理。如果你也在做类似的 Agent 架构探索，欢迎交流。
