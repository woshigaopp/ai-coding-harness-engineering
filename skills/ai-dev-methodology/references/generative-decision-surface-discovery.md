# Generative Decision Surface Discovery

本文件记录一个对 `decision-surface-discovery` 悖论的补充思路。

## Contents

- [Problem](#problem)
- [Two Kinds Of Surfaces](#two-kinds-of-surfaces)
- [Generative Surface Tests](#generative-surface-tests)
- [Workflow Implication](#workflow-implication)
- [Retrospective Rule](#retrospective-rule)

## Problem

经验型决策面发现能改善大需求 workflow，但它有一个悖论：

```text
AI 要发现决策面，依赖提前抽象；
但提前抽象本身，又依赖人已经经历过这类失败。
```

例如 `auto-create`、`select-existing`、`managed resource`、`runtime mode` 这些触发器已经是人类从历史需求和收敛事故中抽象出来的经验。它们有效，但不可能一次性完备。新的需求形状出现时，AI 仍可能不知道该展开哪些决策面。

因此目标不应是提前抽象所有可能的决策面，而是：

```text
不要求经验库完备；
要求每次需求进入 workflow 时，AI 能系统性制造新的候选决策面。
```

经验库应当作为种子，而不是答案库。真正需要补上的，是从需求本身生成未知 surface 的机制。

## Two Kinds Of Surfaces

可以把决策面分成两类：

| Type | Meaning | Role |
|---|---|---|
| Experience-shaped surface | 来自历史失败和人类工程直觉的问题形状，例如 managed resource ownership、frontend action-flow、runtime materialization parity | 命中高频已知坑 |
| Generative surface | 通过系统性压力测试从当前需求生成的候选决策面 | 发现经验库未覆盖的未知坑 |

经验型 surface 解决“以前踩过的坑不要再踩”。生成型 surface 解决“没踩过的坑如何被看见”。

## Generative Surface Tests

### 1. Consumer Enumeration Stress Test

不要先问“这个需求涉及哪些决策”，而是问：

```text
这个改动之后，哪些既有 consumer 会继续读取、展示、操作、验证它？
```

典型 consumer 包括：

- list
- detail
- progress
- logs
- metrics
- delete
- update
- retry
- permission
- mock
- acceptance
- observability
- billing / capacity if relevant

每个 consumer 都要问：

```text
它看到的新对象、新状态、新资源或新 mode 是否仍然成立？
如果不成立，是 unsupported、hidden、disabled、fallback、error，还是需要新 provider guarantee？
```

回答不上来时，产生 candidate decision surface。

### 2. Mutation Stress Test

只要需求让系统状态发生变化，就套一遍：

```text
before -> mutation -> after -> readback -> later action -> cleanup
```

每一段都可能产生未知 surface：

- mutation 写了什么？
- 谁是 authoritative state owner？
- after 状态谁读？
- later action 是否依赖它？
- cleanup 是否需要反向操作？
- partial failure 是否留下 residual state？

这个测试不依赖 `auto-create`、`runtime mode` 等关键词。只要有 create / update / delete / save / resize / scale / import / bind 等 mutation，就应执行。

### 3. Invariant Breakage Stress Test

问一个更泛化的问题：

```text
这个需求会不会让旧系统里某个“默认总为真”的假设不再成立？
```

例子：

- 以前某字段总存在，现在可能不存在。
- 以前某资源总是用户提供，现在可能系统创建。
- 以前创建成功就代表可运行，现在创建成功只是配置保存。
- 以前某页面所有 mode 共用，现在某 mode 不支持。
- 以前某 API 返回完整 runtime 状态，现在只能返回 unknown / unavailable / warning。

每个被打破的 invariant 都必须产生 decision / contract / verification / locked N/A。

### 4. Lifecycle Completeness Stress Test

对任何产品对象、运行时对象、外部资源、配置对象或用户可见实体，都套一遍：

```text
create / read / update / operate / observe / fail / delete
```

如果某个环节回答不上来，不是补实现，而是生成 candidate decision surface。

这个测试尤其适合发现创建后能力缺口，例如创建后 logs、metrics、workers、events、delete、update、retry、permission、observability 是否成立。

### 5. Reverse Acceptance Stress Test

从最终验收倒推：

```text
如果我要证明这个需求真的完成，我需要看到什么证据？
```

如果证据需要跨模块，反推出 contract surface。
如果证据需要外部行为，反推出 side-effect surface。
如果证据需要浏览器动作，反推出 frontend action surface。
如果证据无法本地证明，反推出 Not Run / mock boundary / repo-specific acceptance runtime surface。

proof 缺失通常能暴露设计缺失。

## Workflow Implication

`decision-surface-discovery.md` 不应只由经验触发器填充。它应同时消费两类输入：

```text
experience-shaped triggers
  + consumer / mutation / invariant / lifecycle / acceptance stress tests
  -> candidate decision surfaces
  -> owner stage
  -> DEC / C / VER / Txxx / locked N/A / blocked backflow
```

这样悖论仍然存在，但会变弱：

- 不要求人提前抽象所有 surface。
- 只要求人维护少量能生成 surface 的压力测试。
- 新失败如果可泛化，再沉淀为新的 experience-shaped trigger。

## Retrospective Rule

每次 convergence retrospective 中，如果发现漏掉了一个决策面，先判断它属于哪类：

| Finding | Action |
|---|---|
| 已有 experience-shaped trigger 应该命中但没命中 | 修 trigger、artifact 或 validator |
| pressure test 本应生成 candidate surface 但没生成 | 修 generative surface test |
| 当前 pressure test 也无法自然发现 | 判断是否是新的可泛化 experience-shaped trigger |
| 只适用于本需求 | 写入本需求 DEC/C/VER，不进入方法论 |

这个规则的目标是避免经验库无限膨胀成案例碎片，同时让未知 surface 有生成入口。
