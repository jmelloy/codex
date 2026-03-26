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
  type BlockTreeNode,
  blockTreeToBlockTree,
  removeNode,
  getAllBlocks,
  findNode,
  moveNode,
} from "../utils/blockTree"
import { websocketService, type FileChangeEvent } from "../services/websocket"

export const useWorkspaceStore = defineStore("workspace", () => {
  const workspaces = ref<Workspace[]>([])
  const currentWorkspace = ref<Workspace | null>(null)
  const notebooks = ref<Notebook[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  // Block state
  const blockTrees = ref<Map<number, BlockTreeNode[]>>(new Map()) // notebook_id -> block tree
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

  // Flat blocks accessor (all leaf blocks across notebooks)
  const allBlocks = computed(() => {
    const flatMap = new Map<number, Block[]>()
    for (const [notebookId, tree] of blockTrees.value) {
      flatMap.set(notebookId, getAllBlocks(tree))
    }
    return flatMap
  })

  // Derived: is current block a page?
  const isPage = computed(() => currentBlock.value?.block_type === "page")

  // Derived: current leaf block (non-page block with content)
  const currentLeafBlock = computed(() => {
    if (!currentBlock.value || currentBlock.value.block_type === "page") return null
    return currentBlock.value as Block & { content: string }
  })

  // Derived: current page block
  const currentPageBlock = computed(() => {
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

  function notebookSlug(notebookId: number): string {
    const nb = notebooks.value.find((n) => n.id === notebookId)
    return nb?.slug ?? String(notebookId)
  }

  function workspaceSlug(): string {
    return currentWorkspace.value?.slug ?? ""
  }

  async function fetchNotebooks(_workspaceId: number) {
    loading.value = true
    error.value = null
    try {
      notebooks.value = await notebookService.list(workspaceSlug())
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

  async function createNotebook(_workspaceId: number, name: string) {
    loading.value = true
    error.value = null
    try {
      const notebook = await notebookService.create(workspaceSlug(), name)
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
      fetchNotebooks(workspace.id) // fetchNotebooks uses workspaceSlug() internally
    }
    // Disconnect all WebSocket connections when switching workspaces
    websocketService.disconnectAll()
    wsConnected.value.clear()
    // Clear all block state when switching workspaces
    currentBlock.value = null
    currentPageBlocks.value = []
    currentPageMeta.value = null
    currentPageBlockId.value = null
    blockTrees.value.clear()
    expandedNotebooks.value.clear()
  }

  /**
   * Fetch the block tree for a notebook.
   */
  async function fetchBlockTree(notebookId: number) {
    if (!currentWorkspace.value) return

    blockLoading.value = true
    error.value = null
    try {
      const result = await blockService.getTree(notebookSlug(notebookId), workspaceSlug())
      const tree = blockTreeToBlockTree(result.tree)
      blockTrees.value.set(notebookId, tree)
    } catch (e: any) {
      error.value = e.response?.data?.detail || "Failed to fetch blocks"
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
          notebookSlug(block.notebook_id),
          workspaceSlug(),
        )
        currentPageBlocks.value = result.children
      } else {
        // For leaf blocks, load content
        currentPageBlocks.value = []
        currentPageBlockId.value = null

        const blockDetail = await blockService.getBlock(
          block.block_id,
          notebookSlug(block.notebook_id),
          workspaceSlug(),
        )

        const isText = block.content_type?.startsWith("text/") ||
          ["application/json", "application/xml"].includes(block.content_type || "")

        let content = blockDetail.content || ""
        if (isText && !content) {
          try {
            const textResult = await blockService.getText(
              block.block_id,
              notebookSlug(block.notebook_id),
              workspaceSlug(),
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
   * Select a block by its path (resolves path to block via tree).
   */
  async function selectBlockByPath(blockPath: string, notebookId: number) {
    if (!currentWorkspace.value) return

    // Find the block in the tree
    const tree = blockTrees.value.get(notebookId) || []
    const node = findNode(tree, blockPath)
    if (node?.block) {
      await selectBlock(node.block)
    } else if (node?.block_id) {
      // Construct a minimal block to select
      const block: Block = {
        id: 0,
        block_id: node.block_id,
        parent_block_id: node.parent_block_id || null,
        notebook_id: notebookId,
        path: blockPath,
        block_type: (node.block_type as Block["block_type"]) || "page",
        content_format: "markdown",
        order_index: 0,
        title: node.title || node.pageMeta?.title,
        description: node.pageMeta?.description,
        properties: node.pageMeta?.properties,
        created_at: "",
        updated_at: "",
      }
      await selectBlock(block)
    } else {
      // Try resolving via API
      try {
        const resolved = await blockService.resolveLink(blockPath, notebookSlug(notebookId), workspaceSlug())
        await selectBlock(resolved)
      } catch {
        error.value = "Failed to find block"
      }
    }
  }

  /**
   * Save content for the current block.
   */
  async function saveBlock(content: string, properties?: Record<string, any>, keepEditing: boolean = false) {
    if (!currentWorkspace.value || !currentBlock.value) return

    if (!keepEditing) {
      blockLoading.value = true
    }
    error.value = null
    try {
      if (!currentBlock.value.notebook_id) {
        throw new Error("Block has no notebook_id")
      }
      const updated = await blockService.updateBlock(
        currentBlock.value.block_id,
        notebookSlug(currentBlock.value.notebook_id),
        workspaceSlug(),
        content,
      )
      if (properties) {
        await blockService.updateProperties(
          currentBlock.value.block_id,
          notebookSlug(currentBlock.value.notebook_id),
          workspaceSlug(),
          properties,
        )
      }
      currentBlock.value = { ...currentBlock.value, ...updated, content } as Block
    } catch (e: any) {
      error.value = e.response?.data?.detail || "Failed to save block"
      throw e
    } finally {
      if (!keepEditing) {
        blockLoading.value = false
      }
    }
  }

  async function createPage(
    notebookId: number,
    title: string,
    parentPath?: string,
    description?: string,
  ) {
    if (!currentWorkspace.value) return
    try {
      const result = await blockService.createPage(notebookSlug(notebookId), workspaceSlug(), {
        title,
        parent_path: parentPath,
        description,
      })
      await fetchBlockTree(notebookId)
      if (result.path) {
        await selectBlockByPath(result.path, notebookId)
      }
      return result
    } catch (e: any) {
      error.value = e.response?.data?.detail || "Failed to create page"
      throw e
    }
  }

  async function deleteBlock(
    notebookId: number,
    blockId: string,
    _parentBlockId?: string,
  ) {
    if (!currentWorkspace.value) return

    blockLoading.value = true
    error.value = null
    try {
      const result = await blockService.deleteBlock(blockId, notebookSlug(notebookId), workspaceSlug())

      // If the deleted block is the current block, clear selection
      if (currentBlock.value?.block_id === blockId) {
        const blockPath = currentBlock.value.path
        currentBlock.value = null
        currentPageBlocks.value = []
        currentPageBlockId.value = null

        const tree = blockTrees.value.get(notebookId)
        if (tree) {
          removeNode(tree, blockPath)
        }
      } else if (result.blocks) {
        // Update page blocks if we're deleting a child block
        currentPageBlocks.value = result.blocks
      }
    } catch (e: any) {
      error.value = e.response?.data?.detail || "Failed to delete block"
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
    const tree = blockTrees.value.get(event.notebook_id)
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

  function getBlocksForNotebook(notebookId: number): Block[] {
    return allBlocks.value.get(notebookId) || []
  }

  async function uploadBlock(notebookId: number, file: File, _path?: string) {
    if (!currentWorkspace.value) return

    blockLoading.value = true
    error.value = null
    try {
      const newBlock = await blockService.upload(notebookSlug(notebookId), workspaceSlug(), file)
      await fetchBlockTree(notebookId)
      return newBlock
    } catch (e: any) {
      error.value = e.response?.data?.detail || "Failed to upload file"
      throw e
    } finally {
      blockLoading.value = false
    }
  }

  async function moveBlock(blockId: string, notebookId: number, _newPath: string) {
    if (!currentWorkspace.value) return

    blockLoading.value = true
    error.value = null
    try {
      const movedBlock = await blockService.moveBlock(
        blockId,
        notebookSlug(notebookId),
        workspaceSlug(),
        {},
      )
      await fetchBlockTree(notebookId)

      if (currentBlock.value?.block_id === blockId) {
        currentBlock.value = { ...currentBlock.value, ...movedBlock } as Block
      }
      return movedBlock
    } catch (e: any) {
      error.value = e.response?.data?.detail || "Failed to move block"
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
        notebookSlug(notebookId),
        workspaceSlug(),
      )
      currentPageBlocks.value = result.children
    } catch (e: any) {
      error.value = e.response?.data?.detail || "Failed to fetch page blocks"
    } finally {
      blockLoading.value = false
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
      const result = await blockService.createBlock(notebookSlug(notebookId), workspaceSlug(), {
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
      const result = await blockService.reorderBlocks(pageBlockId, notebookSlug(notebookId), workspaceSlug(), blockIds)
      if (result.blocks) {
        currentPageBlocks.value = result.blocks
      }
    } catch (e: any) {
      error.value = e.response?.data?.detail || "Failed to reorder blocks"
    }
  }

  /**
   * Import a markdown file as a page of blocks
   */
  async function importMarkdown(notebookId: number, file: File) {
    if (!currentWorkspace.value) return
    try {
      const result = await blockService.importMarkdown(notebookSlug(notebookId), workspaceSlug(), file)
      await fetchBlockTree(notebookId)
      return result
    } catch (e: any) {
      error.value = e.response?.data?.detail || "Failed to import markdown"
      throw e
    }
  }

  /**
   * Save properties for the current page block
   */
  async function saveBlockProperties(properties: Record<string, any>) {
    if (!currentWorkspace.value || !currentBlock.value) return

    blockLoading.value = true
    error.value = null
    try {
      const updated = await blockService.updateProperties(
        currentBlock.value.block_id,
        notebookSlug(currentBlock.value.notebook_id),
        workspaceSlug(),
        properties,
      )

      currentBlock.value = { ...currentBlock.value, ...updated } as Block

      // Refresh tree to pick up changes
      await fetchBlockTree(currentBlock.value.notebook_id)
    } catch (e: any) {
      error.value = e.response?.data?.detail || "Failed to save block properties"
      throw e
    } finally {
      blockLoading.value = false
    }
  }

  /**
   * Get the block tree for a notebook
   */
  function getBlockTree(notebookId: number): BlockTreeNode[] {
    return blockTrees.value.get(notebookId) || []
  }

  return {
    // Workspace state
    workspaces,
    currentWorkspace,
    notebooks,
    loading,
    error,
    // Block state
    blockTrees,
    allBlocks,
    currentNotebook,
    currentBlock,
    currentLeafBlock,
    currentPageBlock,
    isPage,
    expandedNotebooks,
    blockLoading,
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
    selectBlockByPath,
    saveBlock,
    deleteBlock,
    uploadBlock,
    moveBlock,
    toggleNotebookExpansion,
    getBlocksForNotebook,
    getBlockTree,
    // Page actions
    saveBlockProperties,
    fetchPageBlocks,
    createPage,
    createBlock,
    reorderBlocks,
    importMarkdown,
  }
})
