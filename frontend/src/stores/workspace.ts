import { defineStore } from "pinia";
import { ref } from "vue";
import {
  workspaceService,
  notebookService,
  type Workspace,
  type Notebook,
} from "../services/codex";

export const useWorkspaceStore = defineStore("workspace", () => {
  const workspaces = ref<Workspace[]>([]);
  const currentWorkspace = ref<Workspace | null>(null);
  const notebooks = ref<Notebook[]>([]);
  const loading = ref(false);
  const error = ref<string | null>(null);

  async function fetchWorkspaces() {
    loading.value = true;
    error.value = null;
    try {
      workspaces.value = await workspaceService.list();
    } catch (e: any) {
      error.value = e.response?.data?.detail || "Failed to fetch workspaces";
    } finally {
      loading.value = false;
    }
  }

  async function fetchNotebooks(workspaceId: number) {
    loading.value = true;
    error.value = null;
    try {
      notebooks.value = await notebookService.list(workspaceId);
    } catch (e: any) {
      error.value = e.response?.data?.detail || "Failed to fetch notebooks";
    } finally {
      loading.value = false;
    }
  }

  async function createWorkspace(name: string, path: string) {
    loading.value = true;
    error.value = null;
    try {
      const workspace = await workspaceService.create(name, path);
      workspaces.value.push(workspace);
      return workspace;
    } catch (e: any) {
      error.value = e.response?.data?.detail || "Failed to create workspace";
      throw e;
    } finally {
      loading.value = false;
    }
  }

  async function createNotebook(
    workspaceId: number,
    name: string,
    path: string
  ) {
    loading.value = true;
    error.value = null;
    try {
      const notebook = await notebookService.create(workspaceId, name, path);
      notebooks.value.push(notebook);
      return notebook;
    } catch (e: any) {
      error.value = e.response?.data?.detail || "Failed to create notebook";
      throw e;
    } finally {
      loading.value = false;
    }
  }

  function setCurrentWorkspace(workspace: Workspace | null) {
    currentWorkspace.value = workspace;
    if (workspace) {
      fetchNotebooks(workspace.id);
    }
  }

  return {
    workspaces,
    currentWorkspace,
    notebooks,
    loading,
    error,
    fetchWorkspaces,
    fetchNotebooks,
    createWorkspace,
    createNotebook,
    setCurrentWorkspace,
  };
});
