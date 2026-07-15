---
name: verbatim-script-style
description: Write or rewrite technical and knowledge-sharing verbatim scripts in the user's personal style. Use when the user asks to create a 逐字稿, 分享稿, 技术分享文稿, 知识分享讲稿, or to make draft content sound like their own speaking style, especially when they want emphasis on language style, logic preference, oral delivery, reasoning flow, and non-generic explanation.
---

# Verbatim Script Style

## Overview

Use this skill to produce scripts that sound like the user's own technical sharing style: oral, first-person, reasoning-led, and explicit about why the explanation is arranged this way. The goal is not to force a fixed structure, but to preserve the user's language habits and logic preference across different topics.

## Core Style

Write like a person thinking aloud in a technical sharing session.

- Prefer clear oral explanation over polished article prose.
- Use first person naturally: "我觉得", "我会先", "从我的视角", "这里我想先", "分析到这里".
- Use explicit transition phrases so the audience can follow the speaker's current position: "首先", "然后", "另外", "但是", "基于前面的分析", "总结一下", "接下来".
- Allow medium-length sentences when they carry reasoning. Do not over-compress into slogans or bullet-only summaries.
- Keep the tone exploratory and defensible instead of absolute. Use "可以理解为", "可能", "是否", "我倾向于", "这里需要先弄清楚" when the topic involves interpretation or tradeoffs.
- Make the script suitable to be spoken directly. Avoid dense written phrasing, academic stiffness, marketing language, or generic inspirational openings.

## Logic Preference

Prefer a reasoning path over a knowledge list.

- Start from the problem, not from a concept catalog: "为什么需要这个东西", "它要解决什么问题", "如果没有它会怎样".
- Establish a simple understanding frame before details: positioning, boundary, target, assumptions, or the key question being answered.
- Use causal chains: "因为 A，所以出现 B；B 又带来 C；所以需要 D".
- When explaining an existing design, ask why it looks this way: what constraints, alternatives, and tradeoffs may have led to it.
- Prefer showing the speaker's thinking path before giving the final answer.
- Convert concrete details into a reusable model near the end when possible. The model can be a short formula, sequence, or abstraction.
- Explicitly mark scope and omissions when useful: what this sharing covers, what it intentionally does not cover, and why.

## Writing Workflow

When writing a new script:

1. Identify the audience and the actual sharing goal.
2. Extract the central question the talk should answer.
3. Draft a spoken opening that states the topic, goal, and optional scope boundary.
4. Build the body as a chain of questions and causes, not as a flat outline.
5. Insert first-person reasoning markers where the user would naturally explain their thinking.
6. Close each major section with a small summary or abstraction before moving on.
7. Review for speakability: sentences should be easy to read aloud, transitions should be explicit, and every paragraph should advance the reasoning.

When rewriting existing material:

- Preserve the source facts and conclusions unless asked to change them.
- Reorder material around the reasoning path if needed.
- Replace article-like wording with oral first-person explanation.
- Add missing "why this matters" and "why I explain it this way" transitions.
- Remove empty formalities, buzzwords, and generic background that does not help the listener follow the speaker's thought process.

## Reusable Skeleton

Use this only as a flexible skeleton. Do not force every topic into every section.

```text
今天想分享的主题是【主题】。

这次我主要想回答【核心问题】。如果把这个问题拆开看，其实有几个点需要先弄清楚：【问题一】、【问题二】、【问题三】。

这里我先说明一下范围。【会讲什么】；【暂时不讲什么】，原因是【原因】。

在进入细节之前，我想先从我的视角把这个问题重新推一遍。因为如果直接看【实现/结论/现象】，很容易先入为主，觉得它天然就应该这样。但实际上更重要的是先弄清楚：为什么会有这个问题？

首先，【背景或前提】。在这个前提下会出现一个问题：【问题】。

因为【原因 A】，所以【结果 B】。而【结果 B】又会带来【新的约束或机会】。所以分析到这里，【主题】要解决的问题就比较清楚了。

但是这里不能简单理解成【过度简化的说法】，因为还存在几个复杂点：【复杂点】。

基于前面的分析，我们再来看【实现/方案/方法】，就会更容易理解它为什么是现在这样。

总结一下，我觉得这个问题可以抽象成：【抽象模型】。

这个模型里最关键的点是【关键难点】。后面如果要继续优化或者排查，也应该围绕这个点展开。
```

## Avoid

- Do not make the script sound like a formal article, PRD, or slide notes.
- Do not overuse headings and bullets unless the user asks for an outline.
- Do not assume the topic must be architecture-related. Apply the same reasoning style to operations, product knowledge, source-code reading, troubleshooting, methodology, or any knowledge-sharing topic.
- Do not erase uncertainty. If the source material contains judgment or possible tradeoffs, keep the exploratory tone.
- Do not invent facts to complete the reasoning chain. Mark missing facts as assumptions or ask for the needed context when the gap would change the conclusion.
