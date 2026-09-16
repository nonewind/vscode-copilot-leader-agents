# 穷鬼模式自适应升降级方案（v3.1，实施基线）

状态：v3.1 源码实施完成，静态校验与仓库测试通过；三端真实客户端 Smoke 尚未运行，因此 Hook 触达、模型继承、sandbox 实际覆盖与计费仍不得宣称已验证。目标版本为 0.8.0；ZCode 的模型回退仍需独立运行时探针，若成立再进入后续版本。本文件与 v2 并存，便于逐项对照。

## 1. 目标与边界

本方案解决两个彼此独立的问题：

1. 对足够小、可判定、低风险的工作，允许 Leader 直接完成，避免派发成本高于工作本身；
2. 低价 Worker 因模型或推理档位配置被确定性拒绝时，可选择由父模型的同角色 Worker 接手一次，而不是让 Leader 收回工具。

非目标：不因任务失败、质量不足或 `BLOCKED` 自动换高价模型；不把静态校验写成运行时证明；不改变 Git 写入、删除、依赖、迁移、部署和外部写操作的确认边界；不在 0.8.0 宣称未经探针证明的 ZCode 模型继承能力。

## 2. 两条独立状态轴

### 2.1 执行模式

- `strict`：Leader 只规划、派发、裁决和验收，所有修改及命令仍交给 Worker；
- `adaptive`：仅在第 4 节全部条件满足时，Leader 可以直接进行一次局部修改或一次窄命令。

### 2.2 模型回退模式

- `stop`：模型或档位不可用时停止并报告配置错误；
- `parent-worker`：至多一次，由不钉模型与档位的同角色 fallback Worker 继承父模型继续原包。

两条状态轴不互相隐含。启用 `adaptive` 不自动启用 `parent-worker`，启用回退也不授权 Leader 直做。

### 2.3 0.8.0 默认值

| 平台 | 执行模式默认值 | 回退模式默认值 | 与 0.7.0 的关系 |
| --- | --- | --- | --- |
| VS Code | `strict` | `parent-worker` | 回退保持现状；直做需显式启用 |
| Codex | `strict` | `stop` | Leader 行为保持现状；0.8.0 不再设置项目级子代理模型/档位默认值 |
| ZCode | `strict` | `stop` | 两项均保持现状；0.8.0 只提供执行模式切换 |

安装器的无旗标行为：若已安装 0.8.0 模式状态则保留；若从没有模式状态的 0.7.0 升级，则采用上表默认值。VS Code 的安装状态缺失或非法时取 strict；Codex/ZCode 的模式行缺失、重复、拼错或位于管理块外时 fail-closed 到上表默认值。

## 3. 共享协议的写法

`src/protocols/poor-mode.md` 只描述能力门，不无条件授权直做：

> Direct execution is disabled unless the active platform policy explicitly declares adaptive execution mode. Missing or malformed mode state is strict.

共享失败路由按平台和回退模式解释：

- VS Code 维持现有一次同角色、无模型覆盖的回退；
- Codex 仅在安装策略明确声明 `parent-worker` 时调用 fallback Worker，否则停止；
- ZCode 0.8.0 始终停止并报告配置问题。

`sync_poor_mode.py` 的目标从三份扩大到四份：strict VS Code Leader、adaptive VS Code Leader、Codex `AGENTS.md`、ZCode `AGENTS.md`。平台模式声明位于生成块外，由各平台安装器管理；共享块只消费该声明。

不再要求 strict 文件或安装产物逐字节不变。验收改为行为不变量：strict 工具面不扩大、Leader 不执行写操作、风险决策不弱化、原有 Worker 路由仍成立。

## 4. Adaptive 直做合同

Leader 在第一次修改或命令调用之前，必须确认以下条件全部成立：

1. 当前回合已有直接证据定位到一个明确文件和局部位置，不能只依赖历史记忆；
2. 工作只包含一个局部、可逆的源文件修改，或者一条不修改源文件的窄命令；
3. 不涉及删除、依赖或锁文件、配置、密钥、迁移、持久数据、网络、外部服务、部署、权限、生成文件或批量格式化；
4. 不改变公共 API、跨模块协议、行为边界、持久化格式或安装契约；
5. 不需要跨文件调查、第二次源修改或超过一步的窄验证；
6. 当前没有其他 Writer 持有目标路径或相关生成资源；
7. 已先输出 `DIRECT: <可核对的条件摘要>`。

“窄命令”限定为一个已知的本地诊断或验证程序调用：无 shell 复合、管道、重定向和命令替换；无网络、依赖、环境或外部状态变更；除工作区内正常缓存和测试/构建产物外不写入文件。源文件格式化、代码生成和修复脚本不属于窄命令。

### 4.1 中途失配与所有权转移

- 第一次源修改完成后，Leader 即是该路径的 Writer；
- 若发现范围扩大、验证失败或需要第二次源修改，Leader 停止直做，先读取当前 diff 并形成 checkpoint；
- 只有确认 Leader 的工具调用已结束后，才把该路径连同 checkpoint 移交 Implementer；
- 不通过“重新命名任务”重置直做额度，也不并发启动第二个 Writer。

`DIRECT` 次数、后续转 Worker 次数和验证结果进入成本证据，不能把失败的直做隐藏在普通派发中。

## 5. 模型回退合同

### 5.1 触发条件

只允许以下两类事件触发：

1. 错误明确指出模型或推理档位不支持、不可解析或不可用于当前提供方；
2. 确认原调用已经终止后，一次同模型瞬时重试仍失败。

`FAIL`、`BLOCKED`、`NEEDS_LEADER`、超出范围、证据不足和质量不足都是任务结果，不触发模型升级。

### 5.2 执行规则

- 调用前披露回退原因；
- 调用前确认失败线程已经终止；若角色可写，还要读取并传递其 checkpoint，避免第二个 Writer 与残留调用重叠；
- 每个包至多一次；
- fallback Worker 保持原角色、原 `GOAL`、`BOUNDARIES`、`DONE`、checkpoint 和安全指令；
- fallback Worker 不设置 `model` 与 `model_reasoning_effort`，从父线程解析这两个值；
- 不寻找第三模型，不把回退运行计入低价模型成绩；
- 用户禁止回退或限制花费时立即停止。

## 6. 平台实现

### 6.1 VS Code

新增 `src/agents/leader-adaptive.agent.md`：与 strict Leader 使用同一个 `name: Leader`，工具集为 strict 六项加 `edit`、`execute`；同时只安装一个 Leader 文件。

两份 Leader 在生成块外分别包含唯一的 `leader-worker-execution-mode: strict|adaptive`，并共同声明 `leader-worker-fallback-mode: parent-worker`；`validate.py` 校验声明与文件身份相符。

`scripts/install.py` 增加可选 `--leader strict|adaptive`：

- 显式旗标优先；
- 无旗标时读取 `install-state.json` 的 `leader_mode`；
- 旧状态无该键时取 `strict`；
- 将选中源文件统一安装为 `leader.agent.md`，并把解析后的模式写回状态；
- dry-run 必须显示“检测值、请求值、最终值、源文件、目标文件”。

strict 的工具串继续由 `validate.py` 和测试精确锁定；adaptive 使用独立常量校验。共享协议同时同步到两份 Leader，adaptive 条件块不再手工复制。

VS Code Hook 的命令风险匹配也必须在 0.8.0 收窄到真实命令字段。编辑正文中的命令文本不得触发 Git、依赖或部署规则；敏感编辑只根据工具类型和目标路径判断。Python 与 PowerShell Hook 必须保持同一决策矩阵。

GitHub 等专用工具仍按工具名称与动作分类，不因命令字段收窄而失去写操作确认；禁止再用整段 payload 的自由文本承担动作识别。

### 6.2 Codex

Codex 没有主线程结构性工具裁剪，因此执行模式是协议约束，不能描述为硬隔离。`codex/AGENTS.md` 管理块内增加唯一模式行：

```text
leader-worker-execution-mode: strict|adaptive
leader-worker-fallback-mode: stop|parent-worker
```

`scripts/install_codex.py` 增加 `--mode` 和 `--fallback`；两者默认 `None`，先保留旧管理块内的合法值，未检测到才使用 `strict` 与 `stop`。异常模式行按默认值处理并输出警告。

#### parent-worker 文件

仅在最终回退模式为 `parent-worker` 时安装四个 `leader_*_fallback.toml`。fallback 与 base 的角色、安全指令和沙箱默认逐行规范化比较，允许的差异只有名称、描述、`model` 与 `model_reasoning_effort`。

安装器新增项目级受管状态，记录 fallback 模式、受管文件路径和安装后哈希。首次安装若同名目标已经存在且内容不同则停止，不覆盖；切回 `stop` 时，只有目标哈希仍等于记录的受管哈希才先备份再移除。文件被用户修改、状态缺失或哈希不符时停止并保留文件，不能只凭文件名判断所有权。

基础 Worker 继续显式钉住低价模型和角色档位；fallback 同时省略两个键。根据[官方 Codex 子代理文档](https://learn.chatgpt.com/docs/agent-configuration/subagents)，文件值优先于显式调用、`[agents]` 默认和父值；两个键均未设置且不存在更高优先级覆盖时，才解析到父模型与父档位。

#### `[agents]` 默认值迁移

0.8.0 的源码基线与静态受管键集只保留 `enabled` 和 `max_concurrent_threads_per_session`，不再包含 `default_subagent_model` 与 `default_subagent_reasoning_effort`。四个基础 Worker 已分别显式设置模型和档位；移除项目级默认不会改变它们，但会影响项目内其他未显式设置相应键的子代理，因此旧值迁移必须披露并显式授权。

`--migrate-agent-defaults` 是一次性精确旧值迁移，不与执行模式或回退模式绑定。安装器永不自动补回这两个键。

对两个旧键分别分类为 `absent`、`legacy`、`custom`，再原子决定：

| 聚合状态 | 无迁移旗标 | 有迁移旗标 |
| --- | --- | --- |
| 两键均 `absent` | 继续 | 继续 |
| 存在一至两个键，且所有已存在键均为精确旧值 | 停止并提示 | 一次备份后删除所有已存在旧键，再继续 |
| 任一键为 `custom` | `stop` 模式保留并继续；`parent-worker` 停止 | 不删除 custom；`parent-worker` 仍停止 |
| TOML 重复节、重复键或无法安全解析 | 停止，零写入 | 同样停止，零写入 |

若一键为精确旧值、另一键为 custom，迁移旗标只删除精确旧值并保留 custom；`parent-worker` 因 custom 仍会阻断，`stop` 可继续。所有分类、冲突检查、受影响文件扫描均在备份和写入前完成。迁移提示必须说明这两个键是项目级全局默认：移除后，其他未显式设置模型或档位的自定义及内置子代理也可能改为继承父线程。安装器列出项目内检测到的非受管 agent 文件及其缺失键，但不替用户修改。

安装器先计算完整变更计划并完成所有冲突检查，再建立同一批次备份、通过同目录临时文件替换目标；受管状态只在全部写入成功后更新。中途异常时如实报告错误和备份位置，依靠幂等重跑收敛，不实现跨文件自动回滚。

从 `parent-worker` 切回 `stop` 时不擅自恢复旧默认值；只移除 fallback 文件并提示当前 `[agents]` 状态。恢复全局默认属于另一项显式配置操作。

#### 沙箱表述

fallback 文件保留与 base 相同的 `sandbox_mode`，但它只是 agent 文件默认值，不是不可覆盖保证。[官方文档](https://learn.chatgpt.com/docs/agent-configuration/subagents)说明父回合的实时权限覆盖会在创建子代理时重新应用，即使自定义 agent 文件设置了不同默认值。因此：

- 普通权限模式下验证 Analyzer/Reviewer 的 read-only 默认；
- 另做父线程实时放宽权限的负向探针，记录实际覆盖行为；
- 文档只把协议禁写和默认沙箱作为防线，不宣称实时覆盖下仍有结构性只读。

同步改写 `docs/CODEX.md` 的权限继承说明与 Smoke，以及 `codex/skills/leader-worker-mode/SKILL.md` 中 “structurally read-only” 的过度声明。Smoke 同时覆盖严格父权限限制可写 Worker、宽松父权限覆盖只读默认两个方向。

### 6.3 ZCode

0.8.0 只实现执行模式，不发布 fallback agent。`zcode/AGENTS.md` 管理块包含唯一 `leader-worker-execution-mode` 行；缺失或异常即 strict。

`scripts/install_zcode.py --mode strict|adaptive` 的解析顺序与 Codex 一致：显式值、旧合法值、strict。重装默认保留已选模式；从 0.7.0 升级因没有标记而进入 strict。

Guard 决策顺序：

1. 从项目根或最近祖先的完整管理块解析模式；
2. 仅对真实命令工具的 `command` 字段执行 Git 写入、危险删除、依赖、迁移和部署匹配；
3. 全局硬拒绝先执行；
4. strict 对编辑、命令和 `mcp__*` 执行边界拒绝；
5. adaptive 仍拒绝 `mcp__*`，风险确认类保持专项 ask，其余普通编辑和命令使用通用 ask；
6. 边界未激活时保留全局安全判定，其余放行。

编辑工具只读取目标路径等结构字段进行敏感路径判定，不能扫描正文并把示例命令当成真实操作。目录搜索遍历到文件系统根；会话明确提供的项目根优先。运行时 Smoke 必须同时证明 primary 的决策和 Worker 正常执行不被误拦。

0.8.0 明确把 VS Code 已有的敏感路径确认规则移植到 ZCode。它会使边界未激活项目中的 `.env`、锁文件、工作流、基础设施和迁移路径编辑新增一次 ask；这是有意的跨平台安全统一，必须写入 `docs/ZCODE.md` 与变更日志，而不是隐含行为。

## 7. Guard 统一决策矩阵

以下矩阵只给出 primary/Leader 来源调用的语义目标。VS Code strict 依靠工具面让写操作不可达，ZCode strict 依靠 Guard deny；不得据此声称 VS Code Hook 能识别主线程身份。

| 输入 | strict 结果 | adaptive 结果 | 边界未激活 |
| --- | --- | --- | --- |
| 真实 Git 写命令 | 不可达（VS Code）/ deny（ZCode） | deny | deny |
| 编辑正文含 Git 写命令文本 | 不可达（VS Code）/ deny（ZCode） | 按普通编辑处理 | 按普通编辑处理 |
| 危险删除命令 | 不可达（VS Code）/ deny（ZCode） | deny | deny |
| 独立字面目标删除 | 不可达（VS Code）/ deny（ZCode） | 专项 ask | 专项 ask |
| 依赖、迁移、部署命令 | 不可达（VS Code）/ deny（ZCode） | 专项 ask | 专项 ask |
| 敏感路径编辑 | 不可达（VS Code）/ deny（ZCode） | 专项 ask | 专项 ask |
| 普通编辑 | 不可达（VS Code）/ deny（ZCode） | ZCode ask；VS Code 走平台原生权限 | allow |
| 普通命令 | 不可达（VS Code）/ deny（ZCode） | ZCode ask；VS Code 走平台原生权限 | allow |
| `mcp__*` | 不可达（VS Code）/ deny（ZCode） | 不可达（VS Code）/ deny（ZCode） | 平台原行为 |

同一组 case ID 和输入夹具要覆盖 Python Hook、PowerShell Hook 和 ZCode Guard，每个平台维护明确的期望值，防止共享规则漂移又掩盖结构差异。若无法共享实现，至少共享数据驱动的输入。

Worker 来源单独建模：ZCode 已知 Worker 不触发 primary guard；VS Code Hook 是否覆盖子代理工具调用必须在 Phase 1 真实 Smoke 中确认。静态测试只证明输入分类，不预设运行时触达范围；Smoke 结果回填 `docs/NATIVE_LIMITATIONS.md`。无论触达范围如何，真实 Git、删除、依赖、迁移和部署命令的既有 deny/ask 覆盖不得因字段化收窄而弱化。

## 8. 验收门

### 8.1 静态与单元测试

1. `sync_poor_mode.py` 的四目标完全同步；
2. strict/adaptive Leader 工具串分别精确匹配；
3. Codex base/fallback 规范化一致性通过；
4. Codex 九种键组合归并到第 6.2 节四类结果，且冲突路径零写入；
5. 三份 guard 对共享 case 给出各平台声明的期望结果，Python/PowerShell 的共同能力保持一致，真实命令类规则覆盖不弱化；
6. 模式行缺失、重复、非法、块外伪造均 fail-closed；
7. 安装器 dry-run、首次安装、重复安装、切换和回退路径均保留无关内容；
8. `validate.py`、全量单元测试和 `git diff --check` 通过。

### 8.2 运行时 Smoke

| 平台 | strict | adaptive | fallback |
| --- | --- | --- | --- |
| VS Code | Leader 无 edit/execute；小任务仍派发 | 合格小改先声明 `DIRECT` 且零 Worker；不合格用例仍派发；确认 Hook 对 primary/Worker 的实际触达范围 | 保持现有同角色无覆盖回退 |
| Codex | 主线程不直做 | 合格小改可直做；明确记录为提示词行为 | 临时项目启用 `parent-worker`，验证父模型与父档位；分别记录普通权限和实时权限覆盖下的沙箱行为 |
| ZCode | 主线程编辑/命令被 deny | 普通编辑/命令逐次 ask；风险操作保持专项规则 | 0.8.0 必须停止并报告，不得暗中回退 |

静态、安装器和一次性项目测试都不能替代真实新会话 Smoke。每个平台只对实际执行过的层级作结论。

## 9. 实施阶段

### Phase 0：协议与测试骨架

- 新增模式语义、共享能力门和四目标同步；
- 先写模式解析、迁移矩阵、guard 字段分类和安装选择测试；
- 不升级版本，不宣称运行时能力。

### Phase 1：VS Code

- 新增 adaptive Leader、安装状态保存和 Hook 字段收窄；
- 完成 strict/adaptive 安装与真实会话 Smoke；
- 未通过时不推进版本发布。

### Phase 2：Codex

- 实现双状态轴、fallback 条件安装、原子迁移与沙箱限制说明；
- 在一次性项目完成安装矩阵和真实子代理继承 Smoke；
- 失败时 Codex 回退保持 `stop`，不影响 adaptive 直做的独立评估。

### Phase 3：ZCode

- 实现执行模式、全祖先解析和 Guard 字段收窄；
- 完成 strict/adaptive/边界未激活的运行时矩阵；
- fallback 只做隔离探针，不进入 0.8.0 发布物。

### Phase 4：发布门

- 所有已声明能力的真实 Smoke 通过；
- 版本源、两个 marketplace、插件清单、安装文档和变更日志一致升至 0.8.0；
- 清楚区分源码状态、安装状态和已发布状态；
- 基准中 `DIRECT`、fallback、重试和返工单列，不与低价模型纯运行混榜。

## 10. 预期变更面

- 共享：`src/protocols/poor-mode.md`、`scripts/sync_poor_mode.py`、`scripts/validate.py`、测试与相关文档；
- VS Code：新增 adaptive Leader，修改安装器、安装状态、Python/PowerShell Hook；
- Codex：新增四个 fallback 源文件，修改 AGENTS、Skill、安装器和文档；`codex/config.toml` 与静态受管键集移除两个全局默认键，以显式旗标一次性迁移精确旧值；
- ZCode：修改 AGENTS、Skill、安装器、Guard、插件版本和文档；0.8.0 不新增 fallback agent；在 ZCode 文档和变更日志披露边界未激活时新增的敏感路径 ask；
- 不修改基准评分公式，只新增事件分类和混榜限制说明。

## 11. 反审后锁定的决定

1. 保留执行模式与回退模式两条独立状态轴，不引入组合模式名；
2. Codex fallback 默认 `stop`，仅显式 opt-in；
3. 源码静态移除全局模型/档位默认键，旧精确值一次性迁移，不按模式自动恢复；
4. `sandbox_mode` 只承诺 agent 默认值，父线程实时权限覆盖优先；
5. guard 字段化匹配作为 0.8.0 bug 修复，且必须保持真实命令规则覆盖；
6. ZCode adaptive 进入 0.8.0，fallback 继续由后续探针和独立版本门控。
