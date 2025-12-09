import { ref, computed } from "vue";
import { defineStore } from "pinia";
import type { Notebook } from "@/types";
import { notebooksApi } from "@/api";

export const useNotebooksStore = defineStore("notebooks", () => {
  const notebooks = ref<Map<string, Notebook>>(new Map());
  const loading = ref(false);
  const error = ref<string | null>(null);
  const workspacePath = ref<string>("/tmp/test_workspace");

  const notebooksList = computed(() => Array.from(notebooks.value.values()));

  async function loadNotebooks() {
    loading.value = true;
    error.value = null;

    try {
      const list = await notebooksApi.list(workspacePath.value);
      notebooks.value = new Map(list.map((nb) => [nb.id, nb]));
    } catch (e) {
      error.value = e instanceof Error ? e.message : "Failed to load notebooks";
    } finally {
      loading.value = false;
    }
  }

  async function loadNotebook(notebookId: string) {
    try {
      const notebook = await notebooksApi.get(workspacePath.value, notebookId);
      notebooks.value.set(notebook.id, notebook);
      return notebook;
    } catch (e) {
      error.value = e instanceof Error ? e.message : "Failed to load notebook";
      return null;
    }
  }

  async function createNotebook(
    title: string,
    description = "",
    tags: string[] = [],
  ) {
    try {
      const notebook = await notebooksApi.create(workspacePath.value, {
        title,
        description,
        tags,
      });
      notebooks.value.set(notebook.id, notebook);
      return notebook;
    } catch (e) {
      error.value =
        e instanceof Error ? e.message : "Failed to create notebook";
      return null;
    }
  }

  function setWorkspacePath(path: string) {
    workspacePath.value = path;
  }

  return {
    notebooks,
    notebooksList,
    loading,
    error,
    workspacePath,
    loadNotebooks,
    loadNotebook,
    createNotebook,
    setWorkspacePath,
  };
});
