import { computed, reactive } from "vue";

import { ApiError, fetchTasks, patchTaskStatus, postTask } from "./api";
import type { CreateTaskInput, Task, TaskStatus } from "./types";

export interface TaskBoardDeps {
  fetchTasks: typeof fetchTasks;
  patchTaskStatus: typeof patchTaskStatus;
  postTask: typeof postTask;
  clearSession: () => void;
}

const defaultDeps: TaskBoardDeps = {
  fetchTasks,
  patchTaskStatus,
  postTask,
  clearSession: () => localStorage.removeItem("token"),
};

export function formatEstimate(value: number | null | undefined): string {
  return value ? `${value} h` : "未估算";
}

export function formatCreatedAt(value: string): string {
  return value.slice(0, 16).replace("T", " ");
}

export function errorMessage(error: unknown, clearSession: () => void): string {
  if (!(error instanceof ApiError)) return "网络错误";
  if (error.status === 401) {
    clearSession();
    return "登录已失效";
  }
  return error.message;
}

export function createTaskBoard(
  projectId: number,
  token: string,
  deps: TaskBoardDeps = defaultDeps,
) {
  const state = reactive({
    tasks: [] as Task[],
    page: 1,
    pageSize: 20,
    total: 0,
    query: "",
    loading: false,
    creating: false,
    error: "",
  });

  const totalPages = computed(() => Math.ceil(state.total / state.pageSize));

  async function load(): Promise<void> {
    state.loading = true;
    state.error = "";
    try {
      const result = await deps.fetchTasks(projectId, token, state.page, state.pageSize, state.query);
      state.tasks = result.items;
      state.total = result.total;
    } catch (error) {
      state.tasks = [];
      state.error = errorMessage(error, deps.clearSession);
    } finally {
      state.loading = false;
    }
  }

  async function changeStatus(task: Task, status: TaskStatus): Promise<void> {
    task.status = status;
    try {
      const updated = await deps.patchTaskStatus(task, status, token);
      Object.assign(task, updated);
    } catch (error) {
      state.error = errorMessage(error, deps.clearSession);
    }
  }

  async function create(input: CreateTaskInput): Promise<void> {
    state.creating = true;
    state.error = "";
    try {
      await deps.postTask(projectId, input, token);
      await load();
    } catch (error) {
      state.error = errorMessage(error, deps.clearSession);
    } finally {
      state.creating = false;
    }
  }

  return { state, totalPages, load, changeStatus, create };
}

