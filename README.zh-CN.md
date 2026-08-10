# VS Code Copilot Leader Agents

这是一套仅依赖 **VS Code Stable + GitHub Copilot Chat 原生能力** 的 Leader/子代理方案。目标是让当前选中的高质量 Leader 专注于需求理解、调度、结果整合和验收，由低成本的 DeepSeek V4 Flash 执行本模式支持的工具任务。

## 核心架构

```text
用户
  ↓
Leader（跟随 Copilot Chat 当前模型）
  ├─ Analyzer：只读分析
  ├─ Implementer：委派范围内修改
  ├─ Tester：只读测试与构建
  ├─ Reviewer：只读差异审查
  └─ Arbiter：关键技术分叉的有限只读核验与独立裁决
```

四个 worker 上下文彼此独立，默认模型固定为 DeepSeek V4 Flash，且对用户隐藏。Arbiter 同样隐藏，但不配置固定 worker 模型：它仅在关键判断升级时以独立上下文继承 Leader 当前模型，并且只获得有限的 `read` 和 `search`。所有子代理都不能继续创建下级代理。

## 成本优先与风险裁量规则

- 所有开发任务建议从 `Leader` 开始；Leader 是风险、质量与成本的最终裁量者。
- Leader 只保留 `agent` 和 `todo` 工具。普通对话、需求澄清、调度、结果整合和验收可直接完成；支持的代码、文件和终端工作必须委派。
- 纯分析任务交给 Analyzer。目标和范围明确的修改任务可直接交给 Implementer，由它一次性完成必要调查、修改和自验证，无需先机械调用 Analyzer。
- Tester 和 Reviewer 只在高风险任务中强制使用；常规任务仅在它们能显著提高可信度时增加，避免重复扫描和无效调度。
- Worker 摘要本身不视为事实证据。影响范围、行为、契约、风险、实现和验收的实质性事实必须绑定紧凑证据账本，区分 `VERIFIED`、`PARTIAL` 和 `INFERRED`，并包含精确来源、最小证据、反证与覆盖缺口。
- 报告冲突、关键结论依赖部分证据或推断、引用不能直接支持结论时，先由 Analyzer 或 Reviewer 只核对点名的 `CLAIM_ID`，不得重复完整调查。
- 判断升级是关键节点保险丝，不是默认复审流程。Worker 完成合理取证和反证检查后，只有在两个以上技术方案会实质改变行为、契约、安全边界、架构责任或可回滚性，且没有证据充足的安全默认项时，才可返回 `ARBITRATION_REQUIRED`。
- Leader 仅对当前授权内、信息完整的技术分叉调用 Arbiter，每个用户任务最多一次。Arbiter 只能用 `read/search` 核验裁决包点名的最多三个决定性事实，不能广泛扫描，也不能执行命令或编辑。缺少运行事实先交给低成本 worker 补足；产品意图、新授权或高风险扩大必须询问用户。
- Arbiter 的一手核验和裁决不是用户授权，不能扩大范围，也不替代高风险任务的 Tester 和 Reviewer。
- 本模式的 worker 只覆盖工作区分析、修改、测试和审查。如果任务需要浏览器、GitHub 或其他 worker 未配置的工具，Leader 必须提示用户退出穷鬼模式，而不是自行接管。
- 删除、依赖或锁文件、配置或密钥、数据库或迁移、持久化数据写入、外部服务或部署、权限或安全边界、影响范围不清或难以回滚的变更属于高风险：必须先说明范围和影响并获得用户明确确认，实施后必须通过独立 Tester 与 Reviewer。
- `批准执行` 是推荐的高风险确认短语，清晰的自然语言确认同样有效；确认不覆盖之后的实质性高风险扩大。
- Git 写操作、危险删除、依赖安装、迁移、部署，以及 GitHub 写入或未知 GitHub 动作，仍由 Hook 拦截或要求确认；命名明确的 GitHub 只读查询不受影响。

## 安装要求

- VS Code Stable 1.128+
- GitHub Copilot Chat 已启用 Agent
- Python 3.9+
- `code` 命令已加入 PATH
- GCMP 插件；安装脚本会自动检测并安装

API Key、Base URL 等敏感配置由用户在 GCMP 中自行填写，本仓库不会读取或保存。

## 一键安装

### macOS / Linux

```bash
chmod +x install.sh
./install.sh
```

### Windows PowerShell

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\install.ps1
```

安装器会：

1. 检测并安装 `vicanent.gcmp`；
2. 尝试识别 DeepSeek V4 Flash 的实际模型 ID；
3. 安装全局 Leader、四个隐藏 worker 与一个隐藏 Arbiter 到 `~/.copilot/agents`；
4. 安装 Skills 到 `~/.copilot/skills`；
5. 安装全局安全 Hook 到 `~/.copilot/hooks`；
6. 同步更新默认 Profile 及全部现有 Profile；
7. 写入低成本 utility model 配置，不覆盖用户主动选择的 Ask、Implement、Explore、Plan 模型；
8. 自动运行校验。

所有同名文件和被修改的 `settings.json` 都会先备份。安装器不会保存 GCMP 凭据。
安装器会将被修改的 JSONC 设置规范化为标准 JSON；原注释保留在备份中，不保留在重写后的文件中。

## 模型识别

优先级如下：

1. 安装参数 `--model` / `-Model`；
2. 环境变量 `COPILOT_WORKER_MODEL`；
3. 已有 VS Code 设置中的 DeepSeek V4 Flash 值；
4. GCMP 扩展文件中的可识别值；
5. 默认值：`DeepSeek-V4-Flash (gcmp.deepseek)`。

若 worker 模型不可用或结果不足，Leader 必须停止并如实说明，请用户显式指定替代 worker 模型，或退出本模式后由其他 Agent 处理。不得由 Leader 静默接管工具任务。

## 使用

1. 重载 VS Code。
2. 在 Copilot Chat Agent 选择器中选择 `Leader`。
3. 输入开发任务；Leader 会将所有需要工具的工作默认委派给低成本 worker，仅在关键技术分叉时使用一次性 Arbiter 保险丝。
4. 仅高风险任务需要确认；可使用：

```text
批准执行
```

这不是唯一有效的确认措辞，清晰的自然语言确认同样有效。VS Code Stable 当前没有受支持的配置可自动将自定义 Agent 设置为默认入口，因此首次及必要时需要手动选择 `Leader`。四个 worker 和 Arbiter 通过 `user-invocable: false` 隐藏。

## 工作区规则冲突

全局规则默认生效。若工作区的 `AGENTS.md`、Copilot Instructions 或其他规则与全局规则冲突：

1. Leader 停止执行；
2. 说明冲突、影响和候选处理方式；
3. 由用户仲裁；
4. 仲裁结果写入当前项目的 `.copilot-leader/arbitration.local.md`；
5. 将 `.copilot-leader/` 写入 `.git/info/exclude`，仅保存在本机。

## 原生能力限制

VS Code 原生能力可以硬性限制工具、隐藏子代理、关闭嵌套子代理，并通过 Hook 拦截已知危险命令。但它无法把聊天中的高风险确认以密码学方式绑定到精确文件列表。因此：

- 工具隔离与危险操作：硬约束；
- 风险分级、高风险确认、范围控制和返工协议：Agent 指令软约束；
- 真正强制的事务式授权需要自定义扩展或外部调度器，本项目按需求不引入。

原生子代理的每次调用都是无状态的，Leader 无法向同一个子代理继续发消息。因此仲裁后会把原目标、未变授权、worker 检查点、裁决结果和验收标准回放给新的同类 worker 调用，不声称恢复原上下文。

详见 [docs/NATIVE_LIMITATIONS.md](docs/NATIVE_LIMITATIONS.md)。

## 校验

```bash
python3 scripts/validate.py
python3 scripts/validate.py --installed
```

## 许可证

MIT
