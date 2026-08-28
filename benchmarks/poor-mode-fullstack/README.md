# 穷鬼模式全栈能力基准

这是一个用于横向比较低价编程模型的、可重复运行的前后端分离基准。候选模型拿到的是一套“基本能跑、公开 Smoke 测试能过、但关键边界有缺陷”的 Flask + Vue 项目。评测端保留隐藏测试、评分规则与过程记录，避免把答案和任务一起交给模型。

## 它测什么

- 后端：认证与资源归属、输入校验、HTTP 错误语义、分页边界、幂等创建、乐观并发控制、事务原子性。
- 前端：请求竞态、分页换算、`0` 值边界、时区、XSS、安全渲染、乐观更新回滚、重复提交、加载与错误状态。
- 跨端：API 契约是否一致、冲突和无权限是否被正确展示、刷新后是否保留正确状态。
- 工作方式：Worker 调用次数、工具动作数、返工轮数、墙钟时间、测试证据、范围违规与测试篡改。

## 目录隔离

```text
candidate/       唯一允许交给候选模型的原始任务包
evaluator/       隐藏测试、评分规则；不要放入候选模型工作区
tools/           准备运行、记录指标、评分、刷新排行榜
scoreboard/      可长期维护的模型成绩
selftests/       基准自身的测试
runs/            本地运行产物，默认不入库
```

“隐藏”是执行边界，不是密码学隔离。如果模型可以读取本仓库根目录，它仍可能找到评测器。正式测评必须用 `prepare` 生成独立工作区，并只向模型开放生成的 `workspace`。

## 一次完整测评

1. 准备候选工作区：

   ```bash
   python3 tools/benchmark.py prepare \
     --model "MiniMax-M3 (TokenPlan) (gcmp.minimax)" \
     --provider gcmp.minimax \
     --price-note "填写当次价格或套餐"
   ```

2. 命令会打印 `run_id` 和工作区路径。先在该工作区安装固定依赖（此阶段不计时），再启动计时：

   ```bash
   pnpm --dir 打印出的工作区/frontend install --frozen-lockfile
   python3 tools/benchmark.py start RUN_ID
   ```

   Python 依赖可安装到统一的干净测评环境。`pnpm-lock.yaml` 固定前端传递依赖；不要在不同模型之间更换包管理器。启动后，只把该工作区以及其中的 `TASK.md` 交给候选模型。不要把 `evaluator/`、`scoreboard/` 或本 README 放入它的上下文。

3. Leader 或外部观察者记录实际过程指标。候选结束后执行：

   ```bash
   python3 tools/benchmark.py record RUN_ID \
     --worker-calls 1 --tool-actions 18 --rework-rounds 0 \
     --input-tokens 120000 --output-tokens 18000 \
     --cost-amount 0.42 --cost-currency CNY \
     --claim "backend:pytest -q" \
     --claim "frontend:npm test -- --run"
   ```

4. 安装候选项目依赖后评分：

   ```bash
   python3 tools/benchmark.py evaluate RUN_ID
   python3 tools/benchmark.py leaderboard
   ```

   评测命令只读取运行工作区；前端隐藏测试通过环境变量导入候选代码，不会永久复制到候选目录。

## 公平比较规则

- 固定同一个基准版本、任务文本、初始仓库与运行环境。
- 一个模型一次直接、无状态调用。只有模型调用报错或无响应可按模式规则重试；功能失败、偷懒或质量差不是模型错误。
- 默认时间上限 45 分钟；默认最多 2 次 Worker 调用。第二次只允许在第一次为模型级错误时使用，或作为单独标注的“返工赛道”。
- `worker_calls` 指真正启动 Worker 的次数；`tool_actions` 指模型产生的读取、搜索、编辑、命令等工具动作总数；自然语言思考不计入。
- 不知道某项过程指标时留空。评分器会标记 `metrics_incomplete`，不会把未知当成 0。
- Token 和成本不是所有供应商都可观测，因此允许留空且不直接扣分；有遥测时必须记录真实值，不能按标价猜测。发生主模型 fallback 的运行标记为 `fallback_contaminated`，只留明细，不进入低价模型主榜。
- 任何修改公开测试、评测入口、依赖脚本来绕过测试，或硬编码已知测试输入的行为，均触发完整性处罚；严重时本次成绩无效。
- 每个模型至少跑 3 次，排行榜优先显示中位数，并保留每次原始成绩。单次成绩只适合初筛。

## 分数怎么读

总分 100：功能正确性 70、工程质量 10、效率 10、完整性与证据 10。另给出三个不计入总分但更适合选模型的派生指标：

- `reasoning_index`：困难行为点得分相对步数的效率，衡量“会不会想明白”。
- `diligence_index`：覆盖面、验证证据、未跳项和无越界的综合值。
- `slacking_index`：`100 - diligence_index`，越高越可能只修表面、跳过测试或用口头完成代替证据。

详细门槛与每一项分值见 [evaluator/STANDARD.md](evaluator/STANDARD.md)。排行榜字段见 [scoreboard/SCHEMA.md](scoreboard/SCHEMA.md)。

## 维护基准

新增坑位时必须同时更新：契约、至少一个隐藏行为测试、`rubric.json` 分值、基准版本和变更日志。不得只增加静态字符串检查；高价值项应尽量从外部观察行为。调整权重会改变历史可比性，应提升基准大版本或重算所有历史记录。
