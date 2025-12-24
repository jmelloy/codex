import { defineStore } from "pinia";
import { ref } from "vue";
import { taskService, type Task } from "../services/codex";

export const useTaskStore = defineStore("tasks", () => {
  const tasks = ref<Task[]>([]);
  const loading = ref(false);
  const error = ref<string | null>(null);

  async function fetchTasks(workspaceId: number) {
    loading.value = true;
    error.value = null;
    try {
      tasks.value = await taskService.list(workspaceId);
    } catch (e: any) {
      error.value = e.response?.data?.detail || "Failed to fetch tasks";
      throw e;
    } finally {
      loading.value = false;
    }
  }

  async function createTask(
    workspaceId: number,
    title: string,
    description?: string
  ) {
    loading.value = true;
    error.value = null;
    try {
      const task = await taskService.create(workspaceId, title, description);
      tasks.value.push(task);
      return task;
    } catch (e: any) {
      error.value = e.response?.data?.detail || "Failed to create task";
      throw e;
    } finally {
      loading.value = false;
    }
  }

  async function updateTaskStatus(id: number, status: string) {
    loading.value = true;
    error.value = null;
    try {
      const updatedTask = await taskService.update(id, status);
      const index = tasks.value.findIndex((t) => t.id === id);
      if (index !== -1) {
        tasks.value[index] = updatedTask;
      }
      return updatedTask;
    } catch (e: any) {
      error.value = e.response?.data?.detail || "Failed to update task";
      throw e;
    } finally {
      loading.value = false;
    }
  }

  return {
    tasks,
    loading,
    error,
    fetchTasks,
    createTask,
    updateTaskStatus,
  };
});
