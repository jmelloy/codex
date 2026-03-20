import { defineStore } from "pinia"
import { ref, computed, type ComputedRef } from "vue"
import {
  workspaceService,
  notebookService,
  fileService,
  folderService,
  blockService,
  type Workspace,
  type Notebook,
  type FileMetadata,
  type FileWithContent,
  type FolderWithFiles,
  type Block,
  type PageMetadata,
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
import { websocketService, type FileChangeEvent } from "../services/websocket"

export const useWorkspaceStore = defineStore("workspace", () => {
  const workspaces = ref<Workspace[]>([])
  const currentWorkspace = ref<Workspace | null>(null)
  const notebooks = ref<Notebook[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  // File state - now using tree structure
  const fileTrees = ref<Map<number, FileTreeNode[]>>(new Map()) // notebook_id -> file tree
  const currentFile = ref<FileWithContent | null>(null)
  const expandedNotebooks = ref<Set<number>>(new Set())
  const fileLoading = ref(false)

  // Folder state
  const currentFolder = ref<FolderWithFiles | null>(null)
  const folderLoading = ref(false)

  // WebSocket connection state
  const wsConnected = ref<Set<number>>(new Set())

  // Set up WebSocket event handler
  websocketService.onFileChange((event: FileChangeEvent) => {
    handleFileChangeEvent(event)
  })

  websocketService.onConnectionChange((connected: boolean, notebookId: number) => {
    if (connected) {
      wsConnected.value.add(notebookId)
    } else {
      wsConnected.value.delete(notebookId)
    }
  })

  // Backwards-compatible files accessor (returns flat list from tree)
  const files = computed(() => {
    const flatMap = new Map<number, FileMetadata[]>()
    for (const [notebookId, tree] of fileTrees.value) {
      flatMap.set(notebookId, getAllFiles(tree))
    }
    return flatMap
  })

  // Derived from current file/folder context or first expanded notebook
  const currentNotebook: ComputedRef<Notebook | null> = computed(() => {
    const notebookId = currentFile.value?.notebook_id ?? currentFolder.value?.notebook_id
    if (notebookId) {
      return notebooks.value.find((n) => n.id === notebookId) ?? null
    }
    if (expandedNotebooks.value.size > 0) {
      const firstExpandedId = [...expandedNotebooks.value][0]
      return notebooks.value.find((n) => n.id === firstExpandedId) ?? null
    }
    return null
  })

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

  async function fetchNotebooks(workspaceId: number) {
    loading.value = true
    error.value = null
    try {
      notebooks.value = await notebookService.list(workspaceId)
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

  async function createNotebook(workspaceId: number, name: string) {
    loading.value = true
    error.value = null
    try {
      const notebook = await notebookService.create(workspaceId, name)
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
      fetchNotebooks(workspace.id)
    }
    // Disconnect all WebSocket connections when switching workspaces
    websocketService.disconnectAll()
    wsConnected.value.clear()
    // Clear file and folder state when switching workspaces
    currentFile.value = null
    currentFolder.value = null
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
      const fileList = await fileService.list(notebookId, currentWorkspace.value.id)
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
      const folder = await folderService.get(folderPath, notebookId, currentWorkspace.value.id)

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
      // First fetch file metadata (fast, no content)
      const fileMeta = await fileService.get(file.id, currentWorkspace.value.id, file.notebook_id)

      // Set file with empty content initially so UI can render metadata immediately
      currentFile.value = { ...fileMeta, content: "" }

      // Then fetch content for text-based files
      const isTextFile =
        fileMeta.content_type.startsWith("text/") ||
        ["application/json", "application/xml"].includes(
          fileMeta.content_type,
        )

      if (isTextFile) {
        const textContent = await fileService.getContent(
          file.id,
          currentWorkspace.value.id,
          file.notebook_id,
        )
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

  async function saveFile(content: string, properties?: Record<string, any>, keepEditing: boolean = false) {
    if (!currentWorkspace.value || !currentFile.value) return

    // Don't set fileLoading during autosave (keepEditing) — it unmounts the editor and resets the cursor
    if (!keepEditing) {
      fileLoading.value = true
    }
    error.value = null
    try {
      if (!currentFile.value.notebook_id) {
        throw new Error("File has no notebook_id")
      }
      const updated = await fileService.update(
        currentFile.value.id,
        currentWorkspace.value.id,
        currentFile.value.notebook_id,
        content,
        properties,
      )
      // Update currentFile with new content and properties
      currentFile.value = { ...currentFile.value, ...updated, content }
      // Update the file node in the tree (incremental update)
      const tree = fileTrees.value.get(currentFile.value.notebook_id)
      if (tree) {
        updateFileNode(tree, currentFile.value)
      }
    } catch (e: any) {
      error.value = e.response?.data?.detail || "Failed to save file"
      throw e
    } finally {
      if (!keepEditing) {
        fileLoading.value = false
      }
    }
  }

  async function createFile(notebookId: number, path: string, content: string) {
    if (!currentWorkspace.value) return

    fileLoading.value = true
    error.value = null
    try {
      const newFile = await fileService.create(notebookId, currentWorkspace.value.id, path, content)

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

  async function deleteFile(fileId: number) {
    if (!currentWorkspace.value || !currentFile.value) return

    fileLoading.value = true
    error.value = null
    try {
      const notebookId = currentFile.value.notebook_id
      await fileService.delete(fileId, currentWorkspace.value.id, notebookId)
      const filePath = currentFile.value.path
      currentFile.value = null

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
      // Disconnect WebSocket when collapsing
      websocketService.disconnect(notebookId)
    } else {
      expandedNotebooks.value.add(notebookId)
      // Fetch files when expanding
      fetchFiles(notebookId)
      // Connect WebSocket for real-time updates
      websocketService.connect(notebookId)
    }
  }

  /**
   * Handle file change events from WebSocket.
   * Updates the file tree incrementally based on the event type.
   */
  async function handleFileChangeEvent(event: FileChangeEvent) {
    const tree = fileTrees.value.get(event.notebook_id)
    if (!tree) {
      // No tree loaded for this notebook, ignore
      return
    }

    switch (event.event_type) {
      case "created":
      case "modified":
      case "scanned":
        // Fetch the updated file metadata from the API
        if (currentWorkspace.value) {
          try {
            const file = await fileService.getByPath(
              event.path,
              currentWorkspace.value.id,
              event.notebook_id,
            )
            if (event.event_type === "created") {
              insertFileNode(tree, file)
            } else {
              // For modified, update the existing node
              if (!updateFileNode(tree, file)) {
                // If node not found, insert it (might have been created outside our view)
                insertFileNode(tree, file)
              }
            }

            // Update current file if it's the one that changed
            if (currentFile.value?.path === event.path && currentFile.value?.notebook_id === event.notebook_id) {
              // Refresh the file content
              await selectFile(file)
            }
          } catch (e) {
            console.warn(`Failed to fetch file metadata for ${event.path}:`, e)
          }
        }
        break

      case "deleted":
        removeNode(tree, event.path)
        // Clear current file if it was deleted
        if (currentFile.value?.path === event.path && currentFile.value?.notebook_id === event.notebook_id) {
          currentFile.value = null
        }
        // Clear current folder if it was deleted
        if (currentFolder.value?.path === event.path && currentFolder.value?.notebook_id === event.notebook_id) {
          currentFolder.value = null
        }
        break

      case "moved":
        if (event.old_path) {
          // Move node from old path to new path
          moveNode(tree, event.old_path, event.path)

          // Fetch updated metadata for the moved file
          if (currentWorkspace.value) {
            try {
              const file = await fileService.getByPath(
                event.path,
                currentWorkspace.value.id,
                event.notebook_id,
              )
              updateFileNode(tree, file)

              // Update current file if it was moved
              if (currentFile.value?.path === event.old_path && currentFile.value?.notebook_id === event.notebook_id) {
                currentFile.value = { ...currentFile.value, ...file }
              }
            } catch (e) {
              console.warn(`Failed to fetch moved file metadata for ${event.path}:`, e)
            }
          }
        }
        break
    }
  }

  function getFilesForNotebook(notebookId: number): FileMetadata[] {
    return files.value.get(notebookId) || []
  }

  async function uploadFile(notebookId: number, file: File, path?: string) {
    if (!currentWorkspace.value) return

    fileLoading.value = true
    error.value = null
    try {
      const newFile = await fileService.upload(notebookId, currentWorkspace.value.id, file, path)

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

      const movedFile = await fileService.move(
        fileId,
        currentWorkspace.value.id,
        notebookId,
        newPath,
      )

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

    // Use fetchFolderContents which handles both loading and tree merging
    const folder = await fetchFolderContents(folderPath, notebookId)
    if (folder) {
      currentFolder.value = folder

      // If this folder is a page, also fetch its blocks
      if (folder.is_page) {
        try {
          // Fetch the page block to get its block_id, then fetch children
          const rootBlocks = await blockService.listRootBlocks(notebookId, currentWorkspace.value.id)
          // Find the block matching this folder path
          const pageBlock = rootBlocks.blocks.find((b: Block) => b.path === folderPath)
          if (pageBlock) {
            currentPageBlockId.value = pageBlock.block_id
            await fetchPageBlocks(pageBlock.block_id, notebookId)
          }
        } catch {
          // Block loading is optional - folder still works without it
          currentPageBlocks.value = []
          currentPageBlockId.value = null
        }
      } else {
        currentPageBlocks.value = []
        currentPageMeta.value = null
        currentPageBlockId.value = null
      }
    }
  }

  async function saveFolderProperties(properties: Record<string, any>) {
    if (!currentWorkspace.value || !currentFolder.value) return

    folderLoading.value = true
    error.value = null
    try {
      const oldPath = currentFolder.value.path
      const updated = await folderService.updateProperties(
        currentFolder.value.path,
        currentFolder.value.notebook_id,
        currentWorkspace.value.id,
        properties,
      )

      // Check if the folder was renamed (path changed)
      const pathChanged = updated.path !== oldPath

      // Update currentFolder with new properties and potentially new path
      currentFolder.value = { ...currentFolder.value, ...updated }

      // Update the folder node in the tree (incremental update)
      const tree = fileTrees.value.get(currentFolder.value.notebook_id)
      if (tree) {
        if (pathChanged) {
          // Folder was renamed on disk - move the node in the tree
          moveNode(tree, oldPath, updated.path)
        }
        const folderNode = findNode(tree, currentFolder.value.path)
        if (folderNode && folderNode.type === "folder") {
          folderNode.name = updated.name || currentFolder.value.path.split("/").pop() || ""
          folderNode.folderMeta = {
            ...folderNode.folderMeta,
            title: updated.title,
            description: updated.description,
            properties: updated.properties,
          }
        }
      }

      return { pathChanged, oldPath, newPath: updated.path }
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
      await folderService.delete(
        currentFolder.value.path,
        currentFolder.value.notebook_id,
        currentWorkspace.value.id,
      )
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

  // Block state
  const currentPageBlocks = ref<Block[]>([])
  const currentPageMeta = ref<PageMetadata | null>(null)
  const currentPageBlockId = ref<string | null>(null)
  const blockLoading = ref(false)

  /**
   * Fetch blocks for a page and set as current
   */
  async function fetchPageBlocks(blockId: string, notebookId: number) {
    if (!currentWorkspace.value) return
    blockLoading.value = true
    try {
      const result = await blockService.getChildren(
        blockId,
        notebookId,
        currentWorkspace.value.id,
      )
      currentPageBlocks.value = result.children
    } catch (e: any) {
      error.value = e.response?.data?.detail || "Failed to fetch page blocks"
    } finally {
      blockLoading.value = false
    }
  }

  /**
   * Create a new page
   */
  async function createPage(
    notebookId: number,
    title: string,
    parentPath?: string,
    description?: string,
  ) {
    if (!currentWorkspace.value) return
    try {
      const result = await blockService.createPage(notebookId, currentWorkspace.value.id, {
        title,
        parent_path: parentPath,
        description,
      })
      // Refresh the file tree to show the new page folder
      await fetchFiles(notebookId)
      // Select the new page folder
      if (result.path) {
        await selectFolder(result.path, notebookId)
      }
      return result
    } catch (e: any) {
      error.value = e.response?.data?.detail || "Failed to create page"
      throw e
    }
  }

  /**
   * Create a block within a page
   */
  async function createBlock(
    notebookId: number,
    parentBlockId: string,
    blockType: string = "text",
    content: string = "",
    position?: number,
  ) {
    if (!currentWorkspace.value) return
    try {
      const result = await blockService.createBlock(notebookId, currentWorkspace.value.id, {
        parent_block_id: parentBlockId,
        block_type: blockType,
        content,
        position,
      })
      // Refresh blocks
      await fetchPageBlocks(parentBlockId, notebookId)
      return result
    } catch (e: any) {
      error.value = e.response?.data?.detail || "Failed to create block"
      throw e
    }
  }

  /**
   * Reorder blocks within a page
   */
  async function reorderBlocks(
    notebookId: number,
    pageBlockId: string,
    blockIds: string[],
  ) {
    if (!currentWorkspace.value) return
    try {
      await blockService.reorderBlocks(pageBlockId, notebookId, currentWorkspace.value.id, blockIds)
      await fetchPageBlocks(pageBlockId, notebookId)
    } catch (e: any) {
      error.value = e.response?.data?.detail || "Failed to reorder blocks"
    }
  }

  /**
   * Delete a block
   */
  async function deleteBlock(
    notebookId: number,
    blockId: string,
    parentBlockId: string,
  ) {
    if (!currentWorkspace.value) return
    try {
      await blockService.deleteBlock(blockId, notebookId, currentWorkspace.value.id)
      await fetchPageBlocks(parentBlockId, notebookId)
    } catch (e: any) {
      error.value = e.response?.data?.detail || "Failed to delete block"
      throw e
    }
  }

  /**
   * Import a markdown file as a page of blocks
   */
  async function importMarkdown(notebookId: number, file: File) {
    if (!currentWorkspace.value) return
    try {
      const result = await blockService.importMarkdown(notebookId, currentWorkspace.value.id, file)
      await fetchFiles(notebookId)
      return result
    } catch (e: any) {
      error.value = e.response?.data?.detail || "Failed to import markdown"
      throw e
    }
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
    expandedNotebooks,
    fileLoading,
    // Folder state
    currentFolder,
    folderLoading,
    // WebSocket state
    wsConnected,
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
    getFilesForNotebook,
    getFileTree,
    // Folder actions
    selectFolder,
    saveFolderProperties,
    deleteFolder,
    clearFolderSelection,
    // Block state
    currentPageBlocks,
    currentPageMeta,
    currentPageBlockId,
    blockLoading,
    // Block actions
    fetchPageBlocks,
    createPage,
    createBlock,
    reorderBlocks,
    deleteBlock,
    importMarkdown,
  }
})
