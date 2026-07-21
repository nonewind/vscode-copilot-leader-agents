# VS Code Copilot Leader Agents

这是一套仅依赖 **VS Code Stable + GitHub Copilot Chat 原生能力** 的 Leader/子代理方案。目标是让当前选中的高质量模型只负责需求理解、计划、调度、审核与最终结论，其余执行工作默认交给低成本的 DeepSeek V4 Flash。

## 核心架构

```text
用户
  ↓
Leader（跟随 Copilot Chat 当前模型）
  ├─ Analyzer：只读分析
  ├─ Implementer：授权范围内修改
  ├─ Tester：只读测试与构建
  └─ Reviewer：只读差异审查
```

四个子代理上下文彼此独立，默认模型固定为 DeepSeek V4 Flash，且对用户隐藏。子代理不能继续创建下级代理。

## 行为规则

- 所有开发任务必须从 `Leader` 开始。
- Leader 默认不读取代码、不搜索、不执行命令，只通过子代理获得结构化结果。
- 只有结果冲突或必须直接验证时，Leader 才能执行只读检查和验证命令。
- Leader 永远不能修改文件。
- 批准前，Leader 只能调用只读 Analyzer 收集事实。
- Leader 输出计划后，必须等待用户准确回复：`批准执行`。
- 用户批准整体计划后，Leader 可自行组织并行任务、测试、审查和返工。
- 只有 Implementer 能修改代码。
- Implementer 只能修改已批准范围，不得主动扩展扫描或文件范围。
- Tester 通过后才能进入 Reviewer；两者均通过后才能完成。
- 目标、文件范围、风险、依赖、数据库、环境或外部服务影响扩大时，必须停止、说明情况、重新计划并再次等待 `批准执行`。
- 默认模型失败时必须停止并要求用户显式指定替代模型，禁止自行升级。
- 禁止 Git 提交、推送、切换分支、合并、回滚等写操作。
- 删除文件、安装依赖、数据库迁移、配置变更和外部发布默认禁止；必要时由 Hook 要求显式确认或直接阻断。

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
3. 安装全局 Leader 与四个隐藏子代理到 `~/.copilot/agents`；
4. 安装 Skills 到 `~/.copilot/skills`；
5. 安装全局安全 Hook 到 `~/.copilot/hooks`；
6. 同步更新默认 Profile 及全部现有 Profile；
7. 写入低成本 utility model 配置；
8. 自动运行校验。

所有同名文件和被修改的 `settings.json` 都会先备份。安装器不会保存 GCMP 凭据。
安装器会将被修改的 JSONC 设置规范化为标准 JSON；原注释保留在备份中，不保留在重写后的文件中。

## 模型识别

优先级如下：

1. 安装参数 `--model` / `-Model`；
2. 环境变量 `COPILOT_WORKER_MODEL`；
3. 已有 VS Code 设置中的 DeepSeek V4 Flash 值；
4. GCMP 扩展文件中的可识别值；
5. 默认值：`gcmp.deepseek/gcmp.deepseek:::deepseek-v4-flash`。

若运行时模型不可用，Leader 必须暂停并要求用户明确指定替代模型，不得回退到 Leader 模型继续执行。

## 使用

1. 重载 VS Code。
2. 在 Copilot Chat Agent 选择器中选择 `Leader`。
3. 输入开发任务。
4. 查看 Leader 的计划。
5. 确认后准确回复：

```text
批准执行
```

VS Code Stable 当前没有受支持的配置可自动将自定义 Agent 设置为默认入口，因此首次及必要时需要手动选择 `Leader`。四个子代理通过 `user-invocable: false` 隐藏。

## 工作区规则冲突

全局规则默认生效。若工作区的 `AGENTS.md`、Copilot Instructions 或其他规则与全局规则冲突：

1. Leader 停止执行；
2. 说明冲突、影响和候选处理方式；
3. 由用户仲裁；
4. 仲裁结果写入当前项目的 `.copilot-leader/arbitration.local.md`；
5. 将 `.copilot-leader/` 写入 `.git/info/exclude`，仅保存在本机。

## 原生能力限制

VS Code 原生能力可以硬性限制工具、隐藏子代理、关闭嵌套子代理，并通过 Hook 拦截已知危险命令。但它无法把聊天中的 `批准执行` 以密码学方式绑定到精确文件列表。因此：

- 工具隔离与危险操作：硬约束；
- 计划批准、范围控制和返工协议：Agent 指令软约束；
- 真正强制的事务式授权需要自定义扩展或外部调度器，本项目按需求不引入。

详见 [docs/NATIVE_LIMITATIONS.md](docs/NATIVE_LIMITATIONS.md)。

## 校验

```bash
python3 scripts/validate.py
python3 scripts/validate.py --installed
```

## 许可证

MIT
