# VS Code Copilot Leader Agents

这是一套仅依赖 VS Code Stable 与 GitHub Copilot Chat 原生能力的“穷鬼模式”：高能力 Leader 模型负责理解用户、提出关键问题、作出取舍、有限核验决定性事实、调度和验收；固定的低价 Worker 模型负责工作区调查、修改、测试和审查。

## 架构

```text
用户 <-> Leader（当前模型；agent、todo、有限 read/search）
          ├─ Analyzer：低价模型，只读调查
          ├─ Implementer：低价模型，受控修改和自验证
          ├─ Tester：低价模型，针对性验证
          └─ Reviewer：低价模型，差异和风险审查
```

Leader没有编辑、终端、VS Code操作、浏览器、GitHub或外部服务工具。日常工作区操作必须交给Worker；只有Worker证据冲突或不足、且某项源码事实会改变关键判断时，Leader才在完整用户上下文中有限使用`read/search`，证据足够后立即停止。

四个Worker默认固定为DeepSeek V4 Flash，对用户隐藏，且不能继续创建子代理。

## 意图与执行边界

修改前，Leader先明确用户真正想得到的可观察结果。只有答案会改变结果、范围或授权时，才提出一至三个具体问题；目标清楚、可逆的任务直接走快速通道，普通技术细节采用最小安全默认项。

每次委派只需一份自然语言任务简报：

- `GOAL`：要实现或查明的结果；
- `BOUNDARIES`：允许范围、必须保持的行为和非目标；
- `DONE`：什么直接证据足以停止；
- `STOP_AND_REPORT`：遇到哪些新取舍、扩大、风险或验证需求时必须返回Leader。

这四项是语义边界，不是固定表单或工作额度。简单任务保持简短；高风险任务再补充精确路径、禁止事项、验证层级和用户授权。Worker满足`DONE`后立即停止，相邻问题只报告，不顺手处理；需要扩大时统一返回`NEEDS_LEADER`，由高能力Leader判断下一步。

Leader可以把互不依赖、范围不重叠、结果可独立汇总且没有共享副作用的只读问题并发交给多个Analyzer。共享工作区的修改默认由一个Implementer串行完成；差异稳定后，Tester与Reviewer只有在命令不会争用缓存、生成物、数据或环境时才并发。并发只用于缩短关键路径，不增加调查总量，也不允许多个Worker重复扫描。

## 成本与风险工作流

- **无工具任务**：Leader直接完成对话、意图澄清、结果整合和验收。
- **只读分析**：Analyzer收集当前判断所需的直接事实；“先看看”不会自动升级为修改。
- **常规修改**：Implementer完成最小充分修改和最窄自验证。Tester、Reviewer只在能实质增加可信度时加入。
- **高风险任务**：删除、依赖或锁文件、配置或密钥、数据库或迁移、持久化数据写入、外部服务或部署、权限或安全边界、跨模块未知影响或难以回滚的变更，必须先说明计划和影响并取得明确确认；实施后必须由Tester和Reviewer独立通过。

验证按证据升级：先看直接行为和差异，再做目标测试或静态检查；只有共享影响、直接失败、明确契约风险或已确认计划要求时，才扩大到模块、完整构建或全量测试。低一级已经足以验收时必须停止。

Worker模型不可用或持续不足时，Leader停止并请用户指定替代模型或退出本模式，不得接管实施工具。任务需要四个Worker都没有的工具时同样退出本模式。

## 安装要求

- VS Code Stable 1.128+
- GitHub Copilot Chat已启用Agent
- Python 3.9+
- `code`命令已加入PATH
- GCMP插件；安装脚本会自动检测并安装

## 安装

macOS/Linux：

```bash
./install.sh
```

Windows PowerShell：

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\install.ps1
```

可显式指定Worker模型：

```bash
./install.sh --model "DeepSeek-V4-Flash (gcmp.deepseek)"
```

安装器会备份所有同名托管文件和被修改的VS Code设置。升级到0.4.0时，会先备份再清除旧版托管的Arbiter和四个已退役流程Skill。安装完成后重载VS Code并选择`Leader`。GCMP凭据由用户自行配置，本项目不会读取或保存。

## 原生限制

工具清单能硬性隔离Leader决策与Worker实施，Hook能拦截或确认已知危险操作；但意图对齐、语义边界、风险判断和Worker是否严格停止仍是提示词协议。VS Code原生能力无法把聊天确认绑定为持久授权令牌，也不能证明供应商实际模型和Credits行为。详见[docs/NATIVE_LIMITATIONS.md](docs/NATIVE_LIMITATIONS.md)。

## 校验

```bash
python3 scripts/validate.py
python3 scripts/validate.py --installed
python3 -m unittest discover -s tests -v
```

## 许可证

MIT
