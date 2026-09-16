# 穷鬼模式自适应升降级方案（草案 v2）

状态：已由 [v3.1 实施基线](POOR_MODE_ADAPTIVE_V3.md) 取代，仅保留作首轮方案与复审轨迹，不再作为实施规格。

## 一、首轮复审 4 个 P1 的核实结果

| P1 | 核实 | 证据 |
| --- | --- | --- |
| VS Code Leader 没有直做工具 | 成立 | [leader.agent.md](../src/agents/leader.agent.md) frontmatter `tools: ['vscode/askQuestions', 'vscode/memory', 'agent', 'read', 'search', 'web']`，正文明确"你没有编辑、终端……工具"；[validate.py:19](../scripts/validate.py) `LEADER_TOOLS` 与 [test_repository.py](../tests/test_repository.py)（精确工具串断言 + `execute`/`edit` 禁用清单）双重锁死 |
| Codex 推理档位仍被默认值钉死 | 成立 | [codex/config.toml:4](../codex/config.toml) `default_subagent_reasoning_effort = "high"`；官方优先级：agent 文件 > 显式调用参数 > `[agents]` 默认 > 父 Agent，**仅当文件同时省略 model 与 effort 才继承父级两者**——只删 model 默认会让 fallback 继承主模型但强制 high |
| adaptive ask 会绕过全局风险判定 | 成立 | [guard.py:106-115](../zcode/plugins/leader-worker/hooks/guard.py) 边界分支先 return，全局 Git 写入/删除/依赖判定在 117-131 行之后；原位改 ask 会让 Git 写操作降为 ask |
| 旧 Codex 默认值不能无条件受管删除 | 成立 | [install_codex.py](../scripts/install_codex.py) `merge_config` 只有"补缺键 + 拒绝冲突值"两条路径（15-20、129 行），无删除路径、无单键所有权记录，无法区分旧安装器写入与用户自配 |

对首轮总结措辞的订正：首轮说"Codex 侧扫描全部属实"过强，应表述为**修正因果解释、智能维度表述与 fallback 实现细节后，核心 Codex 事实均经源码确认**。且"只剩路线选择一种智能维度"不成立——现有设计还有验证深度升级（[tester.agent.md:23](../src/agents/tester.agent.md)：从最便宜检查起步、必要时才升级到模块/全量验证）和按角色推理档位分级（Codex `medium`/`high`）。本方案新增的是**跨执行平面**的升降级：Leader 直做（降级）与主模型接手 Worker 包（升级）。

## 二、总体结构：strict 不动，adaptive 独立可选

撤回首轮"ZCode 是唯一结构行为变更"的说法。三个平台的结构变更深度不同，全部为**显式可选**，默认安装与现状完全一致：

| 平台 | 机制 A（直做）结构 | 机制 B（回退）结构 |
| --- | --- | --- |
| VS Code | 独立 Adaptive Leader 变体（常设 `edit`+`execute` 工具授权，**最宽**），安装器按模式二选一，默认 strict | 已具备（Worker 清单禁钉模型，不指定即继承 Leader 模型） |
| Codex | 无结构杠杆，协议授权（如实声明） | 继承链结构可用：fallback 变体省略 model+effort 双键 + 移除两个 `[agents]` 默认 |
| ZCode | guard 双模式：adaptive 下编辑/命令降为逐次 `ask`（用户逐笔批准） | 未证实：先探针，通过前共享协议维持"停止并上报" |

不扩大默认 Leader 的工具集——strict 变体一个字符不动，adaptive 以独立文件存在，避免把最宽的授权变成默认面。

## 三、机制 A：自适应直做

**全部条件同时满足才允许直做，任一不满足即照旧派发：**

1. 精确位置已知，不需要任何调查或发现；
2. 单一、局部、可逆的修改，或**单条窄命令**（定义见下）；
3. 不涉及删除、依赖/锁文件、配置、密钥、迁移、持久数据、外部服务、部署、权限变更；
4. 不改变公共契约（不触发 `PUBLIC_TYPESCRIPT_API` / `BEHAVIOR_BOUNDARY`）；
5. 至多一步窄验证；
6. 每次直做单行声明 `DIRECT: <依据>`，计入成本证据。

**窄命令的硬边界**（替代首轮"良性命令"的主观表述）：单条简单命令，无 shell 复合（`&&`、`;`、`|`、重定向）；禁止网络、依赖安装、环境/配置变更、Git 写入、持久数据、外部服务、长驻进程；允许的写入仅限工作区内正常缓存与构建产物。高风险类目（第 3 条所列）即使满足其余条件也永不直做，保留原有确认门。

范围限定：机制 A 只覆盖编辑与窄命令；Leader 既有窄验证读规则不变；`mcp__*` 不在覆盖范围。平台可用性：VS Code 仅 `--leader adaptive` 安装；Codex 协议授权（记录为提示词行为，不称结构证明）；ZCode 仅 adaptive 模式且逐次 ask。

## 四、机制 B：模型失败回退

**触发**：确定性的模型/推理档位拒绝；或确认旧调用已终止后，一次瞬时重试耗尽。**执行**：每包至多一次、调用前披露；保持原角色、沙箱与 `GOAL`/`BOUNDARIES`/`DONE`，由主模型执行的 **fallback Worker 变体**接手包，不是 Leader 收回工具；`FAIL`/`BLOCKED`/`NEEDS_LEADER`/质量不足永不触发；单列记录 `fallback`，不计入低价模型成绩；用户禁止回退或限制花费时以其为准；不发现第三方模型。

**各端实现：**

- **VS Code**：现状已具备（`validate.py` "must not fix its own model" 强制 Worker 清单无模型），仅补协议措辞。
- **Codex**：新增四个 `leader_*_fallback.toml`，**同时省略 `model` 与 `model_reasoning_effort`**（官方规则：仅双省略才继承父级两者），`sandbox_mode` 显式保留角色原值（省略会继承父线程沙箱，可能比 Analyzer/Reviewer 的 read-only 更宽）；`config.toml` **同时移除** `default_subagent_model` 与 `default_subagent_reasoning_effort`（二者分别占据优先级第 3 层，任一残留都会截断父级继承；基础 Agent 各自显式双键，不受移除影响）。
- **ZCode**：**先探针后声明**。共享发布协议在 0.8.0 继续写"ZCode 停止并报配置问题"；用一次性探针（一次性工作区 + 实验性插件副本 + 一个不钉 `model`/`thoughtLevel` 的 agent）验证 ZCode 对缺省字段的继承行为，实验变体不进入正式安装路径。探针通过后才在后续版本（0.9.0）发布四个 fallback 变体并更新共享契约；不通过则维持现状并如实记录。

## 五、平台结构实现细节

### VS Code：独立 Adaptive Leader

- 新增 `src/agents/leader-adaptive.agent.md`：`name: Leader` 与 strict 相同（同时刻只装一个，互斥由安装器保证），frontmatter tools = strict 六项 + `edit` + `execute`；正文在 strict 全部条款上增加机制 A 条件块与 `DIRECT:` 声明要求。
- [install.py](../scripts/install.py) 增加 `--leader strict|adaptive`（默认 strict），控制 rename 映射 `leader.agent.md` / `leader-adaptive.agent.md` → 安装名 `leader.agent.md`；dry-run 显示所选变体。strict 变体文件零改动。
- `validate.py`：`LEADER_TOOLS` 之外新增 `LEADER_ADAPTIVE_TOOLS` 校验第二变体；`tests/test_repository.py` 为两变体分别断言工具串（strict 的禁用清单仅作用于 strict 文件）。

### Codex：安装器迁移矩阵

新键集只含 `enabled` 与 `max_concurrent_threads_per_session`。对目标项目已有配置的处理：

| 既有状态 | 默认（无旗标） | `--migrate-adaptive-config` |
| --- | --- | --- |
| 无两个旧默认键 | 正常安装新键集 | 同左 |
| 两键存在且**精确等于**旧受管值 | **停止并提示**：说明需人工确认或加旗标迁移 | 备份后仅删除这两行精确旧值，继续安装 |
| 键存在但为其他值（用户自配） | 停止并指出冲突键与值，不触碰 | 同样停止（只迁移精确旧值，不覆盖用户值） |

安装器不记录单键所有权，因此一律不猜来源；删除动作只认"键+值完全匹配旧受管值"。

### ZCode：guard 重排与模式解析

**判定顺序（重排后，两模式共用）：**

1. 全局硬拒绝：Git 写操作 deny；危险删除 deny（复合命令删除、通配/特殊字符目标、不可解析命令）；
2. Leader 边界：strict → 编辑/命令/mcp 一律 deny（保持现状，不被后续 ask 类弱化）；adaptive → mcp 仍 deny，编辑/命令落入第 4 步；
3. 全局确认类：独立安全删除 ask；依赖/迁移/部署 ask；
4. adaptive 剩余普通编辑/命令 → ask（逐笔批准）。

要点：strict 的 deny 先于一切 ask 类（独立安全删除命令在 strict 下仍是边界 deny，不降为删除 ask）；adaptive 下 Git 写子命令恒 deny、依赖安装类命令恒得到专项确认 ask、独立安全删除得到删除确认 ask，都先于通用 adaptive ask。已知局限（已实证）：全局判定基于展平输入的文本匹配，编辑内容中恰好出现与 Git 写子命令相同的相邻词序列时会误中规则——本方案 v2 撰写时，设计文档正文引用的命令示例即触发过一次该拦截；两模式下均如此，属既有模式匹配局限，测试中固化为已知行为，修复（收窄匹配到命令字段）列为后续独立工作项。

**模式解析（fail-closed）：**仅解析完整管理块内**唯一**一行 `leader-worker-mode: strict|adaptive`（严格正则，允许尾随空白）；缺失、重复、拼错、出现在管理块外 → 一律按 strict。

**目录解析：**优先会话传入的项目根变量；否则从当前目录**遍历到文件系统根**逐级找最近的含管理块的 `AGENTS.md`（替换现有仅向上三层的 `parents[:3]`），避免深层工作目录漏判。

**重装保留模式：**[install_zcode.py](../scripts/install_zcode.py) 合并管理块前先读出旧块中的模式行；新增 `--mode strict|adaptive`，默认"保留检测到的模式，否则 strict"，把模式行写入新管理块。

### Codex fallback 一致性防线

八个 agent 形成两套近似指令，防漂移：`validate.py` 对每对 base/fallback 做规范化比较——剔除 `model`、`model_reasoning_effort` 两行并替换 `name`/`description` 后，其余内容必须逐行一致；任一侧安全条款改动未同步另一侧即失败。

## 六、验收矩阵

**ZCode guard 决策矩阵**（测试固化为用例）：

| 操作类别 | strict（边界激活） | adaptive | 边界未激活 |
| --- | --- | --- | --- |
| Git 写操作 | deny | deny | deny |
| 危险删除 | deny | deny | deny |
| 独立安全删除 | deny（边界） | ask（删除确认） | ask |
| 依赖/迁移/部署 | deny（边界） | ask（专项确认） | ask |
| 普通编辑 | deny | ask（adaptive） | 放行 |
| 普通命令 | deny | ask（adaptive） | 放行 |
| `mcp__*` | deny | deny | 放行 |

**Codex 安装器迁移矩阵**：见第五节表，四行状态 × 两旗标行为全部测试固化。

**回退继承 Smoke 矩阵**（Codex）：基础 Agent 调用 → 子线程报 `gpt-5.6-luna` + 角色档位；fallback 调用 → 子线程报**父线程模型与父线程档位**（双键省略 + 双默认移除后才成立）；同时验证 fallback Analyzer 仍被 read-only 沙箱拒绝写入。

**直做条件清单**：第三节六条 all-or-none 清单作为 Smoke 判据；任一条不满足的用例必须仍走 Worker。

## 七、变更清单

**共享：** [src/protocols/poor-mode.md](../src/protocols/poor-mode.md)（机制 A 条件块；失败路由：VS Code/Codex 回退条款，**ZCode 维持"停止并上报"**）→ `sync_poor_mode.py --write` 同步三个 Leader；[docs/POOR_MODE.md](POOR_MODE.md)、`docs/ARCHITECTURE.md`、`docs/NATIVE_LIMITATIONS.md`、两份 README、`CONTRIBUTING.md`、`CHANGELOG.md`；版本四处一致升 0.8.0。

**VS Code：** `src/agents/leader-adaptive.agent.md`（新增）；`src/agents/leader.agent.md` 仅同步内嵌块；`src/skills/leader-orchestration/SKILL.md`、`src/skills/cost-control/SKILL.md`；`scripts/install.py`（`--leader` 旗标）；`validate.py`（双工具集校验）；`tests/test_repository.py`（双变体断言）。

**Codex：** `codex/agents/leader_*_fallback.toml` ×4（双键省略、沙箱保留）；`codex/config.toml`（移除两个默认键）；`scripts/install_codex.py`（新键集 + `--migrate-adaptive-config`）；`codex/AGENTS.md` 与 `codex/skills/leader-worker-mode/SKILL.md` 措辞；`docs/CODEX.md`（8 个 agent、迁移矩阵、Smoke 步骤）；`validate.py`（config 键反转 + fallback 一致性比较）；测试同步。

**ZCode：** `zcode/plugins/leader-worker/hooks/guard.py`（判定重排 + 模式解析 fail-closed + 全根遍历）；`zcode/AGENTS.md`（模式标记行 + 边界节双模式描述 + 直做条款；回退条款维持现状）；`zcode/plugins/leader-worker/skills/leader-worker-mode/SKILL.md`；`scripts/install_zcode.py`（`--mode` 与模式保留）；`docs/ZCODE.md`；`zcode/marketplace.json`、`plugin.json`；**0.8.0 不含 fallback agent 文件**。

## 八、分阶段落地与 Smoke

每阶段以上一阶段通过为门，不带病推进。

- **Phase 0（源码，无运行时声明）**：全部文本 + 结构文件 + 校验器 + 测试 + 版本；`validate.py`、`sync_poor_mode.py`、全量测试通过；strict 安装路径产物与 0.7.0 逐字节等价（除版本号与变更日志）。
- **Phase 1（VS Code）**：先 strict 回归（既有 Smoke 全绿，Leader 仍无 edit/execute）；再 `--leader adaptive` 安装 + 新会话：小改直做并声明 `DIRECT:`、零 Worker 调用；中等任务仍完整委派；回退 Smoke 不变。
- **Phase 2（Codex 一次性项目）**：`docs/CODEX.md` 既有 8 步回归；直做用例（记录为提示词行为）；把某基础 Agent 的 `model` 改为无效值制造确定性拒绝 → 披露后调 fallback，子线程报**父模型与父档位**；安装器迁移矩阵四状态实测；fallback Analyzer 沙箱拒绝实测。
- **Phase 3a（ZCode 探针，不产生发布物）**：一次性工作区 + 实验插件副本 + 一个不钉 `model`/`thoughtLevel` 的 agent，观察是否继承主模型与档位；结论无论真假都记录，不修改 0.8.0 共享协议。
- **Phase 3b（ZCode 提升，独立版本 0.9.0，仅探针通过）**：发布四个 fallback 变体、更新共享契约与 `docs/ZCODE.md`；同时做 strict 回归 + `--mode adaptive` 切换 + guard 决策矩阵全组合实测（含模式行缺失/重复/拼错的 fail-closed 用例）。

Codex `SubagentStart` 状态关联（结构化区分主线程以约束机制 A）仍列为后续可选探索，本方案不依赖。

## 九、度量与基准规则

沿用首轮：成本证据报告包数、`DIRECT` 次数、`fallback` 次数、重试/返工次数四类一等事件，未知留空；使用直做或回退的运行在[全栈基准](../benchmarks/poor-mode-fullstack/README.md)单列，不混入低价模型主榜；回退运行不能证明低成本模型能力；静态校验通过不得写成节省百分比。

## 十、已锁定的取舍

| 决策 | 选择 | 理由 |
| --- | --- | --- |
| VS Code 直做结构 | 独立 Adaptive Leader 文件 + 安装器二选一，不扩大默认 Leader | 常设工具授权是三端最宽的结构面，必须显式选择而非默认获得 |
| 直做判据 | 六条可判定条件 + 窄命令硬边界清单，弃用一切主观标准 | 主观标准不可验收，会退化为全直做或全委派 |
| 回退执行者 | 主模型 fallback Worker 变体接手，非 Leader 收回工具 | 角色沙箱与验收链不变，三端语义一致 |
| Codex 继承链 | fallback 双键省略 + 双默认移除 + 沙箱显式保留 | 官方优先级：文件 > 显式调用 > 默认 > 父级；任一残留截断继承 |
| Codex 旧默认迁移 | 默认停止提示，`--migrate-adaptive-config` 备份后仅删精确旧值 | 安装器无单键所有权，不得猜来源；遵守保留无关配置的承诺 |
| guard 判定顺序 | 全局硬拒绝 → strict 边界/adaptive 豁免 → 全局确认类 → adaptive ask | strict 不被弱化；adaptive 下风险类操作永不落入通用 ask |
| guard 全局匹配收窄 | 列为后续独立工作项，本轮仅测试固化现状 | 本方案不引入该局限，但已实证其存在；收窄属独立行为变更，需单独验证 |
| ZCode 回退节奏 | 先探针后声明，0.8.0 协议维持"停止并上报" | 不在共享协议里先宣称能力、失败后再回退文档 |
| ZCode 模式解析 | 管理块内唯一规范行，异常一律 strict；遍历到文件系统根 | fail-closed；深层工作目录不漏判 |
| `FAIL` 等任务失败 | 永不触发模型升级 | 任务证据与模型故障混淆会破坏失败路由可判定性 |
