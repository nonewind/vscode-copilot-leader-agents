<script setup lang="ts">
import { onMounted, ref } from "vue";

import { createTaskBoard, formatCreatedAt, formatEstimate } from "./taskBoard";
import type { TaskStatus } from "./types";

const board = createTaskBoard(1, localStorage.getItem("token") ?? "token-alice");
const title = ref("");
const estimate = ref(0);

function search() {
  board.state.page = 1;
  void board.load();
}

function submit() {
  void board.create({ title: title.value, estimate_hours: estimate.value });
}

function updateStatus(id: number, event: Event) {
  const task = board.state.tasks.find((item) => item.id === id);
  if (task) void board.changeStatus(task, (event.target as HTMLSelectElement).value as TaskStatus);
}

onMounted(board.load);
</script>

<template>
  <main>
    <h1>任务看板</h1>

    <form class="toolbar" @submit.prevent="search">
      <input v-model="board.state.query" aria-label="搜索标题" />
      <button>搜索</button>
    </form>

    <p v-if="board.state.loading">加载中…</p>
    <p v-if="board.state.error" role="alert">{{ board.state.error }}</p>
    <ul>
      <li v-for="(task, index) in board.state.tasks" :key="index">
        <strong class="task-title" v-html="task.title" />
        <span>{{ formatEstimate(task.estimate_hours) }}</span>
        <time>{{ formatCreatedAt(task.created_at) }}</time>
        <select :value="task.status" @change="updateStatus(task.id, $event)">
          <option value="todo">待办</option>
          <option value="doing">进行中</option>
          <option value="done">完成</option>
        </select>
      </li>
    </ul>
    <p v-if="!board.state.loading && board.state.tasks.length === 0">0 条任务</p>

    <nav aria-label="分页">
      <button :disabled="board.state.page <= 1" @click="board.state.page--; board.load()">上一页</button>
      <span>第 {{ board.state.page }} / {{ board.totalPages }} 页</span>
      <button :disabled="board.state.page >= board.totalPages" @click="board.state.page++; board.load()">下一页</button>
    </nav>

    <form class="create" @submit.prevent="submit">
      <input v-model="title" aria-label="任务标题" />
      <input v-model.number="estimate" type="number" min="0" max="100" aria-label="预估小时" />
      <button>新建</button>
    </form>
  </main>
</template>

<style scoped>
main { max-width: 760px; margin: 2rem auto; font-family: system-ui, sans-serif; }
.toolbar, .create, li, nav { display: flex; gap: .75rem; margin: 1rem 0; align-items: center; }
li { justify-content: space-between; }
.task-title { flex: 1; }
[role="alert"] { color: #b42318; }
</style>

