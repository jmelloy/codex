import { defineStore } from "pinia";
import { ref } from "vue";
import {
  workspaceService,
  notebookService,
  fileService,
  type Workspace,
  type Notebook,
  type FileMetadata,
  type FileWithContent,
} from "../services/codex";
import { useThemeStore } from "./theme";

export const useWorkspaceStore = defineStore("workspace", () => {
  const workspaces = ref<Workspace[]>([]);
  const currentWorkspace = ref<Workspace | null>(null);
  const notebooks = ref<Notebook[]>([]);
  const loading = ref(false);
  const error = ref<string | null>(null);

  // File state
  const files = ref<Map<number, FileMetadata[]>>(new Map()); // notebook_id -> files
  const currentNotebook = ref<Notebook | null>(null);
  const currentFile = ref<FileWithContent | null>(null);
  const isEditing = ref(false);
  const expandedNotebooks = ref<Set<number>>(new Set());
  const fileLoading = ref(false);

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

  async function createWorkspace(name: string) {
    loading.value = true;
    error.value = null;
    try {
      const workspace = await workspaceService.create(name);
      workspaces.value.push(workspace);
      return workspace;
    } catch (e: any) {
      error.value = e.response?.data?.detail || "Failed to create workspace";
      throw e;
    } finally {
      loading.value = false;
    }
  }

  async function createNotebook(workspaceId: number, name: string) {
    loading.value = true;
    error.value = null;
    try {
      const notebook = await notebookService.create(workspaceId, name);
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
      // Load theme from workspace
      const themeStore = useThemeStore();
      themeStore.loadFromWorkspace(workspace.id, workspace.theme_setting);
    }
    // Clear file state when switching workspaces
    currentNotebook.value = null;
    currentFile.value = null;
    isEditing.value = false;
    files.value.clear();
    expandedNotebooks.value.clear();
  }

  // File actions
  async function fetchFiles(notebookId: number) {
    if (!currentWorkspace.value) return;

    fileLoading.value = true;
    error.value = null;
    try {
      const fileList = await fileService.list(
        notebookId,
        currentWorkspace.value.id,
      );
      files.value.set(notebookId, fileList);
    } catch (e: any) {
      error.value = e.response?.data?.detail || "Failed to fetch files";
    } finally {
      fileLoading.value = false;
    }
  }

  async function selectFile(file: FileMetadata) {
    if (!currentWorkspace.value) return;

    fileLoading.value = true;
    error.value = null;
    try {
      const fileWithContent = await fileService.get(
        file.id,
        currentWorkspace.value.id,
        file.notebook_id,
      );
      currentFile.value = fileWithContent;
      isEditing.value = false;
    } catch (e: any) {
      error.value = e.response?.data?.detail || "Failed to load file";
    } finally {
      fileLoading.value = false;
    }
  }

  async function saveFile(content: string, properties?: Record<string, any>) {
    if (!currentWorkspace.value || !currentFile.value) return;

    fileLoading.value = true;
    error.value = null;
    try {
      if (!currentFile.value.notebook_id) {
        throw new Error("File has no notebook_id");
      }
      const updated = await fileService.update(
        currentFile.value.id,
        currentWorkspace.value.id,
        currentFile.value.notebook_id,
        content,
        properties,
      );
      // Update currentFile with new content and properties
      currentFile.value = { ...currentFile.value, ...updated, content };
      isEditing.value = false;

      // Refresh file list for the notebook
      await fetchFiles(currentFile.value.notebook_id);
    } catch (e: any) {
      error.value = e.response?.data?.detail || "Failed to save file";
      throw e;
    } finally {
      fileLoading.value = false;
    }
  }

  async function createFile(notebookId: number, path: string, content: string) {
    if (!currentWorkspace.value) return;

    fileLoading.value = true;
    error.value = null;
    try {
      const newFile = await fileService.create(
        notebookId,
        currentWorkspace.value.id,
        path,
        content,
      );
      // Refresh file list
      await fetchFiles(notebookId);
      // Select the new file
      await selectFile(newFile);
      return newFile;
    } catch (e: any) {
      error.value = e.response?.data?.detail || "Failed to create file";
      throw e;
    } finally {
      fileLoading.value = false;
    }
  }

  async function deleteFile(fileId: number) {
    if (!currentWorkspace.value || !currentFile.value) return;

    fileLoading.value = true;
    error.value = null;
    try {
      await fileService.delete(fileId, currentWorkspace.value.id);
      const notebookId = currentFile.value.notebook_id;
      currentFile.value = null;
      isEditing.value = false;
      // Refresh file list
      if (notebookId) {
        await fetchFiles(notebookId);
      }
    } catch (e: any) {
      error.value = e.response?.data?.detail || "Failed to delete file";
      throw e;
    } finally {
      fileLoading.value = false;
    }
  }

  function toggleNotebookExpansion(notebook: Notebook) {
    const notebookId = notebook.id;
    if (expandedNotebooks.value.has(notebookId)) {
      expandedNotebooks.value.delete(notebookId);
    } else {
      expandedNotebooks.value.add(notebookId);
      // Fetch files when expanding
      fetchFiles(notebookId);
    }
    currentNotebook.value = notebook;
  }

  function setEditing(editing: boolean) {
    isEditing.value = editing;
  }

  function getFilesForNotebook(notebookId: number): FileMetadata[] {
    return files.value.get(notebookId) || [];
  }

  return {
    // Workspace state
    workspaces,
    currentWorkspace,
    notebooks,
    loading,
    error,
    // File state
    files,
    currentNotebook,
    currentFile,
    isEditing,
    expandedNotebooks,
    fileLoading,
    // Workspace actions
    fetchWorkspaces,
    fetchNotebooks,
    createWorkspace,
    createNotebook,
    setCurrentWorkspace,
    // File actions
    fetchFiles,
    selectFile,
    saveFile,
    createFile,
    deleteFile,
    toggleNotebookExpansion,
    setEditing,
    getFilesForNotebook,
  };
});
