# SOP: <SOP Name>

状态：`Draft`

## 摘要

SOP 名称：`<SOP Name>`

SOP 路径：`<sop-path>`

Owner：`<owner / team / agent>`

适用场景：

1. `<什么时候使用本 SOP。>`
2. `<本 SOP 要稳定复用的流程。>`

不适用场景：

1. `<明确不适用场景。>`
2. `<需要改用 long-running-goal / report / automation 的场景。>`

## 触发条件

1. `<用户请求中的触发语义。>`
2. `<定期 / 手动 / 事件触发条件。>`

## 前置条件

1. `<需要存在的文件、目录、环境变量或权限。>`
2. `<需要先读取的事实源。>`
3. `<不能缺失的输入。>`

## 工作目录

```text
<working-directory>
```

## 输入

| 输入 | 必需 | 来源 | 校验方式 |
|---|---:|---|---|
| `<input>` | 是/否 | `<user / file / command>` | `<validation>` |

## Execution Harness

简单手动 SOP 可在不适用字段写 `Not applicable: <原因>`。Agent-executed 或 automated SOP 必须明确以下执行约束，不能只依赖执行模型自行判断。

执行模式：`<manual / agent-executed / automated / report-only / validation>`

Prompt / strategy inputs：

```text
<本 SOP 依赖的 prompt、rubric、agent instruction、reviewer instruction 或 strategy；若无则写 Not applicable: no prompt or strategy input.>
```

Orchestration：

```text
<是否使用 subagent；每个 subagent 的单任务边界；父 agent 保留的最终判断；若无则写 Not applicable。>
```

Isolation：

```text
<使用当前 checkout、只读模式、独立 worktree、串行锁定文件、禁止并行写等隔离策略。>
```

Connector permissions：

```text
<允许读取或写入的外部系统、API、ticket、PR、CI、通知渠道；哪些写入必须人工批准。>
```

Independent verification：

```text
<由脚本、测试、reviewer、subagent 或人工检查 producer 输出；若不需要独立验证，写 Not applicable 并说明原因。>
```

Human escalation：

```text
<缺少输入、权限不足、验证失败、破坏性动作、隐私风险、外部写入、连续失败或事实源冲突时如何停下并报告。>
```

Durable writeback：

```text
<结果写回 report、SOP、skill、runbook、TODO、automation memory、validation log 或不写回的规则。>
```

## 允许动作

1. `<允许读取哪些文件。>`
2. `<允许运行哪些命令。>`
3. `<允许修改哪些文件或状态。>`

## 禁止动作

1. `<禁止发送外部消息、删除、发布、重置、迁移等。>`
2. `<没有明确授权时禁止的动作。>`

## 标准步骤

### Step 1 - `<步骤名称>`

目的：`<目的>`

操作：

```bash
<command-or-action>
```

预期输出：

```text
<expected-output>
```

失败处理：

```text
<stop / retry once / collect diagnostics / escalate>
```

完成条件：

```text
<可观察、可检查的步骤完成条件。>
```

### Step 2 - `<步骤名称>`

目的：`<目的>`

操作：

```bash
<command-or-action>
```

预期输出：

```text
<expected-output>
```

失败处理：

```text
<stop / retry once / collect diagnostics / escalate>
```

完成条件：

```text
<可观察、可检查的步骤完成条件。>
```

## 验证标准

1. `<必须通过的命令或检查。>`
2. `<必须存在的报告、diff、截图或 artifact。>`
3. `<必须同步的文档或状态。>`

## 输出合同

执行完成后必须报告：

1. `<完成了什么。>`
2. `<实际读取或修改的路径。>`
3. `<实际运行的命令和结果。>`
4. `<生成的报告或 artifact 路径。>`
5. `<未解决风险或下一步。>`

## 停止条件

必须停止并报告 blocker 的情况：

1. `<缺少必要输入。>`
2. `<验证失败。>`
3. `<权限或工具不可用。>`
4. `<请求超出允许动作。>`
5. `<事实源与 SOP 假设冲突。>`

## 更新规则

修改本 SOP 时必须：

1. 保留当前已验证命令，除非有新证据替代。
2. 记录为什么流程变化。
3. 同步相关 README、runbook、automation memory 或 skill 文档。
4. 修改 prompt、rubric、agent strategy、connector permissions、automation trigger 或 independent verification rules 前，必须先有 evidence-backed review；未稳定时使用 `prompt-strategy-loop`。
5. 同步更新 Execution Harness、允许动作、禁止动作、验证标准和停止条件中受影响的部分。
6. 重新运行 SOP ready/link 检查。

## 复用 Prompt

```text
Use $sop to execute <SOP Name> at <sop-path>. Follow the SOP exactly, honor the Execution Harness, stop on failed required validation or stop conditions, do not perform forbidden actions, and report commands, outputs, changed paths, generated artifacts, validation evidence, and unresolved blockers.
```
