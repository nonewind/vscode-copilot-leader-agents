import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError, fetchTasks, postTask } from "@candidate/src/api";
import {
  createTaskBoard,
  errorMessage,
  formatCreatedAt,
  formatEstimate,
} from "@candidate/src/taskBoard";
import type { TaskBoardDeps } from "@candidate/src/taskBoard";
import type { Task } from "@candidate/src/types";

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

function task(overrides: Partial<Task> = {}): Task {
  return {
    id: 1,
    title: "Original",
    status: "todo",
    estimate_hours: 0,
    created_at: "2026-08-28T00:30:00Z",
    version: 1,
    ...overrides,
  };
}

function deps(overrides: Partial<TaskBoardDeps> = {}): TaskBoardDeps {
  return {
    fetchTasks: vi.fn().mockResolvedValue({ items: [], page: 1, page_size: 20, total: 0 }),
    patchTaskStatus: vi.fn(),
    postTask: vi.fn(),
    clearSession: vi.fn(),
    ...overrides,
  };
}

beforeEach(() => {
  vi.restoreAllMocks();
});

describe("hidden task board behavior", () => {
  it("[frontend.pagination] sends the one-based UI page unchanged", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ items: [], page: 2, page_size: 20, total: 0 }),
    });
    vi.stubGlobal("fetch", fetchMock);
    await fetchTasks(1, "token", 2, 20, "hello");
    const url = String(fetchMock.mock.calls[0][0]);
    expect(new URL(url, "http://local").searchParams.get("page")).toBe("2");
  });

  it("[frontend.boundaries] preserves zero and distinguishes missing estimates", () => {
    expect(formatEstimate(0)).toBe("0 h");
    expect(formatEstimate(null)).toBe("未估算");
    expect(formatEstimate(undefined)).toBe("未估算");
  });

  it("[frontend.timezone] converts UTC to the configured local timezone and handles invalid input", () => {
    expect(formatCreatedAt("2026-08-28T00:30:00Z")).toContain("08:30");
    expect(formatCreatedAt("not-a-date")).toBe("—");
  });

  it("[frontend.race] lets only the newest search response update data", async () => {
    const first = deferred<any>();
    const second = deferred<any>();
    const fake = deps({ fetchTasks: vi.fn().mockReturnValueOnce(first.promise).mockReturnValueOnce(second.promise) });
    const board = createTaskBoard(1, "token", fake);
    board.state.query = "old";
    const oldLoad = board.load();
    board.state.query = "new";
    const newLoad = board.load();
    second.resolve({ items: [task({ id: 2, title: "new" })], page: 1, page_size: 20, total: 1 });
    await newLoad;
    first.resolve({ items: [task({ id: 1, title: "old" })], page: 1, page_size: 20, total: 1 });
    await oldLoad;
    expect(board.state.tasks.map((item) => item.title)).toEqual(["new"]);
  });

  it("[frontend.loading] remains loading until the newest request settles", async () => {
    const first = deferred<any>();
    const second = deferred<any>();
    const fake = deps({ fetchTasks: vi.fn().mockReturnValueOnce(first.promise).mockReturnValueOnce(second.promise) });
    const board = createTaskBoard(1, "token", fake);
    const firstLoad = board.load();
    const secondLoad = board.load();
    first.resolve({ items: [], page: 1, page_size: 20, total: 0 });
    await firstLoad;
    expect(board.state.loading).toBe(true);
    second.resolve({ items: [], page: 1, page_size: 20, total: 0 });
    await secondLoad;
    expect(board.state.loading).toBe(false);
  });

  it("[frontend.preserve] preserves the last successful data after a load error", async () => {
    const fake = deps({
      fetchTasks: vi.fn()
        .mockResolvedValueOnce({ items: [task()], page: 1, page_size: 20, total: 1 })
        .mockRejectedValueOnce(new Error("offline")),
    });
    const board = createTaskBoard(1, "token", fake);
    await board.load();
    await board.load();
    expect(board.state.tasks).toHaveLength(1);
    expect(board.state.error).toBe("网络错误");
  });

  it("[frontend.rollback] rolls optimistic status back after a conflict", async () => {
    const pending = deferred<Task>();
    const fake = deps({ patchTaskStatus: vi.fn().mockReturnValue(pending.promise) });
    const board = createTaskBoard(1, "token", fake);
    const item = task();
    board.state.tasks = [item];
    const update = board.changeStatus(item, "done");
    expect(item.status).toBe("done");
    pending.reject(new ApiError(409, "version_conflict", "conflict"));
    await update;
    expect(item.status).toBe("todo");
    expect(board.state.error).toBe("数据已被其他人更新");
  });

  it("[frontend.duplicate_update] blocks a second update for the same task while pending", async () => {
    const pending = deferred<Task>();
    const patch = vi.fn().mockReturnValue(pending.promise);
    const board = createTaskBoard(1, "token", deps({ patchTaskStatus: patch }));
    const item = task();
    const first = board.changeStatus(item, "doing");
    const second = board.changeStatus(item, "done");
    expect(patch).toHaveBeenCalledTimes(1);
    pending.resolve(task({ status: "doing", version: 2 }));
    await Promise.all([first, second]);
  });

  it("[frontend.duplicate_create] blocks duplicate create calls while pending", async () => {
    const pending = deferred<Task>();
    const post = vi.fn().mockReturnValue(pending.promise);
    const board = createTaskBoard(1, "token", deps({ postTask: post }));
    const first = board.create({ title: "One", estimate_hours: 0 });
    const second = board.create({ title: "One", estimate_hours: 0 });
    expect(post).toHaveBeenCalledTimes(1);
    pending.resolve(task());
    await Promise.all([first, second]);
  });

  it("[frontend.idempotency] sends nonempty distinct keys for independent submissions", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => task() });
    vi.stubGlobal("fetch", fetchMock);
    await postTask(1, { title: "First", estimate_hours: 0 }, "token");
    await postTask(1, { title: "Second", estimate_hours: 0 }, "token");
    const firstHeaders = fetchMock.mock.calls[0][1].headers as Record<string, string>;
    const secondHeaders = fetchMock.mock.calls[1][1].headers as Record<string, string>;
    expect(firstHeaders["Idempotency-Key"]).toBeTruthy();
    expect(secondHeaders["Idempotency-Key"]).toBeTruthy();
    expect(firstHeaders["Idempotency-Key"]).not.toBe(secondHeaders["Idempotency-Key"]);
  });

  it("[frontend.errors] maps all contractual statuses and clears only an expired session", () => {
    const clear = vi.fn();
    expect(errorMessage(new ApiError(401, "unauthorized", "x"), clear)).toBe("登录已失效");
    expect(clear).toHaveBeenCalledTimes(1);
    expect(errorMessage(new ApiError(403, "forbidden", "x"), clear)).toBe("无权访问");
    expect(errorMessage(new ApiError(404, "not_found", "x"), clear)).toBe("资源不存在");
    expect(errorMessage(new ApiError(409, "version_conflict", "x"), clear)).toBe("数据已被其他人更新");
    expect(errorMessage(new ApiError(422, "validation_error", "具体校验错误"), clear)).toBe("具体校验错误");
    expect(clear).toHaveBeenCalledTimes(1);
  });
});
