---
name: test-case-design
description: |
  Turn a requirement document, PRD, or API spec into a machine-checkable test case set: split the text into atomic requirement items, generate cases with equivalence partitioning / boundary value analysis / decision table / state transition / orthogonal design, then emit case JSON plus a requirement-to-case traceability matrix.
  Use this skill when the user asks to "写测试用例"、"设计测试用例"、"拆测试点"、"补充边界用例"、"做需求覆盖分析"、"generate test cases", or pastes a requirement and asks what should be tested.
  Also use it to check an existing 用例集 for schema violations and requirement gaps.
  Do NOT use it for executing tests against a live system (接口压测、UI 自动化、跑测试脚本)、for writing 缺陷单 or 质量报告, or for code review — those are separate workflows.
---

# Test Case Design

把需求文本变成可校验的用例集，交付两样东西：用例 JSON（机器可消费）和追溯矩阵（证明每个需求条目都被覆盖）。

## Inputs to collect

先确认这些再动手；缺哪一项就用下面的追问补齐：

- **需求原文**：用户粘贴、文件路径或文档引用。只说"帮我写用例"却没给需求时，先要原文——没有原文就没有可拆解的条目，产出的用例集看起来完整，实际覆盖的是模型自己的臆测。
- **被测对象与交互方式**：REST API、Web UI、CLI、批处理任务、规则引擎……这决定步骤写"发起请求"还是"点击按钮"，也决定哪些覆盖维度适用。
- **需求条目与用例的编号起点**：`R-1`、`TC-001` 是否与既有资产冲突。
- **优先级口径**：P0 在这个团队代表什么（阻断主流程？资损？数据安全？）。各团队口径差异极大，照搬默认会让 P0 失去筛选意义。
- **范围边界**：本次覆盖哪些端/模块/角色；哪些明确不在本次范围。
- **环境前提**：预发环境、测试账号、依赖的外部系统——它决定 `preconditions` 与用例是否可执行。
- **已有材料**：历史用例、数据字典、接口契约，能对齐格式和命名就复用。

## Procedure

1. **收集并确认需求输入**（粘贴文本 / 文件 / 文档）。
   原因：需求原文是唯一事实来源；先确认它再拆条目，能避免后面整批返工。

2. **把需求拆成原子条目 `R-1, R-2, ...`**，每条记录 `title`、原文摘录（`source_ref`）与来源位置。
   原因：原子条目是覆盖的最小单位；条目太粗会掩盖缺口，太细则无法对应一句需求。带上原文摘录，后续被质疑"这条用例从哪来的"时可以直接回溯。

3. **判定每条是否可测试**，`testable` 置 false 的（背景叙述、目标声明、术语解释）单独归类，不强行生成用例。
   原因：给不可测项编用例只会制造覆盖率的假象，让真正的缺口被淹没。

4. **为每个可测试点选适用的设计方法**（等价类、边界值、判定表、状态迁移、正交、场景法），选择依据见 `references/design-methods.md`。
   原因：凭直觉罗列用例容易只覆盖"顺利路径"；每种方法对应一类系统性遗漏，选方法等于决定这轮能发现哪类缺陷。

5. **按覆盖维度清单补齐**：功能 / 边界 / 异常 / 权限 / 数据 / 并发 / 性能 / 兼容，清单与维度取值见 `references/coverage-dimensions.md`。
   原因：维度清单是查漏网用的统一视角，每个维度都问一遍"这一条适用吗"，比凭经验想更容易发现被忽略的维度。维度不适用的，在报告里写明理由，不要静默跳过。

6. **按 `references/case-schema.md` 产出用例 JSON**：编号 `TC-001` 递增，每条用例写清 `action` 与 `expected`，`requirement_refs` 指向它验证的条目。
   原因：`expected` 写不出可判定结果的用例，等于没有验证点，后续执行时也无法判断通过与否。

7. **运行校验脚本**，不通过就修复后重跑：
   ```
   node scripts/validate-cases.mjs cases.json
   ```
   原因：JSON 里的错漏（ID 重复、悬空引用、枚举取值写错）靠肉眼看几乎必然漏掉；脚本的退出码是"能不能交付"的客观门槛。

8. **渲染报告与追溯矩阵**：
   ```
   node scripts/render-report.mjs cases.json
   ```
   原因：追溯矩阵是向需求方证明"每条需求都有用例"的凭据，也是暴露覆盖缺口的唯一视图。

9. **汇报覆盖情况**：给出需求条目总数、可测试条目数、用例总数、维度分布，并明确列出**未被覆盖的需求条目 ID** 与**未决问题**（需求本身的歧义、缺失的前置条件、口径未确认的点）。
   原因：发现需求缺陷是这套流程的主要价值之一；把歧义写成自己的假设会让缺陷永久消失，而假设一旦被下游当成需求，就再也找不回来了。

## Output contract

- **用例集 JSON**（单个文件），结构与字段语义见 `references/case-schema.md`：
  - `meta`：`source`（需求来源标识）、`generated_at`（ISO-8601）、`case_count`（用例总数）
  - `requirements[]`：`id`、`title`、`source_ref`、`testable`
  - `cases[]`：`id`、`title`、`requirement_refs`、`dimension`、`priority`、`preconditions`、`steps[{action, expected}]`、`data`、`tags`
- **Markdown 报告**（`render-report.mjs` 的 stdout）：用例总览表、追溯矩阵（需求条目 → 覆盖用例 ID → 覆盖状态）、未覆盖需求条目清单。
- **覆盖汇报**：未覆盖需求条目 ID 列表 + 未决问题列表，两项都不能省略。

## Failure handling

- **校验脚本报错**：按它列出的问题逐条修 JSON，修完重跑再交付。连续两轮仍有同类错误，说明生成逻辑（例如维度映射、编号规则）有偏差，先回看 `references/case-schema.md` 与 `references/coverage-dimensions.md`，不要继续手改 JSON。
- **需求有歧义或缺前置条件**：写进未决问题清单，列出你的两种以上可能理解与各自影响，请需求方裁定；不要自行选定一种然后当成既定事实。
- **需求条目拆不出来 / 粒度明显不对**：回到第 2 步重新拆，或请用户补充上下文。用例集对不上需求原文时，多半是条目拆错了，而不是用例写得少。
- **某个维度确实不适用**（如纯离线批处理任务没有并发语义）：在报告里写明"该维度不适用 + 理由"，让不覆盖成为显式决定而不是空白。
- **文件读不到 / JSON 语法错误**：原样把错误信息报给用户并停止，不要凭空修补一个损坏的用例集。
- **覆盖缺口过大**（多数可测试条目没有用例）：说明缺的是输入信息还是设计工作量，并给出补齐建议，而不是交付一个"结构合法但覆盖稀薄"的集合。

## Examples

输入（需求原文片段）：

> 用户密码最少 8 位，最多 20 位，必须同时包含字母和数字；连续 5 次输错锁定账号 15 分钟。

拆解与产出要点：

- 需求条目：`R-1` 密码长度 8–20 位；`R-2` 必须含字母与数字；`R-3` 连错 5 次锁定 15 分钟。
- `R-1` 用边界值法生成 `boundary` 维度用例：长度 7（拒绝）、8（接受）、20（接受）、21（拒绝）。
- `R-2` 用等价类 + 判定表生成 `functional` 维度用例：纯数字、纯字母、字母+数字；规则组合用判定表覆盖"只有字母""只有数字""两者都有"。
- `R-3` 用状态迁移生成 `exception` 维度用例：错误次数 4→5 的迁移点、锁定后第 6 次输入、15 分钟到期后第 1 次输入。
- 交付前跑 `node scripts/validate-cases.mjs cases.json` 与 `node scripts/render-report.mjs cases.json`，把追溯矩阵里"未覆盖"一栏为空的结果连同未决问题一起交给需求方。

## Windows (win32) platform notes

- 两个脚本都是纯 Node.js，直接用 `node scripts/validate-cases.mjs cases.json` 调用，PowerShell 与 cmd 下行为一致。
- 路径交给 Node 解析（脚本内部走 `path.resolve`），不要写死盘符或类 Unix 绝对路径。
- 临时文件放在当前工作目录下的子目录里（例如 `./tmp-cases/`），不要假定系统存在类 Unix 临时目录。
