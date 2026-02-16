import { describe, it, expect, beforeEach, vi, type Mock } from "vitest"
import apiClient from "../../services/api"
import {
  workspaceService,
  notebookService,
  fileService,
  folderService,
  searchService,
  templateService,
} from "../../services/codex"

vi.mock("../../services/api", () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}))

const mockGet = apiClient.get as Mock
const mockPost = apiClient.post as Mock
const mockPut = apiClient.put as Mock
const mockPatch = apiClient.patch as Mock
const mockDelete = apiClient.delete as Mock

describe("Codex Services", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe("workspaceService", () => {
    it("lists, gets, creates, and updates theme for workspaces", async () => {
      const mockWorkspaces = [
        { id: 1, name: "Workspace 1", path: "/path1", owner_id: 1 },
        { id: 2, name: "Workspace 2", path: "/path2", owner_id: 1 },
      ]

      // list
      mockGet.mockResolvedValue({ data: mockWorkspaces })
      expect(await workspaceService.list()).toEqual(mockWorkspaces)
      expect(mockGet).toHaveBeenCalledWith("/api/v1/workspaces/")

      // get
      mockGet.mockResolvedValue({ data: mockWorkspaces[0] })
      expect(await workspaceService.get(1)).toEqual(mockWorkspaces[0])
      expect(mockGet).toHaveBeenCalledWith("/api/v1/workspaces/1")

      // create
      mockPost.mockResolvedValue({ data: mockWorkspaces[0] })
      expect(await workspaceService.create("New Workspace")).toEqual(mockWorkspaces[0])
      expect(mockPost).toHaveBeenCalledWith("/api/v1/workspaces/", { name: "New Workspace" })

      // updateTheme
      const themed = { id: 1, name: "Workspace", theme_setting: "dark" }
      mockPatch.mockResolvedValue({ data: themed })
      expect(await workspaceService.updateTheme(1, "dark")).toEqual(themed)
      expect(mockPatch).toHaveBeenCalledWith("/api/v1/workspaces/1/theme", { theme: "dark" })
    })
  })

  describe("notebookService", () => {
    it("lists, gets, and creates notebooks", async () => {
      const mockNotebooks = [{ id: 1, name: "Notebook 1" }, { id: 2, name: "Notebook 2" }]

      mockGet.mockResolvedValue({ data: mockNotebooks })
      expect(await notebookService.list(1)).toEqual(mockNotebooks)
      expect(mockGet).toHaveBeenCalledWith("/api/v1/workspaces/1/notebooks/")

      mockGet.mockResolvedValue({ data: mockNotebooks[0] })
      expect(await notebookService.get(1, 1)).toEqual(mockNotebooks[0])
      expect(mockGet).toHaveBeenCalledWith("/api/v1/workspaces/1/notebooks/1")

      mockPost.mockResolvedValue({ data: mockNotebooks[0] })
      expect(await notebookService.create(1, "New Notebook")).toEqual(mockNotebooks[0])
      expect(mockPost).toHaveBeenCalledWith("/api/v1/workspaces/1/notebooks/", { name: "New Notebook" })
    })
  })

  describe("fileService", () => {
    const mockFile = {
      id: 1,
      notebook_id: 1,
      path: "test.md",
      filename: "test.md",
      content_type: "text/markdown",
      size: 100,
    }

    it("lists files (paginated and legacy format)", async () => {
      mockGet.mockResolvedValue({ data: { files: [mockFile], pagination: {} } })
      expect(await fileService.list(1, 1)).toEqual([mockFile])
      expect(mockGet).toHaveBeenCalledWith("/api/v1/workspaces/1/notebooks/1/files/")

      // Legacy array format
      mockGet.mockResolvedValue({ data: [mockFile] })
      expect(await fileService.list(1, 1)).toEqual([mockFile])
    })

    it("gets file metadata and content", async () => {
      mockGet.mockResolvedValue({ data: mockFile })
      expect(await fileService.get(1, 1, 1)).toEqual(mockFile)
      expect(mockGet).toHaveBeenCalledWith("/api/v1/workspaces/1/notebooks/1/files/1")

      const mockContent = { id: 1, content: "# Test content" }
      mockGet.mockResolvedValue({ data: mockContent })
      expect(await fileService.getContent(1, 1, 1)).toEqual(mockContent)
      expect(mockGet).toHaveBeenCalledWith("/api/v1/workspaces/1/notebooks/1/files/1/text")
    })

    it("gets file by path with URL encoding", async () => {
      mockGet.mockResolvedValue({ data: mockFile })
      await fileService.getByPath("folder/test file.md", 1, 1)
      expect(mockGet).toHaveBeenCalledWith(
        "/api/v1/workspaces/1/notebooks/1/files/path/folder%2Ftest%20file.md"
      )
    })

    it("gets content by path and returns content URLs", async () => {
      const mockContent = { id: 1, content: "content" }
      mockGet.mockResolvedValue({ data: mockContent })
      await fileService.getContentByPath("folder/test.md", 1, 1)
      expect(mockGet).toHaveBeenCalledWith(
        "/api/v1/workspaces/1/notebooks/1/files/path/folder%2Ftest.md/text"
      )

      expect(fileService.getContentUrlByPath("folder/test.png", 1, 1)).toBe(
        "/api/v1/workspaces/1/notebooks/1/files/path/folder%2Ftest.png/content"
      )
      expect(fileService.getContentUrl(1, 2, 3)).toBe(
        "/api/v1/workspaces/2/notebooks/3/files/1/content"
      )
    })

    it("resolves links", async () => {
      const mockResolved = { ...mockFile, resolved_path: "resolved/test.md" }
      mockPost.mockResolvedValue({ data: mockResolved })
      expect(await fileService.resolveLink("test.md", 1, 1, "current/path.md")).toEqual(mockResolved)
      expect(mockPost).toHaveBeenCalledWith(
        "/api/v1/workspaces/1/notebooks/1/files/resolve-link",
        { link: "test.md", current_file_path: "current/path.md" }
      )
    })

    it("creates, updates, and deletes files", async () => {
      // create
      mockPost.mockResolvedValue({ data: mockFile })
      expect(await fileService.create(1, 1, "new.md", "# New file")).toEqual(mockFile)
      expect(mockPost).toHaveBeenCalledWith("/api/v1/workspaces/1/notebooks/1/files/", {
        path: "new.md",
        content: "# New file",
      })

      // update with content and properties
      mockPut.mockResolvedValue({ data: mockFile })
      await fileService.update(1, 1, 1, "updated content", { tag: "test" })
      expect(mockPut).toHaveBeenCalledWith("/api/v1/workspaces/1/notebooks/1/files/1", {
        content: "updated content",
        properties: { tag: "test" },
      })

      // update with only properties
      await fileService.update(1, 1, 1, null, { tag: "test" })
      expect(mockPut).toHaveBeenCalledWith("/api/v1/workspaces/1/notebooks/1/files/1", {
        properties: { tag: "test" },
      })

      // update with only content
      await fileService.update(1, 1, 1, "new content", undefined)
      expect(mockPut).toHaveBeenCalledWith("/api/v1/workspaces/1/notebooks/1/files/1", {
        content: "new content",
      })

      // delete
      mockDelete.mockResolvedValue({})
      await fileService.delete(1, 1, 1)
      expect(mockDelete).toHaveBeenCalledWith("/api/v1/workspaces/1/notebooks/1/files/1")
    })

    it("uploads files with and without path", async () => {
      mockPost.mockResolvedValue({ data: mockFile })
      const file = new File(["content"], "test.txt", { type: "text/plain" })

      await fileService.upload(1, 1, file, "uploads/test.txt")
      expect(mockPost).toHaveBeenCalledWith(
        "/api/v1/workspaces/1/notebooks/1/files/upload",
        expect.any(FormData),
        expect.objectContaining({ headers: { "Content-Type": "multipart/form-data" } })
      )

      await fileService.upload(1, 1, file)
      const formData = mockPost.mock.calls[1][1] as FormData
      expect(formData.get("path")).toBeNull()
    })

    it("moves files", async () => {
      const movedFile = { ...mockFile, path: "new/path.md" }
      mockPatch.mockResolvedValue({ data: movedFile })
      expect(await fileService.move(1, 1, 1, "new/path.md")).toEqual(movedFile)
      expect(mockPatch).toHaveBeenCalledWith(
        "/api/v1/workspaces/1/notebooks/1/files/1/move",
        { new_path: "new/path.md" }
      )
    })

    it("gets file history and file at commit", async () => {
      const mockHistory = {
        file_id: 1,
        path: "test.md",
        history: [{ hash: "abc123", author: "user", date: "2024-01-01", message: "commit" }],
      }
      mockGet.mockResolvedValue({ data: mockHistory })
      expect(await fileService.getHistory(1, 1, 1, 10)).toEqual(mockHistory)
      expect(mockGet).toHaveBeenCalledWith(
        "/api/v1/workspaces/1/notebooks/1/files/1/history?max_count=10"
      )

      // Default max_count
      mockGet.mockResolvedValue({ data: { file_id: 1, path: "test.md", history: [] } })
      await fileService.getHistory(1, 1, 1)
      expect(mockGet).toHaveBeenCalledWith(
        "/api/v1/workspaces/1/notebooks/1/files/1/history?max_count=20"
      )

      // getAtCommit
      const mockFileAtCommit = { file_id: 1, path: "test.md", commit_hash: "abc123", content: "old content" }
      mockGet.mockResolvedValue({ data: mockFileAtCommit })
      expect(await fileService.getAtCommit(1, 1, 1, "abc123")).toEqual(mockFileAtCommit)
      expect(mockGet).toHaveBeenCalledWith(
        "/api/v1/workspaces/1/notebooks/1/files/1/history/abc123"
      )
    })
  })

  describe("templateService", () => {
    it("lists and creates from templates", async () => {
      const mockTemplates = [
        { id: "note", name: "Note", description: "A note", icon: "📝" },
        { id: "journal", name: "Journal", description: "A journal entry", icon: "📓" },
      ]
      mockGet.mockResolvedValue({ data: { templates: mockTemplates } })
      expect(await templateService.list(1, 1)).toEqual(mockTemplates)
      expect(mockGet).toHaveBeenCalledWith("/api/v1/workspaces/1/notebooks/1/files/templates")

      // create with filename
      const mockFile = { id: 1, path: "new-note.md", filename: "new-note.md" }
      mockPost.mockResolvedValue({ data: mockFile })
      expect(await templateService.createFromTemplate(1, 1, "note", "my-note.md")).toEqual(mockFile)
      expect(mockPost).toHaveBeenCalledWith(
        "/api/v1/workspaces/1/notebooks/1/files/from-template",
        { template_id: "note", filename: "my-note.md" }
      )

      // create without filename
      mockPost.mockResolvedValue({ data: { id: 1, path: "untitled.md" } })
      await templateService.createFromTemplate(1, 1, "note")
      expect(mockPost).toHaveBeenCalledWith(
        "/api/v1/workspaces/1/notebooks/1/files/from-template",
        { template_id: "note", filename: null }
      )
    })

    it("expands date patterns in filenames", () => {
      vi.setSystemTime(new Date(2024, 5, 15)) // June 15, 2024
      expect(templateService.expandPattern("{yyyy}-{mm}-{dd}-{title}.md", "my-note"))
        .toBe("2024-06-15-my-note.md")

      vi.setSystemTime(new Date(2024, 0, 5)) // January 5, 2024
      expect(templateService.expandPattern("{yyyy}/{yy}/{mm}/{dd}/{month}/{mon}/{title}", "test"))
        .toBe("2024/24/01/05/January/Jan/test")

      // Default title
      vi.setSystemTime(new Date(2024, 0, 1))
      expect(templateService.expandPattern("{title}.md")).toBe("untitled.md")

      vi.useRealTimers()
    })
  })

  describe("folderService", () => {
    const mockFolder = {
      path: "test-folder",
      name: "test-folder",
      notebook_id: 1,
      file_count: 5,
      files: [],
      subfolders: [],
    }

    it("gets, updates, and deletes folders", async () => {
      // get with URL encoding
      mockGet.mockResolvedValue({ data: mockFolder })
      expect(await folderService.get("folder with spaces", 1, 1)).toEqual(mockFolder)
      expect(mockGet).toHaveBeenCalledWith(
        "/api/v1/workspaces/1/notebooks/1/folders/folder%20with%20spaces"
      )

      // update properties
      const updated = { ...mockFolder, title: "Updated Title" }
      mockPut.mockResolvedValue({ data: updated })
      expect(await folderService.updateProperties("test-folder", 1, 1, { title: "Updated Title" }))
        .toEqual(updated)
      expect(mockPut).toHaveBeenCalledWith(
        "/api/v1/workspaces/1/notebooks/1/folders/test-folder",
        { properties: { title: "Updated Title" } }
      )

      // delete
      mockDelete.mockResolvedValue({})
      await folderService.delete("test-folder", 1, 1)
      expect(mockDelete).toHaveBeenCalledWith(
        "/api/v1/workspaces/1/notebooks/1/folders/test-folder"
      )
    })
  })

  describe("searchService", () => {
    it("searches by text and tags", async () => {
      const mockResults = { results: [{ id: 1, title: "Test" }] }
      mockGet.mockResolvedValue({ data: mockResults })

      expect(await searchService.search(1, "test query")).toEqual(mockResults)
      expect(mockGet).toHaveBeenCalledWith("/api/v1/workspaces/1/search/?q=test%20query")

      const tagResults = { results: [{ id: 1, title: "Tagged File" }] }
      mockGet.mockResolvedValue({ data: tagResults })
      expect(await searchService.searchByTags(1, ["tag1", "tag2"])).toEqual(tagResults)
      expect(mockGet).toHaveBeenCalledWith("/api/v1/workspaces/1/search/tags?tags=tag1%2Ctag2")
    })
  })
})
