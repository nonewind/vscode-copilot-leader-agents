# 成绩表字段

`runs.csv` 每行是一轮，不覆盖历史：

- 身份：`run_id, benchmark_version, model, provider, price_note, context_window`。
- 成本遥测：`input_tokens, output_tokens, cost_amount, cost_currency, score_per_cost_unit`；不可观测时留空。
- 环境：`started_at, finished_at, duration_minutes`。
- 过程：`worker_calls, tool_actions, rework_rounds, fallback_used`。
- 分数：`correctness, engineering, efficiency, integrity, total, grade`。
- 派生：`reasoning_index, diligence_index, slacking_index`。
- 质量：`status, metrics_complete, protected_changed, review_note`。`fallback_contaminated` 不进入主榜。

`leaderboard.csv` 由工具从有效运行生成，同一精确模型/供应商/基准版本聚合为 `runs, median, min, max, completion_rate`。不要手工编辑生成榜；修正原始运行记录后重新生成。
