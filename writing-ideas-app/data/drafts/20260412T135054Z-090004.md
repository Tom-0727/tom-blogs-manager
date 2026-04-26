---
title: "Agent 的 Continual Learning"
date: 2026-04-12 21:00:00
updated: 2026-04-12 21:00:00
tags: [agent-engineering, agent-architecture, learning]
categories: [Agent Engineering]
description: "从实践出发拆解 Agent Continual Learning 的三层框架 -- Model、Harness、Context，结合 Long-Run Agent 实际系统说明工程上最值得投入的学习层次。"
---

## 为什么写这篇

最近读到 Harrison Chase（LangChain 创始人）写的 [Continual Learning for AI Agents](https://blog.langchain.com/continual-learning-for-ai-agents/)，讨论 Agent 如何在运行过程中持续变强。他提出了一个三层框架：Model、Harness、Context，分别对应不同层面的 Learning。

这个话题我一直在关注。2025 年初做 Self-Evolving Agent 相关调研的时候，就已经看到类似的三层优化框架 -- 只不过当时 Harness 更多叫 Code。现在 Harrison 用更工程化的语言重新梳理了这件事，加上我自己也在做 Long-Run Agent Harness，正好结合实践写一篇。

## 三层 Learning 框架

Harrison 把 Agent 的 Continual Learning 分成三层：

- **Model Layer** -- 模型权重本身的更新，通过 SFT、GRPO 等方式微调。
- **Harness Layer** -- 模型周围的代码和基础设施，包括 prompt 模板、工具编排、执行流程。
- **Context Layer** -- Agent 运行时可以读取的外部指令、技能、工具定义，可以按 Agent / 用户 / 组织维度定制。

前面提到，这个划分不算全新 -- 2025 年的 Self-Evolving Agent 研究就有类似的三层优化目标。Harrison 的价值在于他用了更多工程实例把这个框架讲清楚了，而且给出了具体的实现路径。

他举的例子很直观：Claude Code = Claude-Sonnet（Model）+ Claude Code 应用代码（Harness）+ CLAUDE.md 和 Skills（Context）。OpenClaw 也类似 -- 模型 + Pi scaffolding（Harness）+ SOUL.md 和 clawhub skills（Context）。

## 对应到我的实际系统

我用自己搭建的 Long-Run Agent Harness 来看这三层，每一层都有非常具体的对应。

### Model Layer：不做微调，依赖基座能力

坦率地说，我在 Model 层没有做任何 Learning。我的 Agent 直接使用 Claude 的基座能力，没有微调。

原因很务实 -- Harrison 也提到了 Model Layer Learning 的核心挑战：catastrophic forgetting。微调一个能力可能损害其他能力，而且对个人开发者来说，微调的基础设施成本和数据要求都太高了。我选择把精力花在更可控的层面。

### Harness Layer：heartbeat、episode、evaluator

这是我投入最多的一层，也是我认为当前最能体现"Agent 在学习"的一层。

先说整体结构。我的 Harness 核心是一个 heartbeat 驱动的执行循环 -- Agent 被定期唤醒，每次唤醒执行一个完整的 episode。每个 episode 由三个阶段组成：plan、execute、evaluate。这不是随意设计的，而是参考了 Anthropic 在 [Harness Design](https://www.anthropic.com/engineering/harness-design-long-running-apps) 中提出的三 Agent 模式（Planner / Generator / Evaluator）。

为什么需要 evaluator？因为 Agent 天然有"自我满足"的倾向 -- 做完就觉得做好了。evaluator 的作用是在每个 episode 结束时独立审视执行结果，给出 PASS 或 FAIL 的判定。如果 FAIL，Agent 必须根据 evaluator 给出的 required_fixes 进行修正，最多迭代三轮。这个机制本质上就是 Harness 层面的反馈学习 -- 不改模型权重，但通过结构化的约束和反馈，让同一个基座模型产出更高质量的结果。

再说 episode 记录。每个 episode 会产生一份结构化的执行记录：objective、actions taken、key evidence、outcome、reflection。Harrison 在文章里强调 traces 是所有层面 Learning 的基础 -- 我的 episode 记录本质上就是一种 trace。它不仅是复盘的依据，还是后续优化的数据源。比如，多次 episode 的 reflection 中如果反复出现类似的失败模式，就说明 Harness 的某个流程需要调整。

Harrison 还引用了 Meta-Harness 论文来说明系统化的 Harness 优化方法：运行 Agent → 收集 trace → 评估结果 → 用 coding agent 建议改进。我的实践路径和这个思路基本一致 -- evaluator 分析 episode 记录，发现需要优化的点，然后触发 skill 沉淀或 Harness 规则更新。

在之前的文章[《OpenClaw 不是终点》](/2026/04/08/agent-engineering/openclaw-is-not-the-end/)里，我详细讨论过这套 Harness 的设计动机和架构选择，感兴趣的可以看看。

### Context Layer：CLAUDE.md、Skills、Knowledge

Context Layer 的 Learning 在我的系统里是最直观的：

CLAUDE.md 作为 Agent 的行为规则文件，随着实践不断演化 -- 新的 SOP 被加入，旧的规则被修正。Skills 从重复出现的工作模式中结晶出来，变成可复用的能力模块。Memory/knowledge/ 存储从多次 episode 中提炼的长期知识。

Harrison 区分了两种 Context Learning 的路径：**offline**（通过 trace 分析离线优化，比如 OpenClaw 的 "dreaming" 机制）和 **hot-path**（运行时实时更新记忆）。我的系统两种都有 -- evaluator 触发的 skill 沉淀和 knowledge 更新是偏 offline 的，而 episode 执行中的即时记录是 hot-path 的。

## 工程上的判断

读完 Harrison 的文章，结合自己的实践，我的判断是：**对绝大多数实际场景来说，Harness 和 Context Layer 的 Learning 投入产出比远高于 Model Layer。**

这不是说 Model Layer 不重要 -- 基座模型的能力决定了天花板。但从工程落地的角度看，我们能直接改进和控制的是 Harness 的执行流程和 Context 的知识积累。这两层的优化周期更短、反馈更快、风险更低，而且效果是可以叠加的。

Harrison 在文章里也强调了一个关键点：traces 是所有层面 Learning 的基础。不管是用 trace 来微调模型、优化 Harness，还是分析 Context 的效果，都需要先把 trace 收集好。这和我在 episode 设计上的思路完全一致 -- 先记录，再提炼，最后才是改进。

## 一点展望

Continual Learning 对 Agent 来说不是可选项，而是长期运行的必要条件。一个不能学习的 Agent，本质上就是一个需要人类不断手动更新的工具。

好消息是，从 Harrison 的框架可以看出，Agent 的 Learning 不一定要从最难的 Model Layer 开始。Harness 和 Context 层面的持续优化，已经能带来非常实际的能力提升。对于正在做 Agent 工程的人来说，这可能是当下最值得投入的方向。
