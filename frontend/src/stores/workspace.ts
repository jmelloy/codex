import { defineStore } from "pinia";
import { ref } from "vue";
import {
  workspaceService,
  notebookService,
  fileService,
  folderService,
  type Workspace,
  type Notebook,
  type FileMetadata,
  type FileWithContent,
  type FolderMetadata,
  type FolderWithFiles,
} from "../services/codex";

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

  // Folder state
  const currentFolder = ref<FolderWithFiles | null>(null);
  const folderLoading = ref(false);

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
    }
    // Clear file and folder state when switching workspaces
    currentNotebook.value = null;
    currentFile.value = null;
    currentFolder.value = null;
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
    currentFolder.value = null; // Clear folder selection when selecting a file
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

  async function uploadFile(notebookId: number, file: File, path?: string) {
    if (!currentWorkspace.value) return;

    fileLoading.value = true;
    error.value = null;
    try {
      const newFile = await fileService.upload(
        notebookId,
        currentWorkspace.value.id,
        file,
        path,
      );
      // Refresh file list
      await fetchFiles(notebookId);
      return newFile;
    } catch (e: any) {
      error.value = e.response?.data?.detail || "Failed to upload file";
      throw e;
    } finally {
      fileLoading.value = false;
    }
  }

  async function moveFile(fileId: number, notebookId: number, newPath: string) {
    if (!currentWorkspace.value) return;

    fileLoading.value = true;
    error.value = null;
    try {
      const movedFile = await fileService.move(
        fileId,
        currentWorkspace.value.id,
        notebookId,
        newPath,
      );
      // Refresh file list
      await fetchFiles(notebookId);
      // Update current file if it was the one moved
      if (currentFile.value?.id === fileId) {
        currentFile.value = { ...currentFile.value, ...movedFile };
      }
      return movedFile;
    } catch (e: any) {
      error.value = e.response?.data?.detail || "Failed to move file";
      throw e;
    } finally {
      fileLoading.value = false;
    }
  }

  // Folder actions
  async function selectFolder(folderPath: string, notebookId: number) {
    if (!currentWorkspace.value) return;

    folderLoading.value = true;
    error.value = null;
    currentFile.value = null; // Clear current file when selecting folder
    isEditing.value = false;
    try {
      const folder = await folderService.get(
        folderPath,
        notebookId,
        currentWorkspace.value.id,
      );
      currentFolder.value = folder;
    } catch (e: any) {
      error.value = e.response?.data?.detail || "Failed to load folder";
    } finally {
      folderLoading.value = false;
    }
  }

  async function saveFolderProperties(properties: Record<string, any>) {
    if (!currentWorkspace.value || !currentFolder.value) return;

    folderLoading.value = true;
    error.value = null;
    try {
      const updated = await folderService.updateProperties(
        currentFolder.value.path,
        currentFolder.value.notebook_id,
        currentWorkspace.value.id,
        properties,
      );
      // Update currentFolder with new properties
      currentFolder.value = { ...currentFolder.value, ...updated };
      // Refresh file list for the notebook
      await fetchFiles(currentFolder.value.notebook_id);
    } catch (e: any) {
      error.value = e.response?.data?.detail || "Failed to save folder properties";
      throw e;
    } finally {
      folderLoading.value = false;
    }
  }

  async function deleteFolder() {
    if (!currentWorkspace.value || !currentFolder.value) return;

    folderLoading.value = true;
    error.value = null;
    try {
      await folderService.delete(
        currentFolder.value.path,
        currentFolder.value.notebook_id,
        currentWorkspace.value.id,
      );
      const notebookId = currentFolder.value.notebook_id;
      currentFolder.value = null;
      // Refresh file list
      await fetchFiles(notebookId);
    } catch (e: any) {
      error.value = e.response?.data?.detail || "Failed to delete folder";
      throw e;
    } finally {
      folderLoading.value = false;
    }
  }

  function clearFolderSelection() {
    currentFolder.value = null;
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
    // Folder state
    currentFolder,
    folderLoading,
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
    uploadFile,
    moveFile,
    toggleNotebookExpansion,
    setEditing,
    getFilesForNotebook,
    // Folder actions
    selectFolder,
    saveFolderProperties,
    deleteFolder,
    clearFolderSelection,
  };
});
