import { describe, expect, it, vi } from "vitest";

import { createTaskBoard, formatEstimate } from "../src/taskBoard";
import type { TaskBoardDeps } from "../src/taskBoard";

describe("task board smoke", () => {
  it("formats a positive estimate", () => {
    expect(formatEstimate(2)).toBe("2 h");
  });

  it("loads a page", async () => {
    const deps: TaskBoardDeps = {
      fetchTasks: vi.fn().mockResolvedValue({ items: [], page: 1, page_size: 20, total: 0 }),
      patchTaskStatus: vi.fn(),
      postTask: vi.fn(),
      clearSession: vi.fn(),
    };
    const board = createTaskBoard(1, "token", deps);
    await board.load();
    expect(deps.fetchTasks).toHaveBeenCalled();
    expect(board.state.loading).toBe(false);
  });
});
