# VS Code Copilot Leader Agents

这是一套仅依赖 VS Code Stable 与 GitHub Copilot Chat 原生能力的“穷鬼模式”：高能力 Leader 模型负责理解用户、提出关键问题、作出取舍、有限核验决定性事实、调度和验收；固定的低价 Worker 模型负责工作区调查、修改、测试和审查。

## 架构

```text
用户 <-> Leader（当前模型；agent、有限 read/search/web）
          ├─ Analyzer：低价模型，只读调查
          ├─ Implementer：低价模型，受控修改和自验证
          ├─ Tester：低价模型，针对性验证
          └─ Reviewer：低价模型，差异和风险审查
```

Leader没有编辑、终端、通用VS Code操作、浏览器、GitHub、todo或外部写入工具。日常工作区操作必须交给Worker；只有Worker证据冲突或不足、且某项源码事实会改变关键判断时，Leader才有限使用`read/search`。唯一的`web`工具只用于工作区无法提供的一个有界公开事实或权威文档，不得登录、外部写入或传出工作区内容与凭据；`vscode/askQuestions`只用于会改变结果、边界或授权的用户决策；`vscode/memory`只保存用户明确要求记住的稳定偏好或可复用项目事实，不保存任务状态，也不触发工作。

Leader默认固定子模型为`GLM-5.3-Flash (CodingPlan) (gcmp.zhipu)`，首次调用Analyzer、Implementer、Tester或Reviewer时显式指定；其 GCMP 目录模型 ID 是`glm-5.3-flash`，VS Code 选择器路由是`gcmp.zhipu:::glm-5.3-flash`。四个Worker自身不声明模型。子模型调用报错、无响应或返回`MODEL_UNAVAILABLE`时，Leader携带原简报和检查点重试一次同职责Worker；两次均因该模型错误失败时，调用同职责Worker但不指定子模型，使其继承当前Leader主模型并完成当前任务剩余范围。`FAIL`、`BLOCKED`、`NEEDS_LEADER`和结果质量不足属于任务证据，不触发模型重试；不自动发现第三个模型。Worker对用户隐藏，且不能继续创建子代理。

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

安装器会备份所有同名托管文件和被修改的VS Code设置。升级到0.4.0时，会先备份再清除旧版托管的Arbiter和四个已退役流程Skill。安装完成后重载VS Code并选择`Leader`。GCMP凭据由用户自行配置，本项目不会读取或保存。

若已经安装 GCMP，而模型选择器中没有默认模型，请先执行`./install.sh --update-extension`再安装。

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
