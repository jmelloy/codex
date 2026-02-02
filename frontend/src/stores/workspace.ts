import { defineStore } from "pinia"
import { ref, computed } from "vue"
import {
  workspaceService,
  notebookService,
  fileService,
  folderService,
  type Workspace,
  type Notebook,
  type FileMetadata,
  type FileWithContent,
  type FolderWithFiles,
} from "../services/codex"
import {
  type FileTreeNode,
  buildFileTree,
  insertFileNode,
  removeNode,
  updateFileNode,
  mergeFolderContents,
  getAllFiles,
  findNode,
  moveNode,
} from "../utils/fileTree"

export const useWorkspaceStore = defineStore("workspace", () => {
  const workspaces = ref<Workspace[]>([])
  const currentWorkspace = ref<Workspace | null>(null)
  const notebooks = ref<Notebook[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  // File state - now using tree structure
  const fileTrees = ref<Map<number, FileTreeNode[]>>(new Map()) // notebook_id -> file tree
  const currentNotebook = ref<Notebook | null>(null)
  const currentFile = ref<FileWithContent | null>(null)
  const isEditing = ref(false)
  const expandedNotebooks = ref<Set<number>>(new Set())
  const fileLoading = ref(false)

  // Folder state
  const currentFolder = ref<FolderWithFiles | null>(null)
  const folderLoading = ref(false)

  // Backwards-compatible files accessor (returns flat list from tree)
  const files = computed(() => {
    const flatMap = new Map<number, FileMetadata[]>()
    for (const [notebookId, tree] of fileTrees.value) {
      flatMap.set(notebookId, getAllFiles(tree))
    }
    return flatMap
  })

  // Helper function to get notebook slug by ID
  function getNotebookSlug(notebookId: number): string {
    const notebook = notebooks.value.find((nb) => nb.id === notebookId)
    return notebook?.slug || notebook?.path || ""
  }

  // Helper function to get workspace slug
  function getWorkspaceSlug(): string {
    return currentWorkspace.value?.slug || ""
  }

  async function fetchWorkspaces() {
    loading.value = true
    error.value = null
    try {
      workspaces.value = await workspaceService.list()
    } catch (e: any) {
      error.value = e.response?.data?.detail || "Failed to fetch workspaces"
    } finally {
      loading.value = false
    }
  }

  async function fetchNotebooks(workspaceSlugOrId: string | number) {
    loading.value = true
    error.value = null
    try {
      // Support both slug (string) and legacy ID (number)
      let slug: string
      if (typeof workspaceSlugOrId === "number") {
        // Find workspace by ID to get its slug
        const workspace = workspaces.value.find((ws) => ws.id === workspaceSlugOrId)
        slug = workspace?.slug || ""
      } else {
        slug = workspaceSlugOrId
      }
      notebooks.value = await notebookService.list(slug)
    } catch (e: any) {
      error.value = e.response?.data?.detail || "Failed to fetch notebooks"
    } finally {
      loading.value = false
    }
  }

  async function createWorkspace(name: string) {
    loading.value = true
    error.value = null
    try {
      const workspace = await workspaceService.create(name)
      workspaces.value.push(workspace)
      return workspace
    } catch (e: any) {
      error.value = e.response?.data?.detail || "Failed to create workspace"
      throw e
    } finally {
      loading.value = false
    }
  }

  async function createNotebook(workspaceSlugOrId: string | number, name: string) {
    loading.value = true
    error.value = null
    try {
      // Support both slug (string) and legacy ID (number)
      let slug: string
      if (typeof workspaceSlugOrId === "number") {
        const workspace = workspaces.value.find((ws) => ws.id === workspaceSlugOrId)
        slug = workspace?.slug || ""
      } else {
        slug = workspaceSlugOrId
      }
      const notebook = await notebookService.create(slug, name)
      notebooks.value.push(notebook)
      return notebook
    } catch (e: any) {
      error.value = e.response?.data?.detail || "Failed to create notebook"
      throw e
    } finally {
      loading.value = false
    }
  }

  function setCurrentWorkspace(workspace: Workspace | null) {
    currentWorkspace.value = workspace
    if (workspace) {
      fetchNotebooks(workspace.slug)
    }
    // Clear file and folder state when switching workspaces
    currentNotebook.value = null
    currentFile.value = null
    currentFolder.value = null
    isEditing.value = false
    fileTrees.value.clear()
    expandedNotebooks.value.clear()
  }

  // File actions

  /**
   * Fetch all files for a notebook and build the file tree.
   * This loads the complete file list and builds a tree structure.
   */
  async function fetchFiles(notebookId: number) {
    if (!currentWorkspace.value) return

    fileLoading.value = true
    error.value = null
    try {
      const workspaceSlug = getWorkspaceSlug()
      const notebookSlug = getNotebookSlug(notebookId)
      const fileList = await fileService.list(workspaceSlug, notebookSlug)
      // Build tree from flat file list
      const tree = buildFileTree(fileList)
      fileTrees.value.set(notebookId, tree)
    } catch (e: any) {
      error.value = e.response?.data?.detail || "Failed to fetch files"
    } finally {
      fileLoading.value = false
    }
  }

  /**
   * Fetch folder contents and merge them into the existing tree.
   * This allows incremental loading of folder contents on demand.
   */
  async function fetchFolderContents(
    folderPath: string,
    notebookId: number,
  ): Promise<FolderWithFiles | null> {
    if (!currentWorkspace.value) return null

    folderLoading.value = true
    error.value = null
    try {
      const workspaceSlug = getWorkspaceSlug()
      const notebookSlug = getNotebookSlug(notebookId)
      const folder = await folderService.get(workspaceSlug, notebookSlug, folderPath)

      // Get or create the tree for this notebook
      if (!fileTrees.value.has(notebookId)) {
        fileTrees.value.set(notebookId, [])
      }
      const tree = fileTrees.value.get(notebookId)!

      // Merge folder contents into the tree
      mergeFolderContents(tree, folderPath, folder)

      return folder
    } catch (e: any) {
      error.value = e.response?.data?.detail || "Failed to load folder"
      return null
    } finally {
      folderLoading.value = false
    }
  }

  async function selectFile(file: FileMetadata) {
    if (!currentWorkspace.value) return

    fileLoading.value = true
    error.value = null
    currentFolder.value = null // Clear folder selection when selecting a file
    try {
      const workspaceSlug = getWorkspaceSlug()
      const notebookSlug = getNotebookSlug(file.notebook_id)

      // First fetch file metadata (fast, no content)
      const fileMeta = await fileService.get(workspaceSlug, notebookSlug, file.path)

      // Set file with empty content initially so UI can render metadata immediately
      currentFile.value = { ...fileMeta, content: "" }
      isEditing.value = false

      // Then fetch content for text-based files
      const isTextFile =
        fileMeta.content_type.startsWith("text/") ||
        ["application/json", "application/xml", "application/x-codex-view"].includes(
          fileMeta.content_type,
        )

      if (isTextFile) {
        const textContent = await fileService.getContent(workspaceSlug, notebookSlug, file.path)
        // Update with content and any refreshed properties
        currentFile.value = {
          ...fileMeta,
          content: textContent.content,
          properties: textContent.properties ?? fileMeta.properties,
        }
      }
    } catch (e: any) {
      error.value = e.response?.data?.detail || "Failed to load file"
    } finally {
      fileLoading.value = false
    }
  }

  async function saveFile(content: string, properties?: Record<string, any>) {
    if (!currentWorkspace.value || !currentFile.value) return

    fileLoading.value = true
    error.value = null
    try {
      if (!currentFile.value.notebook_id) {
        throw new Error("File has no notebook_id")
      }
      const workspaceSlug = getWorkspaceSlug()
      const notebookSlug = getNotebookSlug(currentFile.value.notebook_id)

      const updated = await fileService.update(
        workspaceSlug,
        notebookSlug,
        currentFile.value.path,
        content,
        properties,
      )
      // Update currentFile with new content and properties
      currentFile.value = { ...currentFile.value, ...updated, content }
      isEditing.value = false

      // Update the file node in the tree (incremental update)
      const tree = fileTrees.value.get(currentFile.value.notebook_id)
      if (tree) {
        updateFileNode(tree, currentFile.value)
      }
    } catch (e: any) {
      error.value = e.response?.data?.detail || "Failed to save file"
      throw e
    } finally {
      fileLoading.value = false
    }
  }

  async function createFile(notebookId: number, path: string, content: string) {
    if (!currentWorkspace.value) return

    fileLoading.value = true
    error.value = null
    try {
      const workspaceSlug = getWorkspaceSlug()
      const notebookSlug = getNotebookSlug(notebookId)
      const newFile = await fileService.create(workspaceSlug, notebookSlug, path, content)

      // Insert the new file into the tree (incremental update)
      if (!fileTrees.value.has(notebookId)) {
        fileTrees.value.set(notebookId, [])
      }
      const tree = fileTrees.value.get(notebookId)!
      insertFileNode(tree, newFile)

      // Select the new file
      await selectFile(newFile)
      return newFile
    } catch (e: any) {
      error.value = e.response?.data?.detail || "Failed to create file"
      throw e
    } finally {
      fileLoading.value = false
    }
  }

  async function deleteFile(_fileId: number) {
    if (!currentWorkspace.value || !currentFile.value) return

    fileLoading.value = true
    error.value = null
    try {
      const workspaceSlug = getWorkspaceSlug()
      const notebookSlug = getNotebookSlug(currentFile.value.notebook_id)
      await fileService.delete(workspaceSlug, notebookSlug, currentFile.value.path)
      const notebookId = currentFile.value.notebook_id
      const filePath = currentFile.value.path
      currentFile.value = null
      isEditing.value = false

      // Remove the file from the tree (incremental update)
      if (notebookId) {
        const tree = fileTrees.value.get(notebookId)
        if (tree) {
          removeNode(tree, filePath)
        }
      }
    } catch (e: any) {
      error.value = e.response?.data?.detail || "Failed to delete file"
      throw e
    } finally {
      fileLoading.value = false
    }
  }

  function toggleNotebookExpansion(notebook: Notebook) {
    const notebookId = notebook.id
    if (expandedNotebooks.value.has(notebookId)) {
      expandedNotebooks.value.delete(notebookId)
    } else {
      expandedNotebooks.value.add(notebookId)
      // Fetch files when expanding
      fetchFiles(notebookId)
    }
    currentNotebook.value = notebook
  }

  function setEditing(editing: boolean) {
    isEditing.value = editing
  }

  function getFilesForNotebook(notebookId: number): FileMetadata[] {
    return files.value.get(notebookId) || []
  }

  async function uploadFile(notebookId: number, file: File, path?: string) {
    if (!currentWorkspace.value) return

    fileLoading.value = true
    error.value = null
    try {
      const workspaceSlug = getWorkspaceSlug()
      const notebookSlug = getNotebookSlug(notebookId)
      const newFile = await fileService.upload(workspaceSlug, notebookSlug, file, path)

      // Insert the new file into the tree (incremental update)
      if (!fileTrees.value.has(notebookId)) {
        fileTrees.value.set(notebookId, [])
      }
      const tree = fileTrees.value.get(notebookId)!
      insertFileNode(tree, newFile)

      return newFile
    } catch (e: any) {
      error.value = e.response?.data?.detail || "Failed to upload file"
      throw e
    } finally {
      fileLoading.value = false
    }
  }

  async function moveFile(fileId: number, notebookId: number, newPath: string) {
    if (!currentWorkspace.value) return

    fileLoading.value = true
    error.value = null
    try {
      // Find the old path before moving
      const tree = fileTrees.value.get(notebookId)
      let oldPath: string | null = null
      if (tree) {
        const allFiles = getAllFiles(tree)
        const file = allFiles.find((f) => f.id === fileId)
        if (file) {
          oldPath = file.path
        }
      }

      if (!oldPath) {
        throw new Error("File not found in tree")
      }

      const workspaceSlug = getWorkspaceSlug()
      const notebookSlug = getNotebookSlug(notebookId)
      const movedFile = await fileService.move(workspaceSlug, notebookSlug, oldPath, newPath)

      // Update the tree: move the node from old path to new path
      if (tree && oldPath) {
        moveNode(tree, oldPath, newPath)
        // Also update the file metadata in the node
        updateFileNode(tree, movedFile)
      }

      // Update current file if it was the one moved
      if (currentFile.value?.id === fileId) {
        currentFile.value = { ...currentFile.value, ...movedFile }
      }
      return movedFile
    } catch (e: any) {
      error.value = e.response?.data?.detail || "Failed to move file"
      throw e
    } finally {
      fileLoading.value = false
    }
  }

  // Folder actions

  /**
   * Select a folder and load its contents.
   * This is a unified operation that:
   * 1. Sets the current folder for display
   * 2. Merges the folder contents into the file tree
   */
  async function selectFolder(folderPath: string, notebookId: number) {
    if (!currentWorkspace.value) return

    currentFile.value = null // Clear current file when selecting folder
    isEditing.value = false

    // Use fetchFolderContents which handles both loading and tree merging
    const folder = await fetchFolderContents(folderPath, notebookId)
    if (folder) {
      currentFolder.value = folder
    }
  }

  async function saveFolderProperties(properties: Record<string, any>) {
    if (!currentWorkspace.value || !currentFolder.value) return

    folderLoading.value = true
    error.value = null
    try {
      const workspaceSlug = getWorkspaceSlug()
      const notebookSlug = getNotebookSlug(currentFolder.value.notebook_id)
      const updated = await folderService.updateProperties(
        workspaceSlug,
        notebookSlug,
        currentFolder.value.path,
        properties,
      )
      // Update currentFolder with new properties
      currentFolder.value = { ...currentFolder.value, ...updated }

      // Update the folder node in the tree (incremental update)
      const tree = fileTrees.value.get(currentFolder.value.notebook_id)
      if (tree) {
        const folderNode = findNode(tree, currentFolder.value.path)
        if (folderNode && folderNode.type === "folder") {
          folderNode.folderMeta = {
            ...folderNode.folderMeta,
            title: updated.title,
            description: updated.description,
            properties: updated.properties,
          }
        }
      }
    } catch (e: any) {
      error.value = e.response?.data?.detail || "Failed to save folder properties"
      throw e
    } finally {
      folderLoading.value = false
    }
  }

  async function deleteFolder() {
    if (!currentWorkspace.value || !currentFolder.value) return

    folderLoading.value = true
    error.value = null
    try {
      const workspaceSlug = getWorkspaceSlug()
      const notebookSlug = getNotebookSlug(currentFolder.value.notebook_id)
      await folderService.delete(workspaceSlug, notebookSlug, currentFolder.value.path)
      const notebookId = currentFolder.value.notebook_id
      const folderPath = currentFolder.value.path
      currentFolder.value = null

      // Remove the folder from the tree (incremental update)
      const tree = fileTrees.value.get(notebookId)
      if (tree) {
        removeNode(tree, folderPath)
      }
    } catch (e: any) {
      error.value = e.response?.data?.detail || "Failed to delete folder"
      throw e
    } finally {
      folderLoading.value = false
    }
  }

  function clearFolderSelection() {
    currentFolder.value = null
  }

  /**
   * Get the file tree for a notebook
   */
  function getFileTree(notebookId: number): FileTreeNode[] {
    return fileTrees.value.get(notebookId) || []
  }

  return {
    // Workspace state
    workspaces,
    currentWorkspace,
    notebooks,
    loading,
    error,
    // File state - tree structure
    fileTrees,
    files, // Backwards-compatible computed flat list
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
    fetchFolderContents,
    selectFile,
    saveFile,
    createFile,
    deleteFile,
    uploadFile,
    moveFile,
    toggleNotebookExpansion,
    setEditing,
    getFilesForNotebook,
    getFileTree,
    // Folder actions
    selectFolder,
    saveFolderProperties,
    deleteFolder,
    clearFolderSelection,
  }
})
