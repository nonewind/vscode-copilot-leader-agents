export type TaskStatus = "todo" | "doing" | "done";

export interface Task {
  id: number;
  title: string;
  status: TaskStatus;
  estimate_hours: number | null;
  created_at: string;
  version: number;
}

export interface TaskPage {
  items: Task[];
  page: number;
  page_size: number;
  total: number;
}

export interface CreateTaskInput {
  title: string;
  estimate_hours: number;
}

