import { defineStore } from "pinia"
import { ref, computed, type ComputedRef } from "vue"
import {
  workspaceService,
  notebookService,
  folderService,
  blockService,
  type Workspace,
  type Notebook,
  type FolderWithFiles,
  type Block,
  type PageMetadata,
} from "../services/codex"
import {
  type FileTreeNode,
  blockTreeToFileTree,
  removeNode,
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
  const currentFile = ref<(Block & { content: string }) | null>(null)
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
    const flatMap = new Map<number, Block[]>()
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
      const result = await blockService.getTree(notebookId, currentWorkspace.value.id)
      const tree = blockTreeToFileTree(result.tree)
      fileTrees.value.set(notebookId, tree)
    } catch (e: any) {
      error.value = e.response?.data?.detail || "Failed to fetch files"
    } finally {
      fileLoading.value = false
    }
  }

  /**
   * Fetch folder contents via block children.
   * Falls back to legacy folderService if block lookup fails.
   */
  async function fetchFolderContents(
    folderPath: string,
    notebookId: number,
  ): Promise<FolderWithFiles | null> {
    if (!currentWorkspace.value) return null

    folderLoading.value = true
    error.value = null
    try {
      // Try to find the page block for this folder path
      const tree = fileTrees.value.get(notebookId) || []
      const folderNode = findNode(tree, folderPath)
      if (folderNode?.block_id) {
        // Use block API to get children
        const result = await blockService.getChildren(
          folderNode.block_id,
          notebookId,
          currentWorkspace.value.id,
        )
        // Return as FolderWithFiles for compatibility
        return {
          path: folderPath,
          name: folderNode.name,
          notebook_id: notebookId,
          title: folderNode.title,
          file_count: result.children.length,
          files: [],
          subfolders: [],
          is_page: true,
          page_block_id: folderNode.block_id,
          blocks: result.children,
        } as FolderWithFiles
      }

      // Fall back to legacy folder service
      const folder = await folderService.get(folderPath, notebookId, currentWorkspace.value.id)

      // Get or create the tree for this notebook
      if (!fileTrees.value.has(notebookId)) {
        fileTrees.value.set(notebookId, [])
      }
      const treeForMerge = fileTrees.value.get(notebookId)!
      mergeFolderContents(treeForMerge, folderPath, folder)

      return folder
    } catch (e: any) {
      error.value = e.response?.data?.detail || "Failed to load folder"
      return null
    } finally {
      folderLoading.value = false
    }
  }

  /**
   * Fetch root-level contents for a notebook.
   * Uses block tree API, falling back to legacy folder service.
   */
  async function fetchRootContents(notebookId: number) {
    if (!currentWorkspace.value) return

    fileLoading.value = true
    error.value = null
    try {
      // Try block tree first
      try {
        const result = await blockService.getTree(notebookId, currentWorkspace.value.id)
        const tree = blockTreeToFileTree(result.tree)
        fileTrees.value.set(notebookId, tree)
        return
      } catch {
        // Fall through to legacy
      }

      const folder = await folderService.get("", notebookId, currentWorkspace.value.id)
      if (!fileTrees.value.has(notebookId)) {
        fileTrees.value.set(notebookId, [])
      }
      const tree = fileTrees.value.get(notebookId)!
      mergeFolderContents(tree, "", folder)
    } catch (e: any) {
      error.value = e.response?.data?.detail || "Failed to fetch notebook contents"
    } finally {
      fileLoading.value = false
    }
  }

  async function selectFile(file: Block) {
    if (!currentWorkspace.value) return

    fileLoading.value = true
    error.value = null
    currentFolder.value = null
    try {
      const blockDetail = await blockService.getBlock(
        file.block_id,
        file.notebook_id,
        currentWorkspace.value.id,
      )

      currentFile.value = { ...blockDetail, content: blockDetail.content || "" }

      const isTextFile =
        (blockDetail.content_type || "").startsWith("text/") ||
        ["application/json", "application/xml"].includes(blockDetail.content_type || "")

      if (isTextFile && !blockDetail.content) {
        try {
          const textContent = await blockService.getText(
            file.block_id,
            file.notebook_id,
            currentWorkspace.value.id,
          )
          currentFile.value = {
            ...blockDetail,
            content: textContent.content,
            properties: textContent.properties ?? blockDetail.properties,
          }
        } catch {
          // Content might not be text-readable
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

    if (!keepEditing) {
      fileLoading.value = true
    }
    error.value = null
    try {
      if (!currentFile.value.notebook_id) {
        throw new Error("File has no notebook_id")
      }
      const updated = await blockService.updateBlock(
        currentFile.value.block_id,
        currentFile.value.notebook_id,
        currentWorkspace.value.id,
        content,
      )
      if (properties) {
        await blockService.updateProperties(
          currentFile.value.block_id,
          currentFile.value.notebook_id,
          currentWorkspace.value.id,
          properties,
        )
      }
      currentFile.value = { ...currentFile.value, ...updated, content }
    } catch (e: any) {
      error.value = e.response?.data?.detail || "Failed to save file"
      throw e
    } finally {
      if (!keepEditing) {
        fileLoading.value = false
      }
    }
  }

  async function createFile(notebookId: number, path: string, _content: string) {
    if (!currentWorkspace.value) return

    fileLoading.value = true
    error.value = null
    try {
      const result = await blockService.createPage(notebookId, currentWorkspace.value.id, {
        title: path,
      })
      await fetchBlockTree(notebookId)
      if (result.path) {
        await selectFolder(result.path, notebookId)
      }
      return result
    } catch (e: any) {
      error.value = e.response?.data?.detail || "Failed to create file"
      throw e
    } finally {
      fileLoading.value = false
    }
  }

  async function deleteFile(blockId: string) {
    if (!currentWorkspace.value || !currentFile.value) return

    fileLoading.value = true
    error.value = null
    try {
      const notebookId = currentFile.value.notebook_id
      await blockService.deleteBlock(blockId, notebookId, currentWorkspace.value.id)
      const filePath = currentFile.value.path
      currentFile.value = null

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
      // Fetch block tree (falls back to legacy fetchRootContents)
      fetchBlockTree(notebookId)
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
        if (currentWorkspace.value) {
          try {
            // Refresh the block tree to pick up changes
            await fetchBlockTree(event.notebook_id)

            // Also update currentBlock if relevant
            if (currentBlock.value?.path === event.path && currentBlock.value?.notebook_id === event.notebook_id) {
              await selectBlock(currentBlock.value)
            }
          } catch (e) {
            console.warn(`Failed to refresh tree for ${event.path}:`, e)
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
          moveNode(tree, event.old_path, event.path)

          if (currentWorkspace.value) {
            try {
              await fetchBlockTree(event.notebook_id)
            } catch (e) {
              console.warn(`Failed to refresh tree after move for ${event.path}:`, e)
            }
          }
        }
        break
    }
  }

  function getFilesForNotebook(notebookId: number): Block[] {
    return files.value.get(notebookId) || []
  }

  async function uploadFile(notebookId: number, file: File, _path?: string) {
    if (!currentWorkspace.value) return

    fileLoading.value = true
    error.value = null
    try {
      const newBlock = await blockService.upload(notebookId, currentWorkspace.value.id, file)
      await fetchBlockTree(notebookId)
      return newBlock
    } catch (e: any) {
      error.value = e.response?.data?.detail || "Failed to upload file"
      throw e
    } finally {
      fileLoading.value = false
    }
  }

  async function moveFile(blockId: string, notebookId: number, _newPath: string) {
    if (!currentWorkspace.value) return

    fileLoading.value = true
    error.value = null
    try {
      const movedBlock = await blockService.moveBlock(
        blockId,
        notebookId,
        currentWorkspace.value.id,
        {},
      )
      await fetchBlockTree(notebookId)

      if (currentFile.value?.block_id === blockId) {
        currentFile.value = { ...currentFile.value, ...movedBlock, content: currentFile.value.content }
      }
      return movedBlock
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

      // Backend returns page data directly in the folder response
      if (folder.is_page && folder.page_block_id) {
        currentPageBlockId.value = folder.page_block_id
        currentPageBlocks.value = folder.blocks || []
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
  const currentBlock = ref<Block | null>(null)
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
      // Refresh the parent folder contents to show the new page
      await fetchRootContents(notebookId)
      // Select the new page folder (backend already created initial block)
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
      // Backend returns updated siblings - use directly
      if (result.blocks) {
        currentPageBlocks.value = result.blocks
      }
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
      const result = await blockService.reorderBlocks(pageBlockId, notebookId, currentWorkspace.value.id, blockIds)
      // Backend returns reordered children with content
      if (result.blocks) {
        currentPageBlocks.value = result.blocks
      }
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
    _parentBlockId: string,
  ) {
    if (!currentWorkspace.value) return
    try {
      const result = await blockService.deleteBlock(blockId, notebookId, currentWorkspace.value.id)
      // Backend returns remaining siblings
      if (result.blocks) {
        currentPageBlocks.value = result.blocks
      }
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
      await fetchRootContents(notebookId)
      return result
    } catch (e: any) {
      error.value = e.response?.data?.detail || "Failed to import markdown"
      throw e
    }
  }

  /**
   * Fetch the block tree for a notebook and build the file tree from it.
   * This is the unified replacement for fetchFiles + fetchRootContents.
   */
  async function fetchBlockTree(notebookId: number) {
    if (!currentWorkspace.value) return

    fileLoading.value = true
    error.value = null
    try {
      const result = await blockService.getTree(notebookId, currentWorkspace.value.id)
      const tree = blockTreeToFileTree(result.tree)
      fileTrees.value.set(notebookId, tree)
    } catch (e: any) {
      // Fall back to legacy fetchRootContents if /tree endpoint not available
      console.warn("Block tree fetch failed, falling back to legacy:", e)
      await fetchRootContents(notebookId)
    } finally {
      fileLoading.value = false
    }
  }

  /**
   * Select a block and load its content.
   * Unified replacement for selectFile + selectFolder.
   */
  async function selectBlock(block: Block) {
    if (!currentWorkspace.value) return

    currentBlock.value = block
    blockLoading.value = true
    error.value = null

    try {
      if (block.block_type === "page") {
        // For pages, load children and set as current folder-like view
        currentFile.value = null
        currentPageBlockId.value = block.block_id

        const result = await blockService.getChildren(
          block.block_id,
          block.notebook_id,
          currentWorkspace.value.id,
        )
        currentPageBlocks.value = result.children

        // Set currentFolder for backwards compatibility
        currentFolder.value = {
          path: block.path,
          name: block.title || block.path.split("/").pop() || "",
          notebook_id: block.notebook_id,
          title: block.title,
          description: block.description,
          properties: block.properties,
          file_count: result.children.filter((c: Block) => c.block_type !== "page").length,
          is_page: true,
          page_block_id: block.block_id,
          blocks: result.children,
        } as any
      } else {
        // For leaf blocks, load content
        currentFolder.value = null
        currentPageBlocks.value = []

        const blockDetail = await blockService.getBlock(
          block.block_id,
          block.notebook_id,
          currentWorkspace.value.id,
        )

        // Set currentFile for backwards compatibility
        const isText = block.content_type?.startsWith("text/") ||
          ["application/json", "application/xml"].includes(block.content_type || "")

        let content = blockDetail.content || ""
        if (isText && !content) {
          try {
            const textResult = await blockService.getText(
              block.block_id,
              block.notebook_id,
              currentWorkspace.value.id,
            )
            content = textResult.content
          } catch {
            // Content might not be text-readable
          }
        }

        currentFile.value = {
          ...blockDetail,
          content,
        }
      }
    } catch (e: any) {
      error.value = e.response?.data?.detail || "Failed to load block"
    } finally {
      blockLoading.value = false
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
    fetchRootContents,
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
    currentBlock,
    currentPageBlocks,
    currentPageMeta,
    currentPageBlockId,
    blockLoading,
    // Block actions
    fetchBlockTree,
    selectBlock,
    fetchPageBlocks,
    createPage,
    createBlock,
    reorderBlocks,
    deleteBlock,
    importMarkdown,
  }
})
