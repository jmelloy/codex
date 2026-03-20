import { describe, it, expect, beforeEach, vi } from "vitest"
import { setActivePinia, createPinia } from "pinia"
import { useWorkspaceStore } from "../../stores/workspace"
import {
  workspaceService,
  notebookService,
  blockService,
  folderService,
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
    updateBlock: vi.fn(),
    updateProperties: vi.fn(),
    deleteBlock: vi.fn(),
    upload: vi.fn(),
    moveBlock: vi.fn(),
    createPage: vi.fn(),
    getChildren: vi.fn(),
  },
  folderService: {
    get: vi.fn(),
    updateProperties: vi.fn(),
    delete: vi.fn(),
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
      expect(store.currentFile).toBeNull()
      expect(store.currentFolder).toBeNull()
      expect(store.fileLoading).toBe(false)
      expect(store.folderLoading).toBe(false)
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

      // Loading should be true during fetch
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
      await store.fetchNotebooks(1)

      expect(notebookService.list).toHaveBeenCalledWith(1)
      expect(store.notebooks).toEqual(mockNotebooks)
    })

    it("handles fetch error", async () => {
      vi.mocked(notebookService.list).mockRejectedValue({
        response: { data: { detail: "Not found" } },
      })

      const store = useWorkspaceStore()
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
      const result = await store.createNotebook(1, "New Notebook")

      expect(notebookService.create).toHaveBeenCalledWith(1, "New Notebook")
      expect(store.notebooks).toContainEqual(newNotebook)
      expect(result).toEqual(newNotebook)
    })
  })

  describe("setCurrentWorkspace", () => {
    it("sets current workspace and fetches notebooks", async () => {
      const workspace = { id: 1, name: "Workspace 1", path: "/path1", owner_id: 1 }
      vi.mocked(notebookService.list).mockResolvedValue([])

      const store = useWorkspaceStore()
      store.setCurrentWorkspace(workspace as any)

      expect(store.currentWorkspace).toEqual(workspace)
      expect(notebookService.list).toHaveBeenCalledWith(1)
    })

    it("clears state when setting workspace to null", () => {
      const store = useWorkspaceStore()

      // Set some initial state
      store.currentWorkspace = { id: 1 } as any
      store.currentFile = { id: 1 } as any
      store.currentFolder = { path: "folder" } as any

      store.setCurrentWorkspace(null)

      expect(store.currentWorkspace).toBeNull()
      expect(store.currentFile).toBeNull()
      expect(store.currentFolder).toBeNull()
    })
  })

  describe("fetchFiles", () => {
    it("fetches block tree", async () => {
      const mockTree = { tree: [], notebook_id: 1, workspace_id: 1 }
      vi.mocked(blockService.getTree).mockResolvedValue(mockTree as any)

      const store = useWorkspaceStore()
      store.currentWorkspace = { id: 1 } as any

      await store.fetchFiles(1)

      expect(blockService.getTree).toHaveBeenCalledWith(1, 1)
      expect(store.fileTrees.has(1)).toBe(true)
    })

    it("does nothing without current workspace", async () => {
      const store = useWorkspaceStore()
      await store.fetchFiles(1)

      expect(blockService.getTree).not.toHaveBeenCalled()
    })
  })

  describe("selectFile", () => {
    it("fetches and sets current file", async () => {
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
      store.currentWorkspace = { id: 1 } as any

      await store.selectFile(mockBlock as any)

      expect(blockService.getBlock).toHaveBeenCalledWith("blk_1", 1, 1)
      expect(store.currentFile?.content).toBe("# Test")
      expect(store.currentFolder).toBeNull()
    })
  })

  describe("saveFile", () => {
    it("updates file content via blockService", async () => {
      const mockUpdated = { id: 1, block_id: "blk_1", path: "test.md" }
      vi.mocked(blockService.updateBlock).mockResolvedValue(mockUpdated as any)
      vi.mocked(blockService.updateProperties).mockResolvedValue(mockUpdated as any)

      const store = useWorkspaceStore()
      store.currentWorkspace = { id: 1 } as any
      store.currentFile = { id: 1, block_id: "blk_1", notebook_id: 1, content: "old" } as any
      store.fileTrees.set(1, [])

      await store.saveFile("new content", { key: "value" })

      expect(blockService.updateBlock).toHaveBeenCalledWith("blk_1", 1, 1, "new content")
      expect(blockService.updateProperties).toHaveBeenCalledWith("blk_1", 1, 1, { key: "value" })
    })

    it("throws error when file has no notebook_id", async () => {
      const store = useWorkspaceStore()
      store.currentWorkspace = { id: 1 } as any
      store.currentFile = { id: 1, block_id: "blk_1", notebook_id: undefined } as any

      await expect(store.saveFile("content")).rejects.toThrow("File has no notebook_id")
    })
  })

  describe("createFile", () => {
    it("creates file via blockService", async () => {
      const mockPage = { block_id: "blk_1", path: "new.md" }
      const mockTree = { tree: [], notebook_id: 1, workspace_id: 1 }

      vi.mocked(blockService.createPage).mockResolvedValue(mockPage as any)
      vi.mocked(blockService.getTree).mockResolvedValue(mockTree as any)
      vi.mocked(folderService.get).mockResolvedValue({
        path: "new.md", name: "new.md", notebook_id: 1, file_count: 0, files: [], subfolders: [],
      } as any)

      const store = useWorkspaceStore()
      store.currentWorkspace = { id: 1 } as any

      const result = await store.createFile(1, "new.md", "# New File")

      expect(blockService.createPage).toHaveBeenCalledWith(1, 1, { title: "new.md" })
    })
  })

  describe("deleteFile", () => {
    it("deletes file via blockService and clears current file", async () => {
      vi.mocked(blockService.deleteBlock).mockResolvedValue({ message: "deleted" } as any)

      const store = useWorkspaceStore()
      store.currentWorkspace = { id: 1 } as any
      store.currentFile = { id: 1, block_id: "blk_1", notebook_id: 1, path: "test.md", content: "" } as any
      store.fileTrees.set(1, [{ name: "test.md", path: "test.md", type: "file" }])

      await store.deleteFile("blk_1")

      expect(blockService.deleteBlock).toHaveBeenCalledWith("blk_1", 1, 1)
      expect(store.currentFile).toBeNull()
    })
  })

  describe("uploadFile", () => {
    it("uploads file via blockService", async () => {
      const mockBlock = { id: 1, block_id: "blk_1", path: "upload.png" }
      const mockTree = { tree: [], notebook_id: 1, workspace_id: 1 }
      vi.mocked(blockService.upload).mockResolvedValue(mockBlock as any)
      vi.mocked(blockService.getTree).mockResolvedValue(mockTree as any)

      const store = useWorkspaceStore()
      store.currentWorkspace = { id: 1 } as any

      const file = new File(["content"], "upload.png", { type: "image/png" })
      const result = await store.uploadFile(1, file, "images/upload.png")

      expect(blockService.upload).toHaveBeenCalledWith(1, 1, file)
    })
  })

  describe("moveFile", () => {
    it("moves file via blockService", async () => {
      const movedBlock = { id: 1, block_id: "blk_1", path: "new/path.md" }
      const mockTree = { tree: [], notebook_id: 1, workspace_id: 1 }
      vi.mocked(blockService.moveBlock).mockResolvedValue(movedBlock as any)
      vi.mocked(blockService.getTree).mockResolvedValue(mockTree as any)

      const store = useWorkspaceStore()
      store.currentWorkspace = { id: 1 } as any
      store.fileTrees.set(1, [])

      const result = await store.moveFile("blk_1", 1, "new/path.md")

      expect(blockService.moveBlock).toHaveBeenCalledWith("blk_1", 1, 1, {})
    })
  })

  describe("toggleNotebookExpansion", () => {
    it("expands notebook and fetches block tree", async () => {
      const mockTree = { tree: [], notebook_id: 1, workspace_id: 1 }
      vi.mocked(blockService.getTree).mockResolvedValue(mockTree as any)

      const store = useWorkspaceStore()
      store.currentWorkspace = { id: 1 } as any
      const notebook = { id: 1, name: "Notebook" } as any
      store.notebooks = [notebook]

      store.toggleNotebookExpansion(notebook)

      expect(store.expandedNotebooks.has(1)).toBe(true)
      expect(store.currentNotebook).toEqual(notebook)
      expect(blockService.getTree).toHaveBeenCalledWith(1, 1)
    })

    it("collapses expanded notebook", () => {
      const store = useWorkspaceStore()
      store.expandedNotebooks.add(1)
      const notebook = { id: 1, name: "Notebook" } as any

      store.toggleNotebookExpansion(notebook)

      expect(store.expandedNotebooks.has(1)).toBe(false)
    })
  })

  describe("getFilesForNotebook", () => {
    it("returns flat file list from tree", () => {
      const store = useWorkspaceStore()
      store.fileTrees.set(1, [
        { name: "file1.md", path: "file1.md", type: "file", file: { id: 1, path: "file1.md" } as any },
        {
          name: "folder",
          path: "folder",
          type: "folder",
          children: [
            { name: "file2.md", path: "folder/file2.md", type: "file", file: { id: 2, path: "folder/file2.md" } as any },
          ],
        },
      ])

      const files = store.getFilesForNotebook(1)

      expect(files).toHaveLength(2)
      expect(files.map((f) => f.path)).toContain("file1.md")
      expect(files.map((f) => f.path)).toContain("folder/file2.md")
    })

    it("returns empty array for unknown notebook", () => {
      const store = useWorkspaceStore()
      const files = store.getFilesForNotebook(999)

      expect(files).toEqual([])
    })
  })

  describe("getFileTree", () => {
    it("returns file tree for notebook", () => {
      const mockTree = [{ name: "file.md", path: "file.md", type: "file" as const }]

      const store = useWorkspaceStore()
      store.fileTrees.set(1, mockTree)

      const tree = store.getFileTree(1)

      expect(tree).toEqual(mockTree)
    })

    it("returns empty array for unknown notebook", () => {
      const store = useWorkspaceStore()
      const tree = store.getFileTree(999)

      expect(tree).toEqual([])
    })
  })

  describe("folder operations", () => {
    describe("selectFolder", () => {
      it("selects folder and clears current file", async () => {
        const mockFolder = {
          path: "test-folder",
          name: "test-folder",
          notebook_id: 1,
          files: [],
          subfolders: [],
          file_count: 0,
        }
        vi.mocked(folderService.get).mockResolvedValue(mockFolder as any)

        const store = useWorkspaceStore()
        store.currentWorkspace = { id: 1 } as any
        store.currentFile = { id: 1 } as any

        await store.selectFolder("test-folder", 1)

        expect(store.currentFile).toBeNull()
        expect(store.currentFolder).toEqual(mockFolder)
      })
    })

    describe("saveFolderProperties", () => {
      it("updates folder properties", async () => {
        const updatedFolder = { path: "folder", title: "New Title", notebook_id: 1 }
        vi.mocked(folderService.updateProperties).mockResolvedValue(updatedFolder as any)

        const store = useWorkspaceStore()
        store.currentWorkspace = { id: 1 } as any
        store.currentFolder = { path: "folder", notebook_id: 1, file_count: 0 } as any
        store.fileTrees.set(1, [])

        await store.saveFolderProperties({ title: "New Title" })

        expect(folderService.updateProperties).toHaveBeenCalledWith("folder", 1, 1, {
          title: "New Title",
        })
      })
    })

    describe("deleteFolder", () => {
      it("deletes folder and clears current folder", async () => {
        vi.mocked(folderService.delete).mockResolvedValue(undefined)

        const store = useWorkspaceStore()
        store.currentWorkspace = { id: 1 } as any
        store.currentFolder = { path: "folder", notebook_id: 1, file_count: 0 } as any
        store.fileTrees.set(1, [{ name: "folder", path: "folder", type: "folder" }])

        await store.deleteFolder()

        expect(folderService.delete).toHaveBeenCalledWith("folder", 1, 1)
        expect(store.currentFolder).toBeNull()
      })
    })

    describe("clearFolderSelection", () => {
      it("clears current folder", () => {
        const store = useWorkspaceStore()
        store.currentFolder = { path: "folder" } as any

        store.clearFolderSelection()

        expect(store.currentFolder).toBeNull()
      })
    })
  })
})
