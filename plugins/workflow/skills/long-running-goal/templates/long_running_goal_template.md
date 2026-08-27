# Long Running Goal Template

本文件是 continuation-ready long-running goal 文档模板。使用时复制到项目的 active goal directory，例如 `<goal-dir>/<goal_slug>_long_running_goal_plan.md`，再替换所有 `<...>` 占位符；不要直接在本模板中记录具体任务进度。

整体状态：`Draft`

## 使用说明

1. 先确认项目已有的 planning root 和 goal directory。`<planning-root>` 是更大的文档/计划树；`<goal-dir>` 是直接存放 active goal 文件的目录。不要对已经是 goal directory 的路径再追加 `/todo`。
2. 复制本文件到目标计划路径，例如：

```bash placeholder-example
cp <skill-folder>/templates/long_running_goal_template.md <goal-dir>/<goal_slug>_long_running_goal_plan.md
```

3. 创建或执行实现前先应用 `components/planning-preflight.md`：默认先运行 `grill-with-docs` 确定具体实施方案；只有用户显式表示不需要 grill 时才跳过，并在本文件记录 skip。无论是否跳过 grill，都必须完成 preflight time assessment，并让用户显式选择 Close 是否使用 `watcher:housekeeping` 清理任务临时缓存。
4. 将标题、目标描述、目标路径、Planning preflight marker、Preflight Time Assessment、任务临时缓存 / housekeeping 合同、Loop Blueprint、阶段名称、验证命令和 checkpoint evidence 替换为当前任务内容。
5. “阶段状态表”是 lifecycle 状态的汇总事实源；若阶段正文也写 `状态`，必须与表中对应行一致。`Done` 行必须同时为 `Review=Passed`、`Checkpoint=Done`，`Closed` 时所有阶段和 Close 行均须完成。
6. 执行过程中只更新复制后的 goal 文件，不更新本模板。
7. 每个阶段完成后必须补齐代码证据、行为证据、测试证据、文档证据、回滚证据和剩余风险。
8. 按任务规模增删 `M<N>` 阶段；删除不用的阶段，按顺序新增需要的阶段，并同步更新阶段状态表、Checkpoint evidence、Close Gate 和推荐 Goal Prompt。
9. Close 前必须确认所有阶段 `Done`，并记录最终验证结果；归档后用 `check_todo_index.py --mode closed --archived-goal ...`，无归档删除时用 `--mode absent` 验证 active 导航清理。

## Goal 摘要

目标名称：`<Goal Name>`

目标描述：

1. `<用 1-3 条描述本 goal 要完成什么。>`
2. `<说明最终用户或系统行为的目标态。>`
3. `<说明不属于本 goal 的边界。>`

目标状态：`Draft`

目标 owner：`<owner / team / agent>`

目标路径：`<goal-dir>/<goal_slug>_long_running_goal_plan.md`

Planning root：`<planning-root>`

Goal directory：`<goal-dir>`

Continuation contract：`<同一或另一个 agent 不依赖聊天历史即可从本文件继续执行的关键约束。>`

Planning preflight marker：`<preflight:<goal_slug>:<yyyymmdd>-<short-id> / preflight:<goal_slug>:skip:<yyyymmdd>-<short-id>>`

Planning preflight status：`<Done / Skipped by explicit user instruction>`

Preflight source：`<grill-with-docs / user skip>`

Resolved decisions：`<summary or doc paths>`

Open decisions：`<none or explicit runtime hard stops>`

Docs written：`<CONTEXT.md / ADR paths / Not applicable>`

## Preflight Time Assessment

Assessment target：`<Ready-to-Closed / current-milestone-to-Closed>`

Assessment mode：`<Rough range / Distribution only>`

Rough elapsed-time estimate：`<low-high with unit / Not quickly estimable>`

Basis or blocker：`<YYYY-MM-DD evidence or blocker, external-wait scope, and serial/parallel assumptions>`

Critical-path time-cost distribution：`<Not required: rough range recorded. / at least two rows shaped: - driver — Dominant/Material/Minor/Unknown — reason>`

## Task Temporary Cache / Housekeeping

Close housekeeping policy：`<Enabled / Disabled / Not applicable>`

Housekeeping decision source：`<explicit user confirmation with date or turn context>`

Task temporary cache root strategy：`<Enabled/Disabled: resolve the host platform/runtime standard temporary root, allocate a goal-owned namespace beneath it, and record the exact owner root before first use; Not applicable: no task temporary cache root will be created.>`

Recorded task temporary cache roots：`<one fully resolved owner-labeled absolute path entry per root / Resolve and record before first use / None created / Not applicable>`

Housekeeping boundary：`<Enabled uses watcher:housekeeping only for inventoried task-owned disposable candidates; Disabled preserves and reports; Not applicable creates no root; durable evidence lives outside the roots.>`

## M0 执行前基线

M0 设计冻结时的当前基线：

1. `<当前代码 / 文档 / runtime 的事实 1。>`
2. `<当前已交付或已验证的能力。>`
3. `<当前仍保留的 compatibility / legacy surface。>`
4. `<当前主要失败断点或风险。>`
5. `<当前不属于本计划提交范围的运行产物或外部依赖。>`

已读取的当前事实源：

1. `<root instructions / AGENTS.md / README / current guide / status doc。>`
2. `<相关 architecture / contract / validation / runbook。>`
3. `<现有 TODO / goal / archive / issue / PR。>`

## Loop Blueprint / Harness 边界

如果本 goal 是手动分阶段执行，明确写 `Not applicable: manual staged execution` 并说明原因。若本 goal 包含自动触发、重复循环、sub-agent 编排、worktree 并行、connector 读写或外部系统副作用，必须在执行前冻结以下 harness 边界，不能等执行过程中只依赖 LLM 自行判断。

执行模式：`<Manual staged execution / Loop-shaped execution / Automated loop>`

1. Trigger / 心跳：
   - `<什么事件启动或恢复循环；例如用户命令、schedule、hook、CI、issue、goal-tool。>`
2. Inputs / 输入源：
   - `<循环读取哪些事实源；例如 TODO index、issue、CI log、report、runtime state、checkpoint evidence。>`
3. Triage and orchestration / 分拣与编排：
   - `<finding 如何变成任务，优先级如何确定，哪些角色或 agent 负责探索、实现、验收。>`
4. Worktree and isolation / 隔离策略：
   - `<是否使用当前 checkout、独立 worktree、独立 branch、串行锁定文件，或其他防撞策略。>`
5. Skills and context / 必读上下文：
   - `<每个角色必须读取的 skill、runbook、project doc、spec 或历史决策。>`
6. Connector read/write boundaries / 外部系统读写边界：
   - `<可读/可写的 connector、API、ticket、PR、CI、Slack 等；哪些写入已预授权；哪些未预授权写入会让本 goal 保持 Draft。>`
7. Independent verification / 独立验收：
   - `<由哪个 sub-agent、脚本、测试、reviewer 或 gate 检查 producer 的输出；不得只信自评。>`
8. Runtime hard stops / 运行时硬停止：
   - `<只有哪些技术失败、缺失凭据/事实源、隐私、破坏性动作、未预授权外部写入或连续阻塞会真正停止循环并询问用户；普通 gate / checkpoint / rebuild / refresh / 可本地修复失败不应列为停止点。>`
9. Durable learning / 经验沉淀：
   - `<哪些结果要写回 skill、TODO、report、validation log、runbook、automation memory 或 current doc。>`

## Pre-Approval / YOLO 边界

Ready 前必须冻结 approval 模型；若存在可预见但未确认的 approval 点，本 goal 保持 `Draft`，不得执行到中途再询问。

1. Pre-approved YOLO local operations / 预授权本地操作：
   - `<本 goal 范围内默认允许的非破坏性本地动作，例如 code/docs/source skill edits、rebuild、refresh、reinstall、dependency restore、tests、lint、formatting、link checks、plugin/cache refresh、project-owned generated-artifact cleanup；不要在此处推导任务临时缓存清理授权。>`
2. Pre-approved external reads/writes / 预授权外部读写：
   - `<已允许读取或写入的 connector、API、issue、PR、CI、automation、hook、message surface；无外部写入时写 Not applicable。>`
3. Runtime hard stops / 运行时硬停止：
   - `<仅列真正会停止执行的条件：本地诊断/修复至少三次或三种方式后仍无法继续、缺少 agent 无法本地取得的凭据/文件/事实源、下一步破坏性/不可逆/隐私敏感/外部可见且未预授权、事实源冲突会改变冻结语义、必需 sub-agent/connector/worktree/verifier 失败且无计划内本地下一步。>`
4. Non-stops / 不应中断的事项：
   - `<普通阶段边界、checkpoint、耗时区间超出后的 rebaseline、可记录风险、rebuild、refresh、reinstall、失败但有明确本地下一步的验证、策略合同更新、docs sync 等。>`

## Goal 执行合同

如果本计划被作为 long-running goal 执行，必须按以下合同推进：

1. 执行实现前必须已有 Planning preflight marker 和合格的 Preflight Time Assessment：默认来自 `components/planning-preflight.md` / `grill-with-docs`；只有用户显式跳过 grill 时才记录 skip marker，但 timing 仍必须完成。若 marker 已存在且状态为 `Done` 或 `Skipped by explicit user instruction`，不得重复运行 grill；resume 只快速刷新 timing evidence。
2. 阶段必须顺序执行：`M0 -> M1 -> M2 -> ... -> Close`。
3. 每个阶段开始前必须把阶段状态改为 `In Progress`。
4. 每个阶段完成后必须记录 review 结论、运行命令、通过证据、失败断点和未解决风险。
5. 每个阶段必须应用 `components/checkpoint.md` 并记录 checkpoint evidence。若项目已有 Git / version-control 工作流且用户或项目要求阶段性提交，优先使用本计划中记录的 `<goal_slug> M<N>: <summary>` 或本项目约定格式作为 commit/revision 证据；非 VCS 环境不得强行初始化 Git 或伪造 commit。
6. 若本 goal 存在 Loop Blueprint，每个触及 trigger、input、orchestration、worktree、connector read/write boundaries、independent verification、runtime hard stops 或 durable learning 的阶段必须记录 harness evidence。
7. Review gate 通过后默认继续进入下一阶段；不得因为普通阶段边界、checkpoint、rebuild、refresh、reinstall 或可记录风险而中断询问。
8. 未满足当前阶段 Review gate 时，不得进入下一阶段；若下一步修复或诊断清晰且仍在本 goal 范围内，继续修复并重新验证，不要先询问 permission。
9. 只有遇到运行时硬停止才询问用户：本地诊断/修复至少三次或三种方式后仍技术上无法继续、缺少无法本地取得的凭据/文件/事实源、下一步破坏性/不可逆/隐私敏感/外部可见且未预授权、事实源冲突会改变冻结语义、或必需 sub-agent/connector/worktree/verifier 失败且无计划内本地下一步。
10. 任何阶段失败必须记录 root cause、失败命令、文件路径、已知 breakpoint 和下一步修复建议；只有符合上一条硬停止条件时才停下等待用户。
11. 不允许用 silent fallback、兼容假成功、部分成功包装、alternate backend、隐藏错误或 silent degradation 来绕过 gate。
12. 不允许把 legacy / deprecated surface 重新包装成当前产品语义，除非本 goal 明确要求并完成文档更新。
13. 若执行过程中发现 gate、验证规则、回滚路径、阶段边界、Loop Blueprint 或 long-running-goal 策略不够严谨，只暂停 mutation 到足够记录暴露该问题的证据并更新 reusable strategy 或本计划合同；除非触发第 9 条硬停止条件，不要询问 permission；完成相关验证后回到原阶段继续，不得在实现完成后静默放宽验收标准。
14. 若上下文压缩、中断或用户新请求改变了任务方向，必须先按最新请求确认是否仍是同一 goal；若最新请求只是询问同一 goal 的 status、evidence、clarification、progress 或补充上下文，回答或记录后继续；若最新请求明确要求 pause/stop/redirect/change scope，或转为无关 planning、explanation、alignment、skill editing、review-only、git maintenance 或其他独立任务，才暂停旧阶段执行。
15. Close 只能在所有阶段 `Done` 且完成标准全部有代码、测试和文档证据后执行。
16. 只有 `Close housekeeping policy: Enabled` 才允许在 Close 调用 `watcher:housekeeping`；这只授权清理已记录任务根目录内、盘点后确认可丢弃的缓存候选，不授权无条件删除整个目录。`Disabled`、`Not applicable` 或缺少该字段的 legacy goal 均不得执行清理。

## 状态定义

| 状态 | 含义 |
|---|---|
| `Draft` | 设计仍需补充，不能执行实现 |
| `Ready` | 设计与验收指标已明确，可以开始该阶段 |
| `Not Started` | 该阶段尚未开始，且必须等待前置阶段 Done |
| `In Progress` | 当前阶段正在实现或验证 |
| `Blocked` | 当前阶段触发运行时硬停止；未决设计必须在 Ready 前解决，否则保持 Draft |
| `Done` | 阶段 Review gate、量化验收和 checkpoint evidence 均已完成 |
| `Closed` | 仅用于整体计划完成后关闭并从 active TODO/goal 导航移除 |

## 全局验收规则

每个阶段的验收至少包含：

1. 代码证据：列出新增、修改或删除的关键文件。
2. 行为证据：说明 API / UI / migration / runtime 行为是否变化。
3. 测试证据：列出实际执行命令和结果；不能只写“应当通过”。
4. 文档证据：同步更新本文件状态表，并按需更新 active current docs。
5. 回滚证据：说明该阶段如何回滚，migration 阶段必须说明正反向策略。
6. 风险证据：列出仍保留的 legacy compatibility、未解决风险和下一阶段要消除的部分。
7. Harness 证据：若本阶段触及 Loop Blueprint，记录实际 trigger/input 路径、编排或 worktree 隔离证据、connector 读写结果、独立验收结果、YOLO actions 和运行时硬停止结论。

默认验证命令：

```bash
git diff --check -- <changed-paths>
```

按改动类型追加验证：

1. 涉及 Python / backend model / serializer / API / migration：运行相关 test 和 migration check。
2. 涉及前端页面、route、wire shape 或交互：运行 targeted unit / browser / Playwright validation。
3. 涉及 runtime user flow、proxy、container、fixture 或 browser gate：运行对应 runtime diagnostics。
4. 涉及 shell / PowerShell / batch / Python scripts：运行对应语法检查和 dry-run。
5. 涉及 docs-only：至少运行 `git diff --check -- <changed-paths>`，并确认链接与事实源不冲突。

Checkpoint evidence format：

```text placeholder-example
Checkpoint component: <Pending / Done>
Checkpoint type: <git commit / current HEAD / artifact revision / not applicable>
Revision: <commit hash / HEAD hash / artifact path / issue or task revision / n/a>
Changed files: <milestone-scoped paths or none>
Validation recorded: <commands and pass/fail result>
Out-of-scope dirty changes: <none or excluded paths>
```

## 设计原则

1. `<原则 1：领域 ownership 或模块边界。>`
2. `<原则 2：API / UI / runtime 行为边界。>`
3. `<原则 3：compatibility / legacy 处理原则。>`
4. `<原则 4：failure handling 和 fail-fast 规则。>`
5. `<原则 5：测试与验证边界。>`

## 目标结构

### `<Target Area 1>`

1. `<目标态 1。>`
2. `<目标态 2。>`
3. `<必须保留的兼容边界。>`
4. `<必须移除或禁止恢复的旧行为。>`

### `<Target Area 2>`

1. `<目标态 1。>`
2. `<目标态 2。>`
3. `<风险或后续 Future 边界。>`

## 非目标 / Future 边界

本 goal 不处理：

1. `<明确不处理的事项 1。>`
2. `<明确不处理的事项 2。>`
3. `<明确不处理的事项 3。>`

## 阶段计划

本模板默认给出 `M0`、`M1`、`M2` 三个阶段作为示例。创建具体 goal 时，应按实际任务规模增删阶段：

1. 保留 `M0` 作为执行前基线 / contract review / design freeze，除非本项目已有等价阶段。
2. 删除不需要的示例阶段，不要留下空的占位阶段。
3. 新增阶段时按 `M3`、`M4` 继续编号，并复制完整的范围、Review gate、执行证据、推荐验证和 Checkpoint evidence 结构。
4. 每次增删阶段后，同步更新“阶段状态表”和“推荐 Goal Prompt”里的阶段顺序要求。

### M0 - `<阶段名称>`

状态：`Not Started`

范围：

1. `<本阶段要做的事情 1。>`
2. `<本阶段要做的事情 2。>`
3. `<本阶段不做的事情。>`

Review gate：

1. `<必须满足的验收条件 1。>`
2. `<必须满足的验收条件 2。>`
3. `<必须满足的验收条件 3。>`

执行证据：

1. 代码证据：
   - `<完成后填写关键文件和改动。>`
2. 行为证据：
   - `<完成后填写行为变化或无行为变化说明。>`
3. 测试证据：
   - `<完成后填写实际命令和结果。>`
4. 文档证据：
   - `<完成后填写文档同步情况。>`
5. 回滚证据：
   - `<完成后填写回滚方式。>`
6. 剩余风险：
   - `<完成后填写残留风险。>`
7. Harness evidence：
   - `<若本阶段触及 Loop Blueprint，填写触发、输入、编排、隔离、connector、独立验收、YOLO actions 和运行时硬停止证据；否则写 Not applicable。>`

推荐验证：

```bash
git diff --check -- <changed-paths>
<additional-command-if-needed>
```

Checkpoint evidence：

```text
<Fill the Checkpoint evidence format for M0.>
```

### M1 - `<阶段名称>`

状态：`Not Started`

范围：

1. `<本阶段要做的事情 1。>`
2. `<本阶段要做的事情 2。>`
3. `<本阶段不做的事情。>`

Review gate：

1. `<必须满足的验收条件 1。>`
2. `<必须满足的验收条件 2。>`
3. `<必须满足的验收条件 3。>`

执行证据：

1. 代码证据：
   - `<完成后填写关键文件和改动。>`
2. 行为证据：
   - `<完成后填写行为变化或无行为变化说明。>`
3. 测试证据：
   - `<完成后填写实际命令和结果。>`
4. 文档证据：
   - `<完成后填写文档同步情况。>`
5. 回滚证据：
   - `<完成后填写回滚方式。>`
6. 剩余风险：
   - `<完成后填写残留风险。>`
7. Harness evidence：
   - `<若本阶段触及 Loop Blueprint，填写触发、输入、编排、隔离、connector、独立验收、YOLO actions 和运行时硬停止证据；否则写 Not applicable。>`

推荐验证：

```bash
git diff --check -- <changed-paths>
<additional-command-if-needed>
```

Checkpoint evidence：

```text
<Fill the Checkpoint evidence format for M1.>
```

### M2 - `<阶段名称>`

状态：`Not Started`

范围：

1. `<本阶段要做的事情 1。>`
2. `<本阶段要做的事情 2。>`
3. `<本阶段不做的事情。>`

Review gate：

1. `<必须满足的验收条件 1。>`
2. `<必须满足的验收条件 2。>`
3. `<必须满足的验收条件 3。>`

执行证据：

1. 代码证据：
   - `<完成后填写关键文件和改动。>`
2. 行为证据：
   - `<完成后填写行为变化或无行为变化说明。>`
3. 测试证据：
   - `<完成后填写实际命令和结果。>`
4. 文档证据：
   - `<完成后填写文档同步情况。>`
5. 回滚证据：
   - `<完成后填写回滚方式。>`
6. 剩余风险：
   - `<完成后填写残留风险。>`
7. Harness evidence：
   - `<若本阶段触及 Loop Blueprint，填写触发、输入、编排、隔离、connector、独立验收、YOLO actions 和运行时硬停止证据；否则写 Not applicable。>`

推荐验证：

```bash
git diff --check -- <changed-paths>
<additional-command-if-needed>
```

Checkpoint evidence：

```text
<Fill the Checkpoint evidence format for M2.>
```

## 阶段状态表

| 阶段 | 状态 | Review | Checkpoint |
|---|---|---|---|
| M0 `<阶段名称>` | Not Started | Pending | Pending |
| M1 `<阶段名称>` | Not Started | Pending | Pending |
| M2 `<阶段名称>` | Not Started | Pending | Pending |
| Close | Not Started | Pending | Pending |

## Close Gate

所有 M 阶段完成后，先将 Close 行和整体状态设为 `In Progress` 并补齐以下证据；只有本 gate 全部通过后，才将 Close 行设为 `Done / Passed / Done`、整体状态设为 `Closed`。

Close 前必须满足：

1. 所有阶段均为 `Done`。
2. 所有 Review gate 均为 `Passed`。
3. 所有 checkpoint evidence 均已完成并记录。
4. active current docs、validation log、runtime/test checklist 或相关索引已同步。
5. 所有必须执行的测试命令均记录实际结果。
6. `git diff --check -- <changed-paths>` 通过。
7. Markdown 链接检查按需通过。
8. 若存在 Loop Blueprint，所有触及 harness 的阶段都已记录对应证据。
9. 已按显式 task temporary cache / housekeeping policy 处理：无 root 时明确记录“没有创建 task temporary cache roots”；只有 concrete roots 才记录每个 exact root、处置动作和移除 / 保留 / 失败 / residual size；durable evidence 位于缓存根目录之外。
10. 未解决风险已记录，并明确是否进入 Future。
11. close checkpoint evidence 已记录；若项目已有 Git / version-control 工作流且要求 close commit，使用 `<goal_slug> close: <summary>` 或本项目约定格式。

Close 执行证据：

1. 代码证据：
   - `<Close 时填写最终关键文件。>`
2. 行为证据：
   - `<Close 时填写最终行为结论。>`
3. 测试证据：
   - `<Close 时填写最终命令和结果。>`
4. 文档证据：
   - `<Close 时填写文档同步。>`
5. 回滚证据：
   - `<Close 时填写整体回滚策略。>`
6. 剩余风险：
   - `<Close 时填写 Future / residual risk。>`
7. Harness evidence：
   - `<Close 时填写 Loop Blueprint 最终结论；手动 goal 写 Not applicable。>`
8. Temporary cache / housekeeping evidence：
   - Recorded policy：`<Enabled / Disabled / Not applicable>`
   - Exact roots / Roots outcome：`<逐项重复 goal-owned absolute path / None created>`
   - Action：`<Enabled 的 watcher:housekeeping 有界动作 / Disabled 的 preserved or retained 动作 / no-roots disposition>`
   - Removed size：`<concrete roots 时填写，例如 0 B>`
   - Preserved size：`<concrete roots 时填写，例如 0 B>`
   - Failed size：`<concrete roots 时填写，例如 0 B>`
   - Residual size：`<concrete roots 时填写，例如 0 B>`

Checkpoint evidence：

```text
<Fill the Checkpoint evidence format for Close.>
```

## 当前风险

1. `<执行前已知风险 1。>`
2. `<执行前已知风险 2。>`
3. `<执行前已知风险 3。>`

## 推荐 Goal Prompt

```text
请按照 <goal-dir>/<goal_slug>_long_running_goal_plan.md 执行 <Goal Name>。

执行要求：
1. 若无有效 Planning preflight marker，先应用 components/planning-preflight.md；已有 Done 或 explicit-skip marker 时不要重复 grill。
2. 执行前确认 Pre-Approval / YOLO 边界和显式 task temporary cache / housekeeping policy 已冻结；Loop-shaped goal 还要确认 harness 字段已冻结。
3. 按阶段顺序执行；每阶段开始标 In Progress，完成前记录代码、行为、测试、文档、回滚、风险和 harness evidence。
4. Review gate 通过后默认继续；计划内非破坏性本地动作按 YOLO 边界执行。
5. 每阶段完成前应用 components/checkpoint.md，按 Checkpoint evidence format 记录 revision 证据；不默认 empty commit，非 VCS 不强行初始化 Git。
6. 失败时在本 goal 范围内诊断修复；只有运行时硬停止才停下并报告 root cause、失败命令、文件路径、breakpoint 和下一步。
7. 不允许用 fallback、兼容假成功、alternate backend、部分成功包装、隐藏错误或 silent degradation 绕过 gate。
8. Close 前运行并记录 git diff --check -- <changed-paths> 以及本 goal 指定验证命令。
9. Close 时严格按记录的 housekeeping policy 行事；只有 Enabled 才调用 watcher:housekeeping 做有界清理，不重新解析临时根目录，也不无条件删除整个目录。watcher 不可用时保持 Close/overall In Progress（满足 hard stop 时才 Blocked），不得使用递归删除 fallback；只有用户显式演化 preflight policy 后才能改为 Disabled。
```

## 相关文档

1. `<相关 current doc 1>`
2. `<相关 current doc 2>`
3. `<相关 architecture / API / validation / runbook doc>`
