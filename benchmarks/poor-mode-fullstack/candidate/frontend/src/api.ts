import type { CreateTaskInput, Task, TaskPage, TaskStatus } from "./types";

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
    message: string,
  ) {
    super(message);
  }
}

async function request<T>(path: string, token: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
      ...init?.headers,
    },
  });
  const body = await response.json();
  if (!response.ok) {
    throw new ApiError(response.status, body?.error?.code ?? "unknown", body?.error?.message ?? "请求失败");
  }
  return body as T;
}

export function fetchTasks(
  projectId: number,
  token: string,
  page: number,
  pageSize: number,
  query: string,
): Promise<TaskPage> {
  const params = new URLSearchParams({
    page: String(page - 1),
    page_size: String(pageSize),
    q: query,
  });
  return request(`/api/projects/${projectId}/tasks?${params}`, token);
}

export function patchTaskStatus(
  task: Task,
  status: TaskStatus,
  token: string,
): Promise<Task> {
  return request(`/api/tasks/${task.id}`, token, {
    method: "PATCH",
    body: JSON.stringify({ status, version: task.version }),
  });
}

export function postTask(
  projectId: number,
  input: CreateTaskInput,
  token: string,
): Promise<Task> {
  return request(`/api/projects/${projectId}/tasks`, token, {
    method: "POST",
    headers: { "Idempotency-Key": crypto.randomUUID() },
    body: JSON.stringify(input),
  });
}

