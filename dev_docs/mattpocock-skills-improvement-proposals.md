# Matt Pocock skills 改进建议

状态：仅建议，未修订上游镜像。审查日期：2026-09-07。

审查基线：oh-my-harness `5e1c420`；上游 `v1.2.3`（`6acc160e4e0cd062dbbbd7a1b26ae92855edf07e`）。

本文件记录用户要求保留、但不在本轮实施的改进。`plugins/mattpocock-skills/skills/` 仍按其 scoped AGENTS.md 原样维护；不添加本地覆盖层、不重写 lock、不删减导入技能。建议通过上游修订处理；改变镜像维护方式需要单独决定。

## 优先修复的流程问题

| 问题与源码 | 建议 | 验收场景 |
| --- | --- | --- |
| [implement](../plugins/mattpocock-skills/skills/implement/SKILL.md) 先 review 后 commit；[code-review](../plugins/mattpocock-skills/skills/code-review/SKILL.md) 只比较 `base...HEAD`，遗漏未提交实现。 | 区分提交范围、暂存区、工作区，并由调用方指定审查对象。 | 新分支只有未提交修改时仍审查这些修改；旧提交与新修改混合时均不遗漏。 |
| [resolving-merge-conflicts](../plugins/mattpocock-skills/skills/resolving-merge-conflicts/SKILL.md) 要求 Always resolve、Stage everything。 | 只暂存本次解决的文件；缺少产品决策时保存冲突现场并报告。既不擅自 abort，也不强行选择无依据的行为。 | 有无关 staged/unstaged 文件时不带入合并提交；无法确定双方意图时停止依赖工作。 |
| [wizard 模板](../plugins/mattpocock-skills/skills/wizard/template.sh) 将 secret/variable 写入失败转成 SKIPPED，随后返回 0 并显示 Setup complete。 | 必需步骤失败保留具体诊断，输出 incomplete 并返回非零；可选步骤的缺失单独披露。 | gh 不可用、未登录、写入失败分别有准确结果；成功路径仍隐藏 secret 输入。 |
| [TDD](../plugins/mattpocock-skills/skills/tdd/SKILL.md) 禁止内部测试，[DEEPENING](../plugins/mattpocock-skills/skills/codebase-design/DEEPENING.md) 却允许 internal seams，并要求直接删除旧浅层测试。 | 按独立行为价值选择测试边界；只有实际覆盖被替代的旧测试才删除。 | 高层集成测试新增后，独立的隐私、schema、错误处理覆盖仍保留。 |

## 简化建议

1. **沿用已确认决策。** TDD 只对未确定的测试边界提问；[to-spec](../plugins/mattpocock-skills/skills/to-spec/SKILL.md) 综合已有讨论时不再开启无必要访谈。[grilling](../plugins/mattpocock-skills/skills/grilling/SKILL.md) 保留深度盘问用途，以关键决策已明确为结束条件。
2. **允许暂定假设，验证最终结论。** [diagnosing-bugs](../plugins/mattpocock-skills/skills/diagnosing-bugs/SKILL.md) 可先用代码、配置和日志形成可证伪假设，再选择复现方式；最小化和 3–5 假设不是每次故障的必经门槛。生产或低频问题无法即时复现时，不应禁止有边界的调查。
3. **按规模使用并行与产物。** code-review 保留 Standards/Spec 两个视角，允许合并重复发现并按影响排序；是否使用两个代理、全量测试、HTML 报告或多份设计由任务需要决定。[improve-codebase-architecture](../plugins/mattpocock-skills/skills/improve-codebase-architecture/SKILL.md) 的完整报告可以作为用户选择的模式。
4. **用持久知识需求决定访谈模式。** [ask-matt](../plugins/mattpocock-skills/skills/ask-matt/SKILL.md) 不应因存在 cwd 就认定文档模式总是更好；grill-me/grill-with-docs 已是很薄的入口，可共用普通/记录决策模式，保留 domain-modeling 的独立职责。
5. **按真实会话边界交接。** ask-matt 假设 prototype 必在独立目录，实际 [prototype](../plugins/mattpocock-skills/skills/prototype/SKILL.md) 要求靠近目标模块；仅在真实跨目录、会话、人员或隔离边界时 handoff。固定上下文窗口阈值不应代替当前模型和 harness 的实际状态。
6. **缺失配置不扩大只读审查。** code-review 缺少 issue-tracker.md 时，可先使用已提供的 PR/任务说明和现有仓库事实；配置 tracker、创建文档或标签属于单独有授权的 setup，不是只读 review 的隐含步骤。

## 验证边界

以上基于全部 25 个技能正文、22 份 Markdown 引用、2 个 shell 模板和元数据的源码审查。wizard 的未完成却成功退出路径通过无文件写入、无外部请求的内存 stub 复现。没有执行模型 A/B 回放，不能据此声称模型速度或准确率已有提升。

上游候选应与此基线比较：已授权工作不重复询问、只读不写、缺失必需配置不虚报成功、用户工作不被纳入无关提交、真实回归覆盖不丢失。保留必要的隐私、破坏性操作、外部写入和源镜像边界。
