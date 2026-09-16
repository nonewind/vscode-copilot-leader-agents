# 对 v3 方案的反审（2026-09-16）

结论：**v3 总体优于 v2，建议以 v3 为基础进入实施，但有 1 个必须在 Phase 0 前解决的规格矛盾（F1）和 4 项需要收紧的发现（F2-F5）。** 六个自列挑战点中五个维持 v3 立场，一个（迁移）需修订。

## 一、事实核查（反审新增验证）

| v3 的论断 | 核实结果 |
| --- | --- |
| VS Code Python/PowerShell Hook 存在与 ZCode guard 相同的全文匹配缺陷 | **成立**。[src/hooks/guard.py:130-144](../src/hooks/guard.py) 与 [guard.ps1](../src/hooks/guard.ps1) 均对 `tool_name + flatten(tool_input)` 匹配 Git 硬拒绝——编辑正文含 Git 子命令字面量即误拦；ZCode 侧已有实录 |
| 敏感路径编辑规则 | **v3 不是新发明**：[guard.py:169-179](../src/hooks/guard.py) 已有（.env、credentials/secrets、锁文件、Dockerfile、workflows/k8s/terraform/migrations + edit 类工具 → ask）。但它**同样对 `combined` 匹配**——正文提到 `package-lock.json` 即误触发，属同一缺陷家族，字段化收窄必须一并覆盖 |
| `sandbox_mode` 只是被父线程实时权限覆盖的默认值 | **成立**。官方文档明确："Codex also reapplies the parent turn's live runtime overrides when it spawns a child … even if the selected custom agent file sets different defaults"，且包含 sandbox/approval。宽松父线程可覆盖子代理 read-only 默认；严格父线程方向仓库已记载（[docs/CODEX.md:13](CODEX.md)） |
| GitHub 工具按名称与动作分类 | 成立（[guard.py:109-118](../src/hooks/guard.py)，按 `tool_name` 前缀分类，不扫 payload），字段化收窄不影响该规则 |
| Codex 九种键组合归并四类 | 数学成立：两键 ×（absent/legacy/custom）= 9，按 v3 第 6.2 节四行全覆盖 |

## 二、六个挑战点的裁定

1. **两条独立状态轴——维持。** 两个机制的风险归属不同（直做 = 写权限暴露；回退 = 成本模型完整性）、平台可用性不同（VS Code 现状已有回退，ZCode 两者皆无）、变更节奏不同（ZCode 回退被探针门控）。独立开关避免"要直做就得接受回退"的耦合。代价是 4 种组合的测试面，可接受。约束：只保留两行声明，不引入组合模式名。
2. **Codex 回退默认 `stop`——维持。** 三个理由：移除全局默认键会改变项目内**其他未钉模型子代理**的解析路径，必须显式选择；默认运行保持基准纯净（回退运行单列的度量前提）；与默认值表诚实性一致。VS Code 默认 `parent-worker` 是 0.7.0 既有行为的延续而非新增暴露，不改。
3. **迁移设计——部分修订，见 F1/F2。** 披露义务（全局默认影响的提示、非受管 agent 清单）充分；原子性与基线保留两项要改。
4. **接受 sandbox 只是默认值——维持，且必须落到具体文件。** 这是 v3 对仓库现有文档的实质性纠错：[docs/CODEX.md:42](CODEX.md) "Analyzer and Reviewer are structurally read-only" 与 [codex SKILL.md:12](../codex/skills/leader-worker-mode/SKILL.md) 同句在宽松父线程下**过度声明**，须随 v3 一并改写为"协议禁写 + 默认沙箱"双防线表述；负向探针（宽松父线程下子代理是否可写）列为 Phase 2 必测。
5. **guard 字段化纳入 0.8.0——维持，且比 v3 论证得更强。** 不只是防回归：VS Code 钩子是**用户级全局安装**（[install.py:248-295](../scripts/install.py) 装进用户 copilot/hooks），对所有会话生效；若钩子对 Worker 子代理调用也触发（VS Code 侧未验证，见 F4），则 strict 模式下 Worker 编辑含 Git 字样文件**今天就可能被误拦**。收窄是修 bug 不是加需求。约束：只做字段化与既有规则的移植统一，不新增规则；注意收窄不能弱化真实命令类规则的覆盖。
6. **ZCode 版本切分——维持。** 与 v2 探针门控一致；两轴独立使部分发布在逻辑上自洽；ZCode 回退有已知结构阻力（模型仅由插件 frontmatter 解析、无逐调用覆盖），延后是证据驱动而非任意。

## 三、新发现（v3 未自列）

**F1（P1，Phase 0 前必须解决）：`codex/config.toml` 保留 0.7.0 基线与"切回不恢复"自相矛盾。** v3 第 10 节要求源码基线保留两个默认键、仅迁移时删除，第 6.2 节又要求"切回 `stop` 时不擅自恢复旧默认值"。但现有 `merge_config` 语义是"受管键缺失即补齐"——若两键仍是 stop 模式的受管键，任何一次 stop 重装都会把已迁移删掉的键加回来，直接违反"不恢复"；若改为按模式增删受管键集，则切回 stop 又必然恢复，两条文本互斥。**建议修订**：0.8.0 源码基线直接移除两个默认键（对显式钉模的基础 Agent 冗余；使未钉模型子代理回到 Codex 原生的父级继承），受管键集静态化为 `enabled` + `max_concurrent_threads_per_session`，一次性精确值迁移处理旧安装——无模式依赖、无恢复悖论，迁移提示照旧披露全局影响。

**F2（P2）：批次中途回滚机械过度设计。** "计算完整计划→全部冲突检查→同批次备份→临时文件替换"充分且便宜，应当保留；"中途异常恢复本批已触碰文件并报告恢复结果"对一个本地开发工具安装器收益/复杂度失衡。**建议**：保留前三项 + 每文件 `os.replace` 原子替换；失败时如实报错并指出备份位置，靠"安装器幂等、重跑收敛"覆盖剩余场景。回滚机制不做。

**F3（P2）：sandbox 纠错必须点名改写位置。** 除第 2.4 条所列两处过度声明外，[docs/CODEX.md:13](CODEX.md) 只覆盖了严格父线程方向，需补宽松方向；Smoke 第 8 步应扩为双向（严格父线程限制 Implementer / 宽松父线程是否突破 Analyzer read-only）。

**F4（P2）：决策矩阵只建模了主 Agent 来源的调用，且 VS Code 钩子触发范围未验证。** 矩阵各格的"不可达（VS Code）"注记只对 Leader 成立；若 VS Code Copilot 钩子对子代理工具调用也触发（ZCode 已实证不触发，VS Code 未知），Worker 的编辑/命令同样过钩子，strict 行为今天就受误匹配影响。**建议**：Phase 1 Smoke 增加一步"确认钩子触达范围（primary/子代理）"；矩阵加一行"来源：Worker 发起"或在脚注声明建模范围，期望值按实测回填。

**F5（P3）：敏感路径规则移植到 ZCode 是边界未激活用户的行为变更。** VS Code 版今日已有此规则，移植统一是对的；但 ZCode guard 在未激活 Leader/Worker 的项目里也会多出 .env/锁文件等编辑的 ask。应当作为**有意识的决策**写进 v3 与 ZCODE.md（含变更日志），而不是隐含在矩阵里；若不愿扩大 0.8.0 面，可单列推迟——倾向接受移植，理由是规则已在一个平台出厂且语义一致。

## 四、建议的 v3.1 修订清单

1. 按 F1 改写第 6.2 与第 10 节：源码基线删双键、受管键集静态化、删除"切回不恢复"段（改为"切回 stop 仅移除 fallback 文件；`[agents]` 保持迁移后状态"）。
2. 按 F2 简化原子迁移为"计划先行 + 批次备份 + 每文件原子替换 + 幂等重跑"，删除中途回滚义务。
3. 第 6.2 沙箱节点名 docs/CODEX.md（13/42 行）与 codex SKILL.md 的改写，Smoke 8 扩为双向。
4. 第 7 节矩阵加来源维度或脚注；Phase 1 Smoke 加钩子触达范围验证。
5. 第 6.3/第 10 节将 ZCode 敏感路径移植写成显式决策与文档变更项。
6. 字段化收窄加一条约束：真实命令类规则（Git/删除/依赖/迁移/部署）的覆盖不得弱化，用共享 case 夹具回归证明。

以上完成后，v3 可作为 0.8.0 实施基线。
