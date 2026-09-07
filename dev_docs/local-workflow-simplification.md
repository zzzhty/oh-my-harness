# 本地提示词与 Workflow 简化

基线：`5e1c420`。范围：本地 Watcher、Workflow、Codex support note；Matt Pocock 仅见 [独立建议](mattpocock-skills-improvement-proposals.md)，整个上游插件保持不变。

## 有意调整的合同

- 预检验证决策是否完备，允许复用已有决策；普通 goal 与 sequence 接受同一 completed / explicit-skip 合同。sequence 仍逐项核对 marker、status、source，Draft 子目标必须有完整冻结边界才能参与自动串行交接。
- 时间估算改为可选上下文，不决定 Ready；删除仅服务固定日期、模式、sentinel、两条 driver、HTML 包裹识别的时间检查器及格式矩阵。通用占位符、状态、权限、Close、checkpoint、跨平台缓存边界检查继续保留。
- housekeeping 默认 Disabled；只有 Enabled 要求明确授权。既有 Enabled 不被默认覆盖。清理前仍核对归属、可丢弃性与保留范围。Git 工作树读取失败直接终止，已识别的非 Git 缓存可以直接盘点。
- goal 演化先处理当前任务合同；修改共享 skill/template 必须在源码授权范围内。已授权且仍满足合同的敏感或外部动作不重复询问。
- SOP 保留八个核心章节、每步 action/output；步骤特有的失败处理和完成标准按需增加。共享停止规则、验证与权限必须明确，Ready 检查不授予行动权限。
- scope 入口和 milestone adapter 共用 necessity gate；六份编排分支参考合并为一张任务表。保留只读禁止写入、互斥写范围、父代理负责共享文件与集成、失败披露要求。
- Watcher proposal 强制提供非空的精确日志 identity，复用同一证据窗口；生成 worksheet 与验证分开，完整候选写入独立路径后才能验证。只读压缩分析不需要创建备份，实际修改前仍要可恢复。

## 标识与所有权

被合并的六个 orchestration reference 是仓库内部、非持久化的实现路径；消费者仅有 skill 入口与 ownership 测试，已原子替换为 `task-patterns.md`，不保留别名。35 个 callable skill 名称、invocation 元数据、日志/提案 schema 和上游 lock 不变。

预检 marker/status/source 字段及序列注册表不改名；放宽来源时同时加强三字段一致性检查。已有完整格式 goal/SOP 继续接受。时间说明退出 Ready gate 是本轮明确的合同简化，不是隐藏重设已有测试。

## 验证依据

- 行为 oracle：审计可带未修复发现完成；验证针对真实候选；已授权工作不重复询问；完整决策不强制访谈；简单流程无需重复填表；只读、删除、隐私和必需验证边界继续有效。
- 回归用例覆盖 exact identity 与时间窗口、缺失/空 identity、源和 snapshot 不变、缺失/无效/有效候选、非 Git 只读盘点、Git 失败直报、预检来源与 register 漂移、串行/Blocked/Closed 状态、Enabled 未授权删除、紧凑 SOP 权限/输出/停止规则。
- 独立语义与风险复审发现并修复：压缩 core rule 残留备份要求、空 identity 混入全部证据、模板状态记录措辞歧义、Git 失败被误当非 Git。模板重复总体状态和 M0 标题也已修复。
- 删除固定 prompt 形状、引用数和时估格式的断言；保留行为与权限反例，不以减少测试数量为目标。
- 本轮是源码、结构和行为检查，没有模型 A/B 回放；不声称已量测模型速度或准确率提升。上述优化验证阶段未包含发布与受管安装更新。

## 本轮验证结果

本机 Root 251 项、Watcher 86 项、Workflow 83 项测试均通过，其中 9 项按环境跳过。相关技能 frontmatter、修改后的 Python 编译、Markdown 链接、插件 manifest、分发身份及 diff hygiene 检查通过。新增 promotion-revalidation 场景另由 sequence 8 项测试复验通过。

Root 的 live projection 测试按 Git 索引枚举文件；首次在未暂存删除的状态下读取了旧六个路径并失败。验证时仅临时暂存该组 reference 迁移，完整 Root 测试通过后恢复原未暂存索引，未改测试合同或提交代码。

完成源码和 owning tests 后，分发身份生成脚本运行一次；Watcher 和 Workflow 身份更新，Matt Pocock 源码与身份不变。受影响指令 Markdown 从 146211 降至 108522 UTF-8 字节（约 25.8%），此为文本体积，不是模型 token 或性能测量。

优化验证阶段在本地 `codex/simplify-local-skill-workflows` 完成，本节记录提交前的验证结果；后续发布与安装状态以 Git 远端和 `omh status` 为准。
