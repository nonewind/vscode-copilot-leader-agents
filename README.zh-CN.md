# VS Code Copilot Leader Agents

当前仓库基线：[VERSION](VERSION)（尚未发布）。见[版本变更](CHANGELOG.md)和[穷鬼模式执行说明](docs/POOR_MODE.md)。源码修订不会自动更新已安装客户端。

这是一套支持 VS Code Copilot Chat、ZCode 与 Codex 的“穷鬼模式”：高能力 Leader 模型负责理解用户、提出关键问题、作出取舍、有限核验决定性事实、调度和验收；固定的低价 Worker 模型负责工作区调查、修改、测试和审查。

## 架构

```text
用户 <-> Leader（当前模型；默认 strict，可选 adaptive 快速通道）
          ├─ Analyzer：低价模型，只读调查
          ├─ Implementer：低价模型，受控修改和自验证
          ├─ Tester：低价模型，针对性验证
          └─ Reviewer：低价模型，差异和风险审查
```

默认 strict Leader 没有编辑和终端工具。可选 adaptive Leader 只增加 `edit` 与 `execute`，且必须在位置精确已知、单一可逆、无风险/契约类别、无需继续调查、无 Writer 冲突等全部条件成立时，先声明 `DIRECT:` 再执行一次；范围扩大立即移交 Implementer。两种模式都没有通用 VS Code 操作、浏览器、GitHub、todo 或外部写入工具，日常工作仍由 Worker 完成。

Leader默认固定子模型为`GLM-5.3-Flash (CodingPlan) (gcmp.zhipu)`，首次调用Analyzer、Implementer、Tester或Reviewer时显式指定；其 GCMP 目录模型 ID 是`glm-5.3-flash`，VS Code 选择器路由是`gcmp.zhipu:::glm-5.3-flash`。四个Worker自身不声明模型。子模型调用失败先分类再行动：瞬时失败（超时、无响应、限流，或未声明配置问题的`MODEL_UNAVAILABLE`）由Leader携带原简报和检查点重试一次同职责Worker；确定性拒绝（错误明确声明所请求的模型或推理档位不被支持）不得用同一配置重试——相同调用必然同样失败——直接调用同职责Worker但不指定子模型，使其继承当前Leader主模型并完成当前任务剩余范围。两次瞬时失败同样触发该不指定模型的主模型回退，且必须在回退调用前向用户说明。`FAIL`、`BLOCKED`、`NEEDS_LEADER`和结果质量不足属于任务证据，不触发模型重试；不自动发现第三个模型。Worker对用户隐藏，且不能继续创建子代理。

当前 VS Code 子代理调用没有暴露独立的思考深度参数；即使 GCMP 模型目录提供推理档位，也不能可靠设置`max`。Leader不得伪造`reasoningEffort`或宣称已启用最大档；复杂任务只能在简报里列出必须分析的具体问题、判断规则和证据要求，这属于提示约束，不是平台级推理配置。

## 意图与执行边界

修改前，Leader先明确用户真正想得到的可观察结果。只有答案会改变结果、范围或授权时，才提出一至三个具体问题；目标清楚、可逆的任务直接走快速通道，普通技术细节采用最小安全默认项。

GLM-5.3-Flash定位为低成本执行模型。Leader必须先完成意图理解、任务拆分和关键取舍，再交付一份Worker可以机械执行的自然语言任务简报：

- `GOAL`：一个确定、可观察的任务结果；
- `BOUNDARIES`：精确路径、符号或命令范围，当前已知事实、允许动作、必须保持的行为和非目标；
- `DONE`：逐项验收标准，以及什么文件差异、目标行为、命令或其他直接证据足以判定每项通过；
- `STOP_AND_REPORT`：遇到哪些新取舍、扩大、风险或验证需求时必须返回Leader。

这四项是语义边界，不是固定表单或工作额度。首次调用Worker前必须经过“任务拓扑门”：只有单一可观察结果、单一有界工作面、单条独立验收链同时成立时，才允许单Worker快速通道。复合任务必须拆成有依赖顺序的阶段波次和可独立验收的任务包；两个能够独立验收的任务包不得合并成一个巨大`GOAL`。每个波次应同时启动所有依赖已满足且能安全共存的任务包。选择串行时必须指出具体的数据依赖、契约所有权、文件重叠、生成物冲突或命令副作用，不能只说任务较长、属于同一目标或共享工作区。

修改任务还要给出直接问题证据、期望变化、允许改动的文件或符号，以及存在依赖时的执行顺序；不得用“相关文件”“合理处理”“视情况而定”“全面检查”等表述把范围或质量判断留给Worker。尚不知道精确修改位置时，Leader先让Analyzer回答一个有界事实问题。每个任务包是一次直接、无状态的Worker调用；`GOAL`只是普通文本字段，不是`goal`命令或持续任务。Leader没有`todo`工具，也不得通过memory、其他工具或文字模拟持续Worker生命周期、轮询或自动重调。后续调用只能是拓扑中预先声明且依赖已有直接结果的下一波任务包，或被新证据证明未满足某项`DONE`的针对性返工。Worker满足`DONE`后立即停止，相邻问题只报告，不顺手处理；需要扩大时统一返回`NEEDS_LEADER`，由高能力Leader判断下一步。

对项目外消费者可见的 TypeScript 导出、类型、签名等变化，Leader必须在`DONE`中写入`PUBLIC_TYPESCRIPT_API`：命名的隔离类型检查；公共导出变化还需项目外消费者编译夹具，含正例和`@ts-expect-error`负例。对会改变空白、缺失、空值、`0`、边界、无匹配或无数据结果的行为，Leader必须写入`BEHAVIOR_BOUNDARY`，列出已有契约支持的边界行和预期结果。触发项不是可接受的`NOT_VERIFIED`缺口：Tester必须验证，公共 TypeScript 契约还要由 Reviewer 做窄范围审查。

Leader把互不依赖、范围不重叠、结果可独立汇总且没有共享副作用的只读问题并发交给多个Analyzer。多个Implementer在精确文件所有权、公共契约、生成物和命令均不重叠时也应并发；发生冲突的任务包移到后续依赖波次，而不是重新合并给一个Worker。实施波次稳定后，Tester、Reviewer和其他独立验证包在命令不会争用缓存、生成物、数据或环境时并发。并发只用于缩短关键路径，不增加调查总量，也不允许多个Worker重复扫描。

## 成本与风险工作流

- **无工具任务**：Leader直接完成对话、意图澄清、结果整合和验收。
- **只读分析**：Analyzer收集当前判断所需的直接事实；“先看看”不会自动升级为修改。
- **常规修改**：Implementer完成最小充分修改和最窄自验证。Tester、Reviewer只在能实质增加可信度时加入。
- **高风险任务**：删除、依赖或锁文件、配置或密钥、数据库或迁移、持久化数据写入、外部服务或部署、权限或安全边界、跨模块未知影响或难以回滚的变更，必须先说明计划和影响并取得明确确认；实施后必须由Tester和Reviewer独立通过。

验证按证据升级：先看直接行为和差异，再做目标测试或静态检查；只有共享影响、直接失败、明确契约风险或已确认计划要求时，才扩大到模块、完整构建或全量测试。`PUBLIC_TYPESCRIPT_API`和`BEHAVIOR_BOUNDARY`把它们命名的窄验证变成明确契约风险，但不因此默认跑全量测试。Leader拥有验证深度和最终验收的判断权；默认在直接证据足以支持`DONE`时停止，继续验证必须有新的具体证据直接威胁某项`DONE`。`NOT_VERIFIED`、理论风险、建议扩大验证或附带发现只记录为缺口，不自动生成下一道门禁。同一任务最多一轮针对性返工和一次直接复核，之后必须验收或报告未完成项与剩余风险。

主模型回退只覆盖当前任务，保留原`GOAL`、边界、已确认授权和`DONE`；不会让Leader取得实施工具，也不成为后续任务的默认模型。原生VS Code无法证明未固定模型的子代理实际继承了当前主模型，因此此路径仍需真实VS Code Smoke验证。任务需要四个Worker都没有的工具时同样退出本模式。

## 安装要求

- VS Code Stable 1.128+
- GitHub Copilot Chat已启用Agent
- Python 3.9+
- `code`命令已加入PATH
- GCMP插件，且智谱目录必须包含`gcmp.zhipu:::glm-5.3-flash`

## 安装

### VS Code Copilot

macOS/Linux：

```bash
./install.sh
```

Windows PowerShell：

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\install.ps1
```

只有用户选择替代Worker模型时才显式覆盖默认值：

```bash
./install.sh --model "用户选择的精确模型ID"
```

显式选择 adaptive Leader：

```bash
./install.sh --leader adaptive
```

```powershell
.\install.ps1 -Leader adaptive
```

不传 `--leader` 时保留已安装的合法选择；新安装或旧版升级默认 strict。

安装器会备份所有同名托管文件和被修改的VS Code设置。升级到0.4.0时，会先备份再清除旧版托管的Arbiter和四个已退役流程Skill。安装完成后重载VS Code并选择`Leader`。GCMP凭据由用户自行配置，本项目不会读取或保存。

若已经安装 GCMP，而模型选择器中没有默认模型，请先执行`./install.sh --update-extension`再安装。

### ZCode

ZCode 原生 Plugin、marketplace、四个 Worker、Hook 与主 Agent 指令位于 `zcode/`。strict 模式拒绝主 Agent 的编辑、命令和 MCP 调用；`python3 scripts/install_zcode.py --project /path/to/project --mode adaptive` 会继续拒绝 MCP，并在更强安全规则之后把普通直做编辑/命令降为逐次确认。ZCode 0.8.0 不提供模型回退；敏感路径确认在未激活 Leader 块时也生效，这是有意的跨平台安全统一。详见 [docs/ZCODE.md](docs/ZCODE.md)。

### Codex

Codex 项目级版本位于 `codex/`：四个基础 Worker 固定为 `gpt-5.6-luna` 并按角色分级；四个可选 fallback 角色同时省略模型和档位，用于继承父线程。先预览，再安装：

```bash
python3 scripts/install_codex.py --project /path/to/project --dry-run
python3 scripts/install_codex.py --project /path/to/project
python3 scripts/install_codex.py --project /path/to/project --mode adaptive
python3 scripts/install_codex.py --project /path/to/project --fallback parent-worker
```

新安装默认 strict + stop。旧版写入的精确项目级模型/档位默认值必须通过 `--migrate-agent-defaults` 显式迁移；自定义值会保留，并阻止不真实的父模型回退。各 agent 的 sandbox 只是默认值，父线程实时权限可以收紧或放宽，不能称为硬隔离。完整迁移矩阵与双向 Smoke 见 [docs/CODEX.md](docs/CODEX.md)。

## 原生限制

strict 工具清单能隔离 Leader 决策与 Worker 实施；adaptive 的一次动作限制有意由协议约束。Hook 可拦截或确认已知危险操作，但真实触达范围、模型继承和 Credits 行为仍需运行时证据。详见[docs/NATIVE_LIMITATIONS.md](docs/NATIVE_LIMITATIONS.md)。

## 校验

```bash
python3 scripts/validate.py
python3 scripts/validate.py --installed
python3 -m unittest discover -s tests -v
```

## 许可证

MIT
