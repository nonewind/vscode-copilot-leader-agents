# 任务看板行为契约

## 通用

- 所有 `/api/**` 请求使用 `Authorization: Bearer <token>`；缺失或无效 token 返回 401。
- JSON 错误体为 `{ "error": { "code": string, "message": string } }`，不得以 2xx 表示失败。
- Alice 只能访问 Alice 所属项目 1；Bob 只能访问 Bob 所属项目 2。已认证但无权访问返回 403；资源在其可见范围内不存在时返回 404。
- 日期时间在 API 中均为带 `Z` 的 UTC ISO-8601；界面按浏览器本地时区显示。

## `GET /api/projects/:projectId/tasks`

- 查询参数：`page` 默认为 1，最小 1；`page_size` 默认为 20，范围 1..50；非法值返回 422。
- `q` 是大小写不敏感的标题子串；空字符串等于不筛选。
- 稳定排序：`created_at DESC, id DESC`。
- 返回 `{ items, page, page_size, total }`；超出末页返回空 `items`，`total` 不变。
- 每项包含 `id,title,status,estimate_hours,created_at,version`。`estimate_hours: 0` 必须保留为 0。

## `POST /api/projects/:projectId/tasks`

- 请求体：`title` 为去除首尾空格后的 1..80 字符；`estimate_hours` 为整数 0..100；非法或缺失字段返回 422。
- 必须带非空 `Idempotency-Key`。同一用户、同一项目、同一 key、相同请求体重复提交，返回第一次的任务且不重复创建；首次为 201，重放为 200。
- 同一 key 配不同请求体返回 409；不同用户或项目可以复用相同 key。
- 创建任务与审计记录属于同一事务。审计写入失败时返回 500，任务和幂等记录都不得残留。

## `PATCH /api/tasks/:taskId`

- 请求体至少包含一个可修改字段：`title` 或 `status`，另须包含整数 `version`；未知字段返回 422。
- `status` 只能是 `todo|doing|done`。标题规则同创建接口。
- 仅当请求 version 等于当前 version 才更新；成功返回 200 且 version 加 1。陈旧 version 返回 409，且不得改变任何字段。

## 前端看板

- 首次进入和筛选/翻页时显示加载状态；失败显示错误且保留上一次成功数据。
- 快速连续搜索时，只允许最后一次请求更新界面；旧请求晚返回不得覆盖新结果。
- UI 页码为 1 起，发送给后端也必须为 1 起。无结果时显示 0 条，不出现第 0 页或负页码。
- `estimate_hours` 的 0 显示为 `0 h`，只有 `null/undefined` 显示 `未估算`。
- UTC 时间按浏览器本地时区格式化；无效时间显示 `—`。
- 标题按纯文本渲染，即使内容包含 HTML；列表使用任务 ID 作为稳定 key。
- 状态更新采用乐观 UI；409 或网络失败必须恢复原值并显示错误。更新进行中禁止对同一任务重复提交。
- 新建按钮在请求进行中禁用。幂等 key 在一次用户提交的所有网络重试中保持一致；下一次独立提交使用新 key。
- 401 清理本地会话并显示“登录已失效”；403 显示“无权访问”；404 显示“资源不存在”；409 显示“数据已被其他人更新”；422 显示服务端校验消息。

