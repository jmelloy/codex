import { describe, it, expect, beforeEach, vi } from "vitest"
import { setActivePinia, createPinia } from "pinia"
import { useWorkspaceStore } from "../../stores/workspace"
import {
  workspaceService,
  notebookService,
  blockService,
} from "../../services/codex"

vi.mock("../../services/codex", () => ({
  workspaceService: {
    list: vi.fn(),
    create: vi.fn(),
  },
  notebookService: {
    list: vi.fn(),
    create: vi.fn(),
  },
  blockService: {
    getTree: vi.fn(),
    getBlock: vi.fn(),
    getText: vi.fn(),
    getChildren: vi.fn(),
    updateBlock: vi.fn(),
    updateProperties: vi.fn(),
    deleteBlock: vi.fn(),
    upload: vi.fn(),
    moveBlock: vi.fn(),
    createPage: vi.fn(),
    resolveLink: vi.fn(),
  },
}))

describe("Workspace Store", () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  describe("initial state", () => {
    it("has correct default values", () => {
      const store = useWorkspaceStore()

      expect(store.workspaces).toEqual([])
      expect(store.currentWorkspace).toBeNull()
      expect(store.notebooks).toEqual([])
      expect(store.loading).toBe(false)
      expect(store.error).toBeNull()
      expect(store.currentBlock).toBeNull()
      expect(store.currentLeafBlock).toBeNull()
      expect(store.currentPageBlock).toBeNull()
      expect(store.blockLoading).toBe(false)
    })
  })

  describe("fetchWorkspaces", () => {
    it("fetches and stores workspaces", async () => {
      const mockWorkspaces = [
        { id: 1, name: "Workspace 1", path: "/path1", owner_id: 1 },
        { id: 2, name: "Workspace 2", path: "/path2", owner_id: 1 },
      ]
      vi.mocked(workspaceService.list).mockResolvedValue(mockWorkspaces as any)

      const store = useWorkspaceStore()
      await store.fetchWorkspaces()

      expect(store.workspaces).toEqual(mockWorkspaces)
      expect(store.loading).toBe(false)
      expect(store.error).toBeNull()
    })

    it("sets loading state during fetch", async () => {
      vi.mocked(workspaceService.list).mockImplementation(async () => {
        return []
      })

      const store = useWorkspaceStore()
      const promise = store.fetchWorkspaces()

      expect(store.loading).toBe(true)

      await promise

      expect(store.loading).toBe(false)
    })

    it("handles fetch error", async () => {
      vi.mocked(workspaceService.list).mockRejectedValue({
        response: { data: { detail: "Fetch failed" } },
      })

      const store = useWorkspaceStore()
      await store.fetchWorkspaces()

      expect(store.error).toBe("Fetch failed")
      expect(store.loading).toBe(false)
    })

    it("handles generic fetch error", async () => {
      vi.mocked(workspaceService.list).mockRejectedValue(new Error("Network error"))

      const store = useWorkspaceStore()
      await store.fetchWorkspaces()

      expect(store.error).toBe("Failed to fetch workspaces")
    })
  })

  describe("fetchNotebooks", () => {
    it("fetches notebooks for a workspace", async () => {
      const mockNotebooks = [
        { id: 1, name: "Notebook 1" },
        { id: 2, name: "Notebook 2" },
      ]
      vi.mocked(notebookService.list).mockResolvedValue(mockNotebooks as any)

      const store = useWorkspaceStore()
      store.currentWorkspace = { id: 1, slug: "ws-1" } as any
      await store.fetchNotebooks(1)

      expect(notebookService.list).toHaveBeenCalledWith("ws-1")
      expect(store.notebooks).toEqual(mockNotebooks)
    })

    it("handles fetch error", async () => {
      vi.mocked(notebookService.list).mockRejectedValue({
        response: { data: { detail: "Not found" } },
      })

      const store = useWorkspaceStore()
      store.currentWorkspace = { id: 1, slug: "ws-1" } as any
      await store.fetchNotebooks(1)

      expect(store.error).toBe("Not found")
    })
  })

  describe("createWorkspace", () => {
    it("creates and adds workspace to list", async () => {
      const newWorkspace = { id: 1, name: "New Workspace", path: "/new", owner_id: 1 }
      vi.mocked(workspaceService.create).mockResolvedValue(newWorkspace as any)

      const store = useWorkspaceStore()
      const result = await store.createWorkspace("New Workspace")

      expect(workspaceService.create).toHaveBeenCalledWith("New Workspace")
      expect(store.workspaces).toContainEqual(newWorkspace)
      expect(result).toEqual(newWorkspace)
    })

    it("handles creation error", async () => {
      vi.mocked(workspaceService.create).mockRejectedValue({
        response: { data: { detail: "Name already exists" } },
      })

      const store = useWorkspaceStore()

      await expect(store.createWorkspace("Duplicate")).rejects.toBeDefined()
      expect(store.error).toBe("Name already exists")
    })
  })

  describe("createNotebook", () => {
    it("creates and adds notebook to list", async () => {
      const newNotebook = { id: 1, name: "New Notebook" }
      vi.mocked(notebookService.create).mockResolvedValue(newNotebook as any)

      const store = useWorkspaceStore()
      store.currentWorkspace = { id: 1, slug: "ws-1" } as any
      const result = await store.createNotebook(1, "New Notebook")

      expect(notebookService.create).toHaveBeenCalledWith("ws-1", "New Notebook")
      expect(store.notebooks).toContainEqual(newNotebook)
      expect(result).toEqual(newNotebook)
    })
  })

  describe("setCurrentWorkspace", () => {
    it("sets current workspace and fetches notebooks", async () => {
      const workspace = { id: 1, slug: "workspace-1", name: "Workspace 1", path: "/path1", owner_id: 1 }
      vi.mocked(notebookService.list).mockResolvedValue([])

      const store = useWorkspaceStore()
      store.setCurrentWorkspace(workspace as any)

      expect(store.currentWorkspace).toEqual(workspace)
      expect(notebookService.list).toHaveBeenCalledWith("workspace-1")
    })

    it("clears state when setting workspace to null", () => {
      const store = useWorkspaceStore()

      store.currentWorkspace = { id: 1, slug: "ws-1" } as any
      store.currentBlock = { id: 1, block_type: "file" } as any

      store.setCurrentWorkspace(null)

      expect(store.currentWorkspace).toBeNull()
      expect(store.currentBlock).toBeNull()
    })
  })

  describe("fetchBlockTree", () => {
    it("fetches block tree", async () => {
      const mockTree = { tree: [], notebook_id: 1, workspace_id: 1 }
      vi.mocked(blockService.getTree).mockResolvedValue(mockTree as any)

      const store = useWorkspaceStore()
      store.currentWorkspace = { id: 1, slug: "ws-1" } as any
      store.notebooks = [{ id: 1, slug: "nb-1", name: "Notebook" }] as any

      await store.fetchBlockTree(1)

      expect(blockService.getTree).toHaveBeenCalledWith("nb-1", "ws-1")
      expect(store.blockTrees.has(1)).toBe(true)
    })

    it("does nothing without current workspace", async () => {
      const store = useWorkspaceStore()
      await store.fetchBlockTree(1)

      expect(blockService.getTree).not.toHaveBeenCalled()
    })
  })

  describe("selectBlock", () => {
    it("loads leaf block content", async () => {
      const mockBlock = {
        id: 1,
        block_id: "blk_1",
        parent_block_id: null,
        notebook_id: 1,
        path: "test.md",
        block_type: "file",
        content_format: "markdown",
        order_index: 0,
        content_type: "text/markdown",
        content: "# Test",
        size: 100,
        created_at: "2024-01-01",
        updated_at: "2024-01-01",
      }

      vi.mocked(blockService.getBlock).mockResolvedValue(mockBlock as any)

      const store = useWorkspaceStore()
      store.currentWorkspace = { id: 1, slug: "ws-1" } as any
      store.notebooks = [{ id: 1, slug: "nb-1", name: "Notebook" }] as any

      await store.selectBlock(mockBlock as any)

      expect(blockService.getBlock).toHaveBeenCalledWith("blk_1", "nb-1", "ws-1")
      expect(store.currentBlock?.block_id).toBe("blk_1")
      expect(store.currentLeafBlock?.content).toBe("# Test")
      expect(store.currentPageBlock).toBeNull()
    })

    it("loads page children", async () => {
      const mockPage = {
        id: 2,
        block_id: "page_1",
        parent_block_id: null,
        notebook_id: 1,
        path: "my-page",
        block_type: "page",
        content_format: "markdown",
        order_index: 0,
        title: "My Page",
        created_at: "2024-01-01",
        updated_at: "2024-01-01",
      }

      const mockChildren = {
        parent_block_id: "page_1",
        children: [{ id: 3, block_id: "child_1", block_type: "text" }],
      }

      vi.mocked(blockService.getChildren).mockResolvedValue(mockChildren as any)

      const store = useWorkspaceStore()
      store.currentWorkspace = { id: 1, slug: "ws-1" } as any
      store.notebooks = [{ id: 1, slug: "nb-1", name: "Notebook" }] as any

      await store.selectBlock(mockPage as any)

      expect(blockService.getChildren).toHaveBeenCalledWith("page_1", "nb-1", "ws-1")
      expect(store.currentBlock?.block_type).toBe("page")
      expect(store.currentLeafBlock).toBeNull()
      expect(store.currentPageBlock).not.toBeNull()
      expect(store.currentPageBlock?.is_page).toBe(true)
      expect(store.currentPageBlocks).toHaveLength(1)
    })
  })

  describe("saveBlock", () => {
    it("updates block content via blockService", async () => {
      const mockUpdated = { id: 1, block_id: "blk_1", path: "test.md" }
      vi.mocked(blockService.updateBlock).mockResolvedValue(mockUpdated as any)
      vi.mocked(blockService.updateProperties).mockResolvedValue(mockUpdated as any)

      const store = useWorkspaceStore()
      store.currentWorkspace = { id: 1, slug: "ws-1" } as any
      store.notebooks = [{ id: 1, slug: "nb-1", name: "Notebook" }] as any
      store.currentBlock = { id: 1, block_id: "blk_1", notebook_id: 1, block_type: "file", content: "old" } as any

      await store.saveBlock("new content", { key: "value" })

      expect(blockService.updateBlock).toHaveBeenCalledWith("blk_1", "nb-1", "ws-1", "new content")
      expect(blockService.updateProperties).toHaveBeenCalledWith("blk_1", "nb-1", "ws-1", { key: "value" })
    })

    it("throws error when block has no notebook_id", async () => {
      const store = useWorkspaceStore()
      store.currentWorkspace = { id: 1, slug: "ws-1" } as any
      store.currentBlock = { id: 1, block_id: "blk_1", notebook_id: undefined } as any

      await expect(store.saveBlock("content")).rejects.toThrow("Block has no notebook_id")
    })
  })

  describe("createPage", () => {
    it("creates page via blockService", async () => {
      const mockPage = { block_id: "blk_1", path: "new-page" }
      const mockTree = { tree: [], notebook_id: 1, workspace_id: 1 }

      vi.mocked(blockService.createPage).mockResolvedValue(mockPage as any)
      vi.mocked(blockService.getTree).mockResolvedValue(mockTree as any)
      vi.mocked(blockService.resolveLink).mockRejectedValue(new Error("not found"))

      const store = useWorkspaceStore()
      store.currentWorkspace = { id: 1, slug: "ws-1" } as any
      store.notebooks = [{ id: 1, slug: "nb-1", name: "Notebook" }] as any

      const result = await store.createPage(1, "New Page")

      expect(blockService.createPage).toHaveBeenCalledWith("nb-1", "ws-1", { title: "New Page" })
    })
  })

  describe("deleteBlock", () => {
    it("deletes block via blockService and clears current block", async () => {
      vi.mocked(blockService.deleteBlock).mockResolvedValue({ message: "deleted" } as any)

      const store = useWorkspaceStore()
      store.currentWorkspace = { id: 1, slug: "ws-1" } as any
      store.notebooks = [{ id: 1, slug: "nb-1", name: "Notebook" }] as any
      store.currentBlock = { id: 1, block_id: "blk_1", notebook_id: 1, path: "test.md", block_type: "file" } as any
      store.blockTrees.set(1, [{ name: "test.md", path: "test.md", type: "leaf" as const }])

      await store.deleteBlock(1, "blk_1")

      expect(blockService.deleteBlock).toHaveBeenCalledWith("blk_1", "nb-1", "ws-1")
      expect(store.currentBlock).toBeNull()
    })
  })

  describe("uploadBlock", () => {
    it("uploads block via blockService", async () => {
      const mockBlock = { id: 1, block_id: "blk_1", path: "upload.png" }
      const mockTree = { tree: [], notebook_id: 1, workspace_id: 1 }
      vi.mocked(blockService.upload).mockResolvedValue(mockBlock as any)
      vi.mocked(blockService.getTree).mockResolvedValue(mockTree as any)

      const store = useWorkspaceStore()
      store.currentWorkspace = { id: 1, slug: "ws-1" } as any
      store.notebooks = [{ id: 1, slug: "nb-1", name: "Notebook" }] as any

      const file = new File(["content"], "upload.png", { type: "image/png" })
      const result = await store.uploadBlock(1, file, "images/upload.png")

      expect(blockService.upload).toHaveBeenCalledWith("nb-1", "ws-1", file)
    })
  })

  describe("moveBlock", () => {
    it("moves block via blockService", async () => {
      const movedBlock = { id: 1, block_id: "blk_1", path: "new/path.md" }
      const mockTree = { tree: [], notebook_id: 1, workspace_id: 1 }
      vi.mocked(blockService.moveBlock).mockResolvedValue(movedBlock as any)
      vi.mocked(blockService.getTree).mockResolvedValue(mockTree as any)

      const store = useWorkspaceStore()
      store.currentWorkspace = { id: 1, slug: "ws-1" } as any
      store.notebooks = [{ id: 1, slug: "nb-1", name: "Notebook" }] as any
      store.blockTrees.set(1, [])

      const result = await store.moveBlock("blk_1", 1, "new/path.md")

      expect(blockService.moveBlock).toHaveBeenCalledWith("blk_1", "nb-1", "ws-1", {})
    })
  })

  describe("toggleNotebookExpansion", () => {
    it("expands notebook and fetches block tree", async () => {
      const mockTree = { tree: [], notebook_id: 1, workspace_id: 1 }
      vi.mocked(blockService.getTree).mockResolvedValue(mockTree as any)

      const store = useWorkspaceStore()
      store.currentWorkspace = { id: 1, slug: "ws-1" } as any
      const notebook = { id: 1, slug: "nb-1", name: "Notebook" } as any
      store.notebooks = [notebook]

      store.toggleNotebookExpansion(notebook)

      expect(store.expandedNotebooks.has(1)).toBe(true)
      expect(store.currentNotebook).toEqual(notebook)
      expect(blockService.getTree).toHaveBeenCalledWith("nb-1", "ws-1")
    })

    it("collapses expanded notebook", () => {
      const store = useWorkspaceStore()
      store.expandedNotebooks.add(1)
      const notebook = { id: 1, name: "Notebook" } as any

      store.toggleNotebookExpansion(notebook)

      expect(store.expandedNotebooks.has(1)).toBe(false)
    })
  })

  describe("getBlocksForNotebook", () => {
    it("returns flat block list from tree", () => {
      const store = useWorkspaceStore()
      store.blockTrees.set(1, [
        { name: "block1.md", path: "block1.md", type: "leaf", leafBlock: { id: 1, path: "block1.md" } as any },
        {
          name: "page",
          path: "page",
          type: "page",
          children: [
            { name: "block2.md", path: "page/block2.md", type: "leaf", leafBlock: { id: 2, path: "page/block2.md" } as any },
          ],
        },
      ])

      const blocks = store.getBlocksForNotebook(1)

      expect(blocks).toHaveLength(2)
      expect(blocks.map((b) => b.path)).toContain("block1.md")
      expect(blocks.map((b) => b.path)).toContain("page/block2.md")
    })

    it("returns empty array for unknown notebook", () => {
      const store = useWorkspaceStore()
      const blocks = store.getBlocksForNotebook(999)

      expect(blocks).toEqual([])
    })
  })

  describe("getBlockTree", () => {
    it("returns block tree for notebook", () => {
      const mockTree = [{ name: "block.md", path: "block.md", type: "leaf" as const }]

      const store = useWorkspaceStore()
      store.blockTrees.set(1, mockTree)

      const tree = store.getBlockTree(1)

      expect(tree).toEqual(mockTree)
    })

    it("returns empty array for unknown notebook", () => {
      const store = useWorkspaceStore()
      const tree = store.getBlockTree(999)

      expect(tree).toEqual([])
    })
  })

  describe("deleteBlock (page)", () => {
    it("deletes page block and clears state", async () => {
      vi.mocked(blockService.deleteBlock).mockResolvedValue({ message: "deleted" } as any)

      const store = useWorkspaceStore()
      store.currentWorkspace = { id: 1, slug: "ws-1" } as any
      store.notebooks = [{ id: 1, slug: "nb-1", name: "Notebook" }] as any
      store.currentBlock = { id: 1, block_id: "page_1", notebook_id: 1, path: "page", block_type: "page" } as any
      store.blockTrees.set(1, [{ name: "page", path: "page", type: "page" }])

      await store.deleteBlock(1, "page_1")

      expect(blockService.deleteBlock).toHaveBeenCalledWith("page_1", "nb-1", "ws-1")
      expect(store.currentBlock).toBeNull()
    })
  })
})
