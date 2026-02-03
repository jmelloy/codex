import { describe, it, expect, beforeEach, vi } from "vitest"
import { setActivePinia, createPinia } from "pinia"
import { useWorkspaceStore } from "../../stores/workspace"
import {
  workspaceService,
  notebookService,
  fileService,
  folderService,
} from "../../services/codex"

// Mock the services
vi.mock("../../services/codex", () => ({
  workspaceService: {
    list: vi.fn(),
    create: vi.fn(),
  },
  notebookService: {
    list: vi.fn(),
    create: vi.fn(),
  },
  fileService: {
    list: vi.fn(),
    get: vi.fn(),
    getContent: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
    delete: vi.fn(),
    upload: vi.fn(),
    move: vi.fn(),
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
      expect(store.isEditing).toBe(false)
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
      expect(store.isEditing).toBe(false)
    })
  })

  describe("fetchFiles", () => {
    it("fetches files and builds tree", async () => {
      const mockFiles = [
        { id: 1, path: "file1.md", filename: "file1.md" },
        { id: 2, path: "folder/file2.md", filename: "file2.md" },
      ]
      vi.mocked(fileService.list).mockResolvedValue(mockFiles as any)

      const store = useWorkspaceStore()
      store.currentWorkspace = { id: 1 } as any

      await store.fetchFiles(1)

      expect(fileService.list).toHaveBeenCalledWith(1, 1)
      expect(store.fileTrees.has(1)).toBe(true)
    })

    it("does nothing without current workspace", async () => {
      const store = useWorkspaceStore()
      await store.fetchFiles(1)

      expect(fileService.list).not.toHaveBeenCalled()
    })
  })

  describe("selectFile", () => {
    it("fetches and sets current file", async () => {
      const mockFile = {
        id: 1,
        notebook_id: 1,
        path: "test.md",
        filename: "test.md",
        content_type: "text/markdown",
        size: 100,
      }
      const mockContent = { id: 1, content: "# Test", properties: {} }

      vi.mocked(fileService.get).mockResolvedValue(mockFile as any)
      vi.mocked(fileService.getContent).mockResolvedValue(mockContent as any)

      const store = useWorkspaceStore()
      store.currentWorkspace = { id: 1 } as any

      await store.selectFile(mockFile as any)

      expect(fileService.get).toHaveBeenCalledWith(1, 1, 1)
      expect(fileService.getContent).toHaveBeenCalledWith(1, 1, 1)
      expect(store.currentFile?.content).toBe("# Test")
      expect(store.currentFolder).toBeNull()
    })

    it("does not fetch content for non-text files", async () => {
      const mockFile = {
        id: 1,
        notebook_id: 1,
        path: "image.png",
        filename: "image.png",
        content_type: "image/png",
        size: 1000,
      }

      vi.mocked(fileService.get).mockResolvedValue(mockFile as any)

      const store = useWorkspaceStore()
      store.currentWorkspace = { id: 1 } as any

      await store.selectFile(mockFile as any)

      expect(fileService.get).toHaveBeenCalled()
      expect(fileService.getContent).not.toHaveBeenCalled()
    })

    it("fetches content for JSON files", async () => {
      const mockFile = {
        id: 1,
        notebook_id: 1,
        path: "data.json",
        filename: "data.json",
        content_type: "application/json",
        size: 50,
      }
      const mockContent = { id: 1, content: "{}" }

      vi.mocked(fileService.get).mockResolvedValue(mockFile as any)
      vi.mocked(fileService.getContent).mockResolvedValue(mockContent as any)

      const store = useWorkspaceStore()
      store.currentWorkspace = { id: 1 } as any

      await store.selectFile(mockFile as any)

      expect(fileService.getContent).toHaveBeenCalled()
    })

    it("fetches content for codex view files", async () => {
      const mockFile = {
        id: 1,
        notebook_id: 1,
        path: "view.cdx",
        filename: "view.cdx",
        content_type: "application/x-codex-view",
        size: 200,
      }
      const mockContent = { id: 1, content: "---\ntype: gallery\n---" }

      vi.mocked(fileService.get).mockResolvedValue(mockFile as any)
      vi.mocked(fileService.getContent).mockResolvedValue(mockContent as any)

      const store = useWorkspaceStore()
      store.currentWorkspace = { id: 1 } as any

      await store.selectFile(mockFile as any)

      expect(fileService.getContent).toHaveBeenCalled()
    })
  })

  describe("saveFile", () => {
    it("updates file content", async () => {
      const mockUpdated = { id: 1, path: "test.md", filename: "test.md" }
      vi.mocked(fileService.update).mockResolvedValue(mockUpdated as any)

      const store = useWorkspaceStore()
      store.currentWorkspace = { id: 1 } as any
      store.currentFile = { id: 1, notebook_id: 1, content: "old" } as any
      store.fileTrees.set(1, [])

      await store.saveFile("new content", { key: "value" })

      expect(fileService.update).toHaveBeenCalledWith(1, 1, 1, "new content", { key: "value" })
      expect(store.isEditing).toBe(false)
    })

    it("throws error when file has no notebook_id", async () => {
      const store = useWorkspaceStore()
      store.currentWorkspace = { id: 1 } as any
      store.currentFile = { id: 1, notebook_id: undefined } as any

      await expect(store.saveFile("content")).rejects.toThrow("File has no notebook_id")
    })
  })

  describe("createFile", () => {
    it("creates file and selects it", async () => {
      const mockFile = { id: 1, path: "new.md", filename: "new.md", notebook_id: 1 }
      const mockContent = { id: 1, content: "" }

      vi.mocked(fileService.create).mockResolvedValue(mockFile as any)
      vi.mocked(fileService.get).mockResolvedValue({ ...mockFile, content_type: "text/markdown" } as any)
      vi.mocked(fileService.getContent).mockResolvedValue(mockContent as any)

      const store = useWorkspaceStore()
      store.currentWorkspace = { id: 1 } as any

      const result = await store.createFile(1, "new.md", "# New File")

      expect(fileService.create).toHaveBeenCalledWith(1, 1, "new.md", "# New File")
      expect(result).toEqual(mockFile)
    })
  })

  describe("deleteFile", () => {
    it("deletes file and clears current file", async () => {
      vi.mocked(fileService.delete).mockResolvedValue(undefined)

      const store = useWorkspaceStore()
      store.currentWorkspace = { id: 1 } as any
      store.currentFile = { id: 1, notebook_id: 1, path: "test.md" } as any
      store.fileTrees.set(1, [{ name: "test.md", path: "test.md", type: "file" }])

      await store.deleteFile(1)

      expect(fileService.delete).toHaveBeenCalledWith(1, 1, 1)
      expect(store.currentFile).toBeNull()
      expect(store.isEditing).toBe(false)
    })
  })

  describe("uploadFile", () => {
    it("uploads file and adds to tree", async () => {
      const mockFile = { id: 1, path: "upload.png", filename: "upload.png" }
      vi.mocked(fileService.upload).mockResolvedValue(mockFile as any)

      const store = useWorkspaceStore()
      store.currentWorkspace = { id: 1 } as any

      const file = new File(["content"], "upload.png", { type: "image/png" })
      const result = await store.uploadFile(1, file, "images/upload.png")

      expect(fileService.upload).toHaveBeenCalledWith(1, 1, file, "images/upload.png")
      expect(result).toEqual(mockFile)
    })
  })

  describe("moveFile", () => {
    it("moves file and updates tree", async () => {
      const movedFile = { id: 1, path: "new/path.md", filename: "path.md" }
      vi.mocked(fileService.move).mockResolvedValue(movedFile as any)

      const store = useWorkspaceStore()
      store.currentWorkspace = { id: 1 } as any
      store.fileTrees.set(1, [
        { name: "old.md", path: "old.md", type: "file", file: { id: 1, path: "old.md" } as any },
      ])

      const result = await store.moveFile(1, 1, "new/path.md")

      expect(fileService.move).toHaveBeenCalledWith(1, 1, 1, "new/path.md")
      expect(result).toEqual(movedFile)
    })

    it("updates current file if it was moved", async () => {
      const movedFile = { id: 1, path: "new/path.md", filename: "path.md" }
      vi.mocked(fileService.move).mockResolvedValue(movedFile as any)

      const store = useWorkspaceStore()
      store.currentWorkspace = { id: 1 } as any
      store.currentFile = { id: 1, path: "old.md", content: "content" } as any
      store.fileTrees.set(1, [])

      await store.moveFile(1, 1, "new/path.md")

      expect(store.currentFile?.path).toBe("new/path.md")
    })
  })

  describe("toggleNotebookExpansion", () => {
    it("expands notebook and fetches files", async () => {
      vi.mocked(fileService.list).mockResolvedValue([])

      const store = useWorkspaceStore()
      store.currentWorkspace = { id: 1 } as any
      const notebook = { id: 1, name: "Notebook" } as any

      store.toggleNotebookExpansion(notebook)

      expect(store.expandedNotebooks.has(1)).toBe(true)
      expect(store.currentNotebook).toEqual(notebook)
      expect(fileService.list).toHaveBeenCalled()
    })

    it("collapses expanded notebook", () => {
      const store = useWorkspaceStore()
      store.expandedNotebooks.add(1)
      const notebook = { id: 1, name: "Notebook" } as any

      store.toggleNotebookExpansion(notebook)

      expect(store.expandedNotebooks.has(1)).toBe(false)
    })
  })

  describe("setEditing", () => {
    it("sets editing state", () => {
      const store = useWorkspaceStore()

      store.setEditing(true)
      expect(store.isEditing).toBe(true)

      store.setEditing(false)
      expect(store.isEditing).toBe(false)
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
