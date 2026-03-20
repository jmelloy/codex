import { defineStore } from "pinia"
import { ref, computed, type ComputedRef } from "vue"
import {
  workspaceService,
  notebookService,
  blockService,
  type Workspace,
  type Notebook,
  type Block,
  type PageMetadata,
} from "../services/codex"
import {
  type FileTreeNode,
  blockTreeToFileTree,
  removeNode,
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

  // Unified block state
  const fileTrees = ref<Map<number, FileTreeNode[]>>(new Map()) // notebook_id -> file tree
  const currentBlock = ref<Block | null>(null)
  const currentPageBlocks = ref<Block[]>([])
  const currentPageMeta = ref<PageMetadata | null>(null)
  const currentPageBlockId = ref<string | null>(null)
  const blockLoading = ref(false)
  const expandedNotebooks = ref<Set<number>>(new Set())

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

  // Backwards-compatible flat files accessor
  const files = computed(() => {
    const flatMap = new Map<number, Block[]>()
    for (const [notebookId, tree] of fileTrees.value) {
      flatMap.set(notebookId, getAllFiles(tree))
    }
    return flatMap
  })

  // Derived: is current block a page?
  const isPage = computed(() => currentBlock.value?.block_type === "page")

  // Derived: current file (leaf block with content) for backwards compatibility
  const currentFile = computed(() => {
    if (!currentBlock.value || currentBlock.value.block_type === "page") return null
    return currentBlock.value as Block & { content: string }
  })

  // Derived: current folder-like view for backwards compatibility
  const currentFolder = computed(() => {
    if (!currentBlock.value || currentBlock.value.block_type !== "page") return null
    return {
      path: currentBlock.value.path,
      name: currentBlock.value.title || currentBlock.value.path.split("/").pop() || "",
      notebook_id: currentBlock.value.notebook_id,
      title: currentBlock.value.title,
      description: currentBlock.value.description,
      properties: currentBlock.value.properties,
      file_count: currentPageBlocks.value.filter((c: Block) => c.block_type !== "page").length,
      is_page: true,
      page_block_id: currentBlock.value.block_id,
      blocks: currentPageBlocks.value,
    }
  })

  // Derived from current block context or first expanded notebook
  const currentNotebook: ComputedRef<Notebook | null> = computed(() => {
    const notebookId = currentBlock.value?.notebook_id
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
    // Clear all block state when switching workspaces
    currentBlock.value = null
    currentPageBlocks.value = []
    currentPageMeta.value = null
    currentPageBlockId.value = null
    fileTrees.value.clear()
    expandedNotebooks.value.clear()
  }

  /**
   * Fetch the block tree for a notebook and build the file tree.
   */
  async function fetchBlockTree(notebookId: number) {
    if (!currentWorkspace.value) return

    blockLoading.value = true
    error.value = null
    try {
      const result = await blockService.getTree(notebookId, currentWorkspace.value.id)
      const tree = blockTreeToFileTree(result.tree)
      fileTrees.value.set(notebookId, tree)
    } catch (e: any) {
      error.value = e.response?.data?.detail || "Failed to fetch files"
    } finally {
      blockLoading.value = false
    }
  }

  /**
   * Select a block and load its content.
   * Unified handler for both pages and leaf blocks.
   */
  async function selectBlock(block: Block) {
    if (!currentWorkspace.value) return

    currentBlock.value = block
    blockLoading.value = true
    error.value = null

    try {
      if (block.block_type === "page") {
        // For pages, load children
        currentPageBlockId.value = block.block_id

        const result = await blockService.getChildren(
          block.block_id,
          block.notebook_id,
          currentWorkspace.value.id,
        )
        currentPageBlocks.value = result.children
      } else {
        // For leaf blocks, load content
        currentPageBlocks.value = []
        currentPageBlockId.value = null

        const blockDetail = await blockService.getBlock(
          block.block_id,
          block.notebook_id,
          currentWorkspace.value.id,
        )

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

        currentBlock.value = {
          ...blockDetail,
          content,
        } as Block
      }
    } catch (e: any) {
      error.value = e.response?.data?.detail || "Failed to load block"
    } finally {
      blockLoading.value = false
    }
  }

  /**
   * Select a block by its folder path (resolves path to block via tree).
   */
  async function selectFolder(folderPath: string, notebookId: number) {
    if (!currentWorkspace.value) return

    // Find the block in the tree
    const tree = fileTrees.value.get(notebookId) || []
    const node = findNode(tree, folderPath)
    if (node?.block) {
      await selectBlock(node.block)
    } else if (node?.block_id) {
      // Construct a minimal block to select
      const block: Block = {
        id: 0,
        block_id: node.block_id,
        parent_block_id: node.parent_block_id || null,
        notebook_id: notebookId,
        path: folderPath,
        block_type: (node.block_type as Block["block_type"]) || "page",
        content_format: "markdown",
        order_index: 0,
        title: node.title || node.folderMeta?.title,
        description: node.folderMeta?.description,
        properties: node.folderMeta?.properties,
        created_at: "",
        updated_at: "",
      }
      await selectBlock(block)
    } else {
      // Try resolving via API
      try {
        const resolved = await blockService.resolveLink(folderPath, notebookId, currentWorkspace.value.id)
        await selectBlock(resolved)
      } catch {
        error.value = "Failed to find folder"
      }
    }
  }

  /**
   * Save content for the current block.
   */
  async function saveFile(content: string, properties?: Record<string, any>, keepEditing: boolean = false) {
    if (!currentWorkspace.value || !currentBlock.value) return

    if (!keepEditing) {
      blockLoading.value = true
    }
    error.value = null
    try {
      if (!currentBlock.value.notebook_id) {
        throw new Error("File has no notebook_id")
      }
      const updated = await blockService.updateBlock(
        currentBlock.value.block_id,
        currentBlock.value.notebook_id,
        currentWorkspace.value.id,
        content,
      )
      if (properties) {
        await blockService.updateProperties(
          currentBlock.value.block_id,
          currentBlock.value.notebook_id,
          currentWorkspace.value.id,
          properties,
        )
      }
      currentBlock.value = { ...currentBlock.value, ...updated, content } as Block
    } catch (e: any) {
      error.value = e.response?.data?.detail || "Failed to save file"
      throw e
    } finally {
      if (!keepEditing) {
        blockLoading.value = false
      }
    }
  }

  async function createFile(notebookId: number, path: string, _content: string) {
    if (!currentWorkspace.value) return

    blockLoading.value = true
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
      blockLoading.value = false
    }
  }

  async function deleteFile(blockId: string) {
    if (!currentWorkspace.value || !currentBlock.value) return

    blockLoading.value = true
    error.value = null
    try {
      const notebookId = currentBlock.value.notebook_id
      await blockService.deleteBlock(blockId, notebookId, currentWorkspace.value.id)
      const filePath = currentBlock.value.path
      currentBlock.value = null
      currentPageBlocks.value = []
      currentPageBlockId.value = null

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
      blockLoading.value = false
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
      fetchBlockTree(notebookId)
      websocketService.connect(notebookId)
    }
  }

  /**
   * Handle file change events from WebSocket.
   */
  async function handleFileChangeEvent(event: FileChangeEvent) {
    const tree = fileTrees.value.get(event.notebook_id)
    if (!tree) return

    switch (event.event_type) {
      case "created":
      case "modified":
      case "scanned":
        if (currentWorkspace.value) {
          try {
            await fetchBlockTree(event.notebook_id)
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
        if (currentBlock.value?.path === event.path && currentBlock.value?.notebook_id === event.notebook_id) {
          currentBlock.value = null
          currentPageBlocks.value = []
          currentPageBlockId.value = null
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

    blockLoading.value = true
    error.value = null
    try {
      const newBlock = await blockService.upload(notebookId, currentWorkspace.value.id, file)
      await fetchBlockTree(notebookId)
      return newBlock
    } catch (e: any) {
      error.value = e.response?.data?.detail || "Failed to upload file"
      throw e
    } finally {
      blockLoading.value = false
    }
  }

  async function moveFile(blockId: string, notebookId: number, _newPath: string) {
    if (!currentWorkspace.value) return

    blockLoading.value = true
    error.value = null
    try {
      const movedBlock = await blockService.moveBlock(
        blockId,
        notebookId,
        currentWorkspace.value.id,
        {},
      )
      await fetchBlockTree(notebookId)

      if (currentBlock.value?.block_id === blockId) {
        currentBlock.value = { ...currentBlock.value, ...movedBlock } as Block
      }
      return movedBlock
    } catch (e: any) {
      error.value = e.response?.data?.detail || "Failed to move file"
      throw e
    } finally {
      blockLoading.value = false
    }
  }

  /**
   * Fetch blocks for a page
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
      await fetchBlockTree(notebookId)
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
      await fetchBlockTree(notebookId)
      return result
    } catch (e: any) {
      error.value = e.response?.data?.detail || "Failed to import markdown"
      throw e
    }
  }

  /**
   * Delete a page/folder block
   */
  async function deleteFolder() {
    if (!currentWorkspace.value || !currentBlock.value) return

    blockLoading.value = true
    error.value = null
    try {
      await blockService.deleteBlock(
        currentBlock.value.block_id,
        currentBlock.value.notebook_id,
        currentWorkspace.value.id,
      )
      const notebookId = currentBlock.value.notebook_id
      const blockPath = currentBlock.value.path
      currentBlock.value = null
      currentPageBlocks.value = []
      currentPageBlockId.value = null

      const tree = fileTrees.value.get(notebookId)
      if (tree) {
        removeNode(tree, blockPath)
      }
    } catch (e: any) {
      error.value = e.response?.data?.detail || "Failed to delete folder"
      throw e
    } finally {
      blockLoading.value = false
    }
  }

  /**
   * Save properties for the current page block
   */
  async function saveFolderProperties(properties: Record<string, any>) {
    if (!currentWorkspace.value || !currentBlock.value) return

    blockLoading.value = true
    error.value = null
    try {
      const updated = await blockService.updateProperties(
        currentBlock.value.block_id,
        currentBlock.value.notebook_id,
        currentWorkspace.value.id,
        properties,
      )

      currentBlock.value = { ...currentBlock.value, ...updated } as Block

      // Refresh tree to pick up changes
      await fetchBlockTree(currentBlock.value.notebook_id)
    } catch (e: any) {
      error.value = e.response?.data?.detail || "Failed to save folder properties"
      throw e
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

  // Legacy aliases for backwards compatibility during migration
  const fileLoading = blockLoading
  const folderLoading = blockLoading

  // selectFile is now an alias for selectBlock (for leaf blocks)
  async function selectFile(file: Block) {
    return selectBlock(file)
  }

  return {
    // Workspace state
    workspaces,
    currentWorkspace,
    notebooks,
    loading,
    error,
    // Block state
    fileTrees,
    files, // Backwards-compatible computed flat list
    currentNotebook,
    currentBlock,
    currentFile, // Computed: leaf block with content
    currentFolder, // Computed: page block as folder
    isPage,
    expandedNotebooks,
    blockLoading,
    fileLoading, // Alias for blockLoading
    folderLoading, // Alias for blockLoading
    currentPageBlocks,
    currentPageMeta,
    currentPageBlockId,
    // WebSocket state
    wsConnected,
    // Workspace actions
    fetchWorkspaces,
    fetchNotebooks,
    createWorkspace,
    createNotebook,
    setCurrentWorkspace,
    // Block actions
    fetchBlockTree,
    selectBlock,
    selectFile, // Alias for selectBlock
    selectFolder, // Resolves path then calls selectBlock
    saveFile,
    createFile,
    deleteFile,
    uploadFile,
    moveFile,
    toggleNotebookExpansion,
    getFilesForNotebook,
    getFileTree,
    // Page actions
    saveFolderProperties,
    deleteFolder,
    fetchPageBlocks,
    createPage,
    createBlock,
    reorderBlocks,
    deleteBlock,
    importMarkdown,
  }
})
