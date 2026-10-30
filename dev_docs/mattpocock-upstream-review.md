# Matt Pocock 上游审查记录

> Entries dated before the repository rebuild are historical design and validation
> records: their local commits, PR numbers, installed-state observations and CI
> results refer to the private pre-rebuild archive, not the current installation.
> The 2026-10-29 entry below is a current repository review. Upstream release pins
> and attribution remain applicable.

更新步骤由[插件 README](../plugins/mattpocock-skills/README.md#upstream-updates)维护。本文件记录已检查的上游范围、选择结果和待处理项；“已审查”不表示整版已合入。

最后完整审查的上游版本：`v1.3.2`，提交 `d1478fcb140db0b93c0c8df17bcfd311844749d0`。完整分类只推进审查覆盖；不表示全部采纳。

## 2026-09-08：初始化本地选编基线

- 上游范围：原始引入版本 `v1.2.3` 的完整技能集合；本次没有检查更新的上游发布。
- 本地起点：`8a252783d9c4bddbd7569daf151e7fb150aa7cd1`；选编改动位于 `codex/curate-mattpocock-skills`，尚未提交。
- 选择结果：20 项保留并按需要适配，5 项退出分发；具体名单、行为修订及验证见[实施记录](mattpocock-skills-improvement-proposals.md#8-实施与验收记录2026-09-08)。原始上游来源与许可继续保留。
- 暂缓采纳：无。五项退出技能属于明确跳过，不作为待合入队列。

后续每轮记录实际比较的起止提交、受影响路径、采纳/适配/跳过/暂缓及理由、实际应用和验证结果。暂缓、已选中但待应用、验证未通过的条目都保留原始提交和路径，直至有明确处理结果。

## 2026-10-05：选择性采纳 v1.3.1

- 上游范围：`6acc160e4e0cd062dbbbd7a1b26ae92855edf07e` → `24fe0ef7737efae15c87225755e9f6f5965e4888`；81 个提交、114 个净变更路径已完整分类。
- 本地起点：`2ae341e8c6b1bd1f53b324fd539e27cba5b1b92c`（远端 main）。
- 最终决定：adopt 4、adapt 15、skip 89、defer 6，详见[逐路径记录、迁移范围及验收](mattpocock-v1.3.1-review.md)。
- 实际选择：harness-aware 共享方法加载、domain-modeling 触发及 existing-owner 兼容、新增轻量 `pr`；用户明确批准退休 `resolving-merge-conflicts`，覆盖初审保留建议。Matt catalog 仍为 19。
- 保留原始 v1.2.3 派生归因；新增 pr 单独记录 Matt / HumanLayer 来源和 MIT 通知。现有用户术语文件、历史记录、全工作树审阅及授权边界保持。
- 源修改已在本地应用；独立静态语义/风险审查、受影响 catalog/projection 与插件测试、三包校验、现有分发身份检查通过。完整 root suite 剩 1 个在未修改基线同样复现的 zsh 空 PATH 环境失败，不能称全绿；详细命令、计数及限制见本轮记录。
- 未解决：独立 `retro` 与 `implement-spec` 的 6 个原始路径继续 defer；完整 root 检查的宿主环境限制仍待复验或单独解决。不以审阅基线推进冒充采纳或验证完成。

## 2026-10-05 补充：按用户选择加入显式 retro

- 起点为 PR #23 的 `6fd0430819f5b6817b10b56a6521ecd1c17cd3f2`。用户明确选择后，将同一 v1.3.1 的三个 retro 路径从 defer 改为 adapt；上方初次检查点保留作历史证据。
- 当前 114 条分类为 adopt 4、adapt 18、skip 89、defer 3；当前 Matt catalog 为 20。仅 implement-spec 的三个路径继续 defer。
- retro 是授权会话证据上的可选提案/no-change 入口，与 Watcher skill-maintainer 职责不同；不搜索私有会话/cache，不自动改 source/hooks/CI/权限，不发布、不创建后台任务，不增加原交付门禁。来源、静态反例和补充验收见[详细记录](mattpocock-v1.3.1-review.md#2026-10-05-补充显式会话复盘-retro)。
- 补充已通过独立静态语义/权限审查、全部 owning checks 及生成身份检查；root 353 tests 中剩 1 个既有 zsh 空 PATH 宿主失败（345 passed、7 skipped）。精确补充 head 的远端 CI 以 PR #23 Evidence 为准；未执行用户安装、合并或部署。

## 2026-10-29：选择性采纳正式 v1.3.2

- 正式发布触发，范围 `24fe0ef7737efae15c87225755e9f6f5965e4888` → `d1478fcb140db0b93c0c8df17bcfd311844749d0`；51 个提交、72 个净路径完整分类。没有检查或合入 release 后的 main 变化。
- 本地起点：`b0ea6081585558e3a31fcdc267175fbd3e5d22c9`，独立分支 `codex/mattpocock-v1.3.2-review`。
- adopt 2、adapt 9、skip 60、defer 1；[逐路径决定、实际落点与验证](mattpocock-v1.3.2-review.md)。fresh-context 意图在现有全局 delegation owner 中适配一次，不复制到多个技能或强制增加子代理。
- 保留 20 个 Matt 技能、原始 v1.2.3 归因和现有调用/授权边界。所选改动只应用于本地源分支，未推送、发布、安装或更改已有 release。
- v1.3.1 的 implement-spec 三个原始暂缓路径继续保留，本次新增改动也暂缓。完整审查覆盖不等于整版同步；未完成的验证见本轮详细记录。
