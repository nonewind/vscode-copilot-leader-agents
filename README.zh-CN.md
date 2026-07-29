# VS Code Copilot Leader Agents

这是一套仅依赖 **VS Code Stable + GitHub Copilot Chat 原生能力** 的 Leader/子代理方案。目标是让当前选中的高质量 Leader 自主判断何时直接处理、何时值得委派给低成本的 DeepSeek V4 Flash，而不是把所有任务机械地拆成固定流程。

## 核心架构

```text
用户
  ↓
Leader（跟随 Copilot Chat 当前模型）
  ├─ Analyzer：只读分析
  ├─ Implementer：委派范围内修改
  ├─ Tester：只读测试与构建
  └─ Reviewer：只读差异审查
```

四个子代理上下文彼此独立，默认模型固定为 DeepSeek V4 Flash，且对用户隐藏。子代理不能继续创建下级代理。

## 风险裁量规则

- 所有开发任务建议从 `Leader` 开始；Leader 是风险、质量与成本的最终裁量者，而非只会转交任务的调度器。
- Leader 内置完整的 VS Code、执行、编辑、搜索、浏览器和已配置扩展工具，可直接调查、实现和验证低风险或常规任务；工具可用性不等于可绕过安全边界。
- 子代理是可选的低成本资源。仅在独立分析、并行处理或独立验证能显著提升效率或可信度时委派，且不得重复扫描同一问题。
- 目标明确、影响局限且可逆的低风险任务，可由 Leader 直接完成并做相称的自验证；不要求 Analyzer、固定确认口令、Tester 或 Reviewer。
- 常规任务由 Leader 自主选择直接处理或最小化委派，并选择与风险相称的验证深度。
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
3. 安装全局 Leader 与四个隐藏子代理到 `~/.copilot/agents`；
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

若 worker 模型不可用或结果不足，Leader 可自主直接完成任务；只有仍确需委派时才请用户指定替代模型。

## 使用

1. 重载 VS Code。
2. 在 Copilot Chat Agent 选择器中选择 `Leader`。
3. 输入开发任务；Leader 会按风险选择直接处理或委派。
4. 仅高风险任务需要确认；可使用：

```text
批准执行
```

这不是唯一有效的确认措辞，清晰的自然语言确认同样有效。VS Code Stable 当前没有受支持的配置可自动将自定义 Agent 设置为默认入口，因此首次及必要时需要手动选择 `Leader`。四个子代理通过 `user-invocable: false` 隐藏。

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

详见 [docs/NATIVE_LIMITATIONS.md](docs/NATIVE_LIMITATIONS.md)。

## 校验

```bash
python3 scripts/validate.py
python3 scripts/validate.py --installed
```

## 许可证

MIT
