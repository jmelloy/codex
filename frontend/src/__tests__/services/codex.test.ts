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

// Mock the api client
vi.mock("../../services/api", () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}))

describe("Codex Services", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe("workspaceService", () => {
    it("lists all workspaces", async () => {
      const mockWorkspaces = [
        { id: 1, name: "Workspace 1", path: "/path1", owner_id: 1 },
        { id: 2, name: "Workspace 2", path: "/path2", owner_id: 1 },
      ]
      ;(apiClient.get as Mock).mockResolvedValue({ data: mockWorkspaces })

      const result = await workspaceService.list()

      expect(apiClient.get).toHaveBeenCalledWith("/api/v1/workspaces/")
      expect(result).toEqual(mockWorkspaces)
    })

    it("gets a single workspace by id", async () => {
      const mockWorkspace = { id: 1, name: "Workspace 1", path: "/path1", owner_id: 1 }
      ;(apiClient.get as Mock).mockResolvedValue({ data: mockWorkspace })

      const result = await workspaceService.get(1)

      expect(apiClient.get).toHaveBeenCalledWith("/api/v1/workspaces/1")
      expect(result).toEqual(mockWorkspace)
    })

    it("creates a new workspace", async () => {
      const mockWorkspace = { id: 1, name: "New Workspace", path: "/new", owner_id: 1 }
      ;(apiClient.post as Mock).mockResolvedValue({ data: mockWorkspace })

      const result = await workspaceService.create("New Workspace")

      expect(apiClient.post).toHaveBeenCalledWith("/api/v1/workspaces/", { name: "New Workspace" })
      expect(result).toEqual(mockWorkspace)
    })

    it("updates workspace theme", async () => {
      const mockWorkspace = { id: 1, name: "Workspace", theme_setting: "dark" }
      ;(apiClient.patch as Mock).mockResolvedValue({ data: mockWorkspace })

      const result = await workspaceService.updateTheme(1, "dark")

      expect(apiClient.patch).toHaveBeenCalledWith("/api/v1/workspaces/1/theme", { theme: "dark" })
      expect(result).toEqual(mockWorkspace)
    })
  })

  describe("notebookService", () => {
    it("lists notebooks for a workspace", async () => {
      const mockNotebooks = [
        { id: 1, name: "Notebook 1" },
        { id: 2, name: "Notebook 2" },
      ]
      ;(apiClient.get as Mock).mockResolvedValue({ data: mockNotebooks })

      const result = await notebookService.list(1)

      expect(apiClient.get).toHaveBeenCalledWith("/api/v1/workspaces/1/notebooks/")
      expect(result).toEqual(mockNotebooks)
    })

    it("gets a single notebook by id", async () => {
      const mockNotebook = { id: 1, name: "Notebook 1" }
      ;(apiClient.get as Mock).mockResolvedValue({ data: mockNotebook })

      const result = await notebookService.get(1, 1)

      expect(apiClient.get).toHaveBeenCalledWith("/api/v1/workspaces/1/notebooks/1")
      expect(result).toEqual(mockNotebook)
    })

    it("creates a new notebook", async () => {
      const mockNotebook = { id: 1, name: "New Notebook" }
      ;(apiClient.post as Mock).mockResolvedValue({ data: mockNotebook })

      const result = await notebookService.create(1, "New Notebook")

      expect(apiClient.post).toHaveBeenCalledWith("/api/v1/workspaces/1/notebooks/", {
        name: "New Notebook",
      })
      expect(result).toEqual(mockNotebook)
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

    it("lists files for a notebook", async () => {
      const mockResponse = { files: [mockFile], pagination: {} }
      ;(apiClient.get as Mock).mockResolvedValue({ data: mockResponse })

      const result = await fileService.list(1, 1)

      expect(apiClient.get).toHaveBeenCalledWith("/api/v1/workspaces/1/notebooks/1/files/")
      expect(result).toEqual([mockFile])
    })

    it("handles legacy file list response format", async () => {
      // When response is a direct array (backwards compatibility)
      ;(apiClient.get as Mock).mockResolvedValue({ data: [mockFile] })

      const result = await fileService.list(1, 1)

      expect(result).toEqual([mockFile])
    })

    it("gets file metadata by id", async () => {
      ;(apiClient.get as Mock).mockResolvedValue({ data: mockFile })

      const result = await fileService.get(1, 1, 1)

      expect(apiClient.get).toHaveBeenCalledWith("/api/v1/workspaces/1/notebooks/1/files/1")
      expect(result).toEqual(mockFile)
    })

    it("gets file content by id", async () => {
      const mockContent = { id: 1, content: "# Test content" }
      ;(apiClient.get as Mock).mockResolvedValue({ data: mockContent })

      const result = await fileService.getContent(1, 1, 1)

      expect(apiClient.get).toHaveBeenCalledWith("/api/v1/workspaces/1/notebooks/1/files/1/text")
      expect(result).toEqual(mockContent)
    })

    it("gets file by path with URL encoding", async () => {
      ;(apiClient.get as Mock).mockResolvedValue({ data: mockFile })

      await fileService.getByPath("folder/test file.md", 1, 1)

      expect(apiClient.get).toHaveBeenCalledWith(
        "/api/v1/workspaces/1/notebooks/1/files/by-path?path=folder%2Ftest%20file.md"
      )
    })

    it("gets content by path with URL encoding", async () => {
      const mockContent = { id: 1, content: "content" }
      ;(apiClient.get as Mock).mockResolvedValue({ data: mockContent })

      await fileService.getContentByPath("folder/test.md", 1, 1)

      expect(apiClient.get).toHaveBeenCalledWith(
        "/api/v1/workspaces/1/notebooks/1/files/by-path/text?path=folder%2Ftest.md"
      )
    })

    it("returns content URL by path", () => {
      const url = fileService.getContentUrlByPath("folder/test.png", 1, 1)

      expect(url).toBe(
        "/api/v1/workspaces/1/notebooks/1/files/by-path/content?path=folder%2Ftest.png"
      )
    })

    it("returns content URL by id", () => {
      const url = fileService.getContentUrl(1, 2, 3)

      expect(url).toBe("/api/v1/workspaces/2/notebooks/3/files/1/content")
    })

    it("resolves a link to a file", async () => {
      const mockResolved = { ...mockFile, resolved_path: "resolved/test.md" }
      ;(apiClient.post as Mock).mockResolvedValue({ data: mockResolved })

      const result = await fileService.resolveLink("test.md", 1, 1, "current/path.md")

      expect(apiClient.post).toHaveBeenCalledWith(
        "/api/v1/workspaces/1/notebooks/1/files/resolve-link",
        {
          link: "test.md",
          current_file_path: "current/path.md",
        }
      )
      expect(result).toEqual(mockResolved)
    })

    it("creates a new file", async () => {
      ;(apiClient.post as Mock).mockResolvedValue({ data: mockFile })

      const result = await fileService.create(1, 1, "new.md", "# New file")

      expect(apiClient.post).toHaveBeenCalledWith("/api/v1/workspaces/1/notebooks/1/files/", {
        path: "new.md",
        content: "# New file",
      })
      expect(result).toEqual(mockFile)
    })

    it("updates file with content and properties", async () => {
      ;(apiClient.put as Mock).mockResolvedValue({ data: mockFile })

      const result = await fileService.update(1, 1, 1, "updated content", { tag: "test" })

      expect(apiClient.put).toHaveBeenCalledWith("/api/v1/workspaces/1/notebooks/1/files/1", {
        content: "updated content",
        properties: { tag: "test" },
      })
      expect(result).toEqual(mockFile)
    })

    it("updates file with only properties (no content)", async () => {
      ;(apiClient.put as Mock).mockResolvedValue({ data: mockFile })

      await fileService.update(1, 1, 1, null, { tag: "test" })

      expect(apiClient.put).toHaveBeenCalledWith("/api/v1/workspaces/1/notebooks/1/files/1", {
        properties: { tag: "test" },
      })
    })

    it("updates file with only content (no properties)", async () => {
      ;(apiClient.put as Mock).mockResolvedValue({ data: mockFile })

      await fileService.update(1, 1, 1, "new content", undefined)

      expect(apiClient.put).toHaveBeenCalledWith("/api/v1/workspaces/1/notebooks/1/files/1", {
        content: "new content",
      })
    })

    it("deletes a file", async () => {
      ;(apiClient.delete as Mock).mockResolvedValue({})

      await fileService.delete(1, 1, 1)

      expect(apiClient.delete).toHaveBeenCalledWith("/api/v1/workspaces/1/notebooks/1/files/1")
    })

    it("uploads a file with form data", async () => {
      ;(apiClient.post as Mock).mockResolvedValue({ data: mockFile })
      const file = new File(["content"], "test.txt", { type: "text/plain" })

      const result = await fileService.upload(1, 1, file, "uploads/test.txt")

      expect(apiClient.post).toHaveBeenCalledWith(
        "/api/v1/files/upload",
        expect.any(FormData),
        expect.objectContaining({
          headers: { "Content-Type": "multipart/form-data" },
        })
      )
      expect(result).toEqual(mockFile)
    })

    it("uploads a file without path", async () => {
      ;(apiClient.post as Mock).mockResolvedValue({ data: mockFile })
      const file = new File(["content"], "test.txt", { type: "text/plain" })

      await fileService.upload(1, 1, file)

      const formData = (apiClient.post as Mock).mock.calls[0][1] as FormData
      expect(formData.get("path")).toBeNull()
    })

    it("moves a file", async () => {
      const movedFile = { ...mockFile, path: "new/path.md" }
      ;(apiClient.patch as Mock).mockResolvedValue({ data: movedFile })

      const result = await fileService.move(1, 1, 1, "new/path.md")

      expect(apiClient.patch).toHaveBeenCalledWith(
        "/api/v1/workspaces/1/notebooks/1/files/1/move",
        { new_path: "new/path.md" }
      )
      expect(result).toEqual(movedFile)
    })

    it("gets file history", async () => {
      const mockHistory = {
        file_id: 1,
        path: "test.md",
        history: [{ hash: "abc123", author: "user", date: "2024-01-01", message: "commit" }],
      }
      ;(apiClient.get as Mock).mockResolvedValue({ data: mockHistory })

      const result = await fileService.getHistory(1, 1, 1, 10)

      expect(apiClient.get).toHaveBeenCalledWith(
        "/api/v1/workspaces/1/notebooks/1/files/1/history?max_count=10"
      )
      expect(result).toEqual(mockHistory)
    })

    it("uses default max_count for history", async () => {
      const mockHistory = { file_id: 1, path: "test.md", history: [] }
      ;(apiClient.get as Mock).mockResolvedValue({ data: mockHistory })

      await fileService.getHistory(1, 1, 1)

      expect(apiClient.get).toHaveBeenCalledWith(
        "/api/v1/workspaces/1/notebooks/1/files/1/history?max_count=20"
      )
    })

    it("gets file at commit", async () => {
      const mockFileAtCommit = {
        file_id: 1,
        path: "test.md",
        commit_hash: "abc123",
        content: "old content",
      }
      ;(apiClient.get as Mock).mockResolvedValue({ data: mockFileAtCommit })

      const result = await fileService.getAtCommit(1, 1, 1, "abc123")

      expect(apiClient.get).toHaveBeenCalledWith(
        "/api/v1/files/1/history/abc123?workspace_id=1&notebook_id=1"
      )
      expect(result).toEqual(mockFileAtCommit)
    })
  })

  describe("templateService", () => {
    it("lists templates for a notebook", async () => {
      const mockTemplates = [
        { id: "note", name: "Note", description: "A note", icon: "📝" },
        { id: "journal", name: "Journal", description: "A journal entry", icon: "📓" },
      ]
      ;(apiClient.get as Mock).mockResolvedValue({ data: { templates: mockTemplates } })

      const result = await templateService.list(1, 1)

      expect(apiClient.get).toHaveBeenCalledWith(
        "/api/v1/workspaces/1/notebooks/1/files/templates"
      )
      expect(result).toEqual(mockTemplates)
    })

    it("creates a file from template", async () => {
      const mockFile = { id: 1, path: "new-note.md", filename: "new-note.md" }
      ;(apiClient.post as Mock).mockResolvedValue({ data: mockFile })

      const result = await templateService.createFromTemplate(1, 1, "note", "my-note.md")

      expect(apiClient.post).toHaveBeenCalledWith("/api/v1/files/from-template", {
        notebook_id: 1,
        workspace_id: 1,
        template_id: "note",
        filename: "my-note.md",
      })
      expect(result).toEqual(mockFile)
    })

    it("creates a file from template without filename", async () => {
      const mockFile = { id: 1, path: "untitled.md", filename: "untitled.md" }
      ;(apiClient.post as Mock).mockResolvedValue({ data: mockFile })

      await templateService.createFromTemplate(1, 1, "note")

      expect(apiClient.post).toHaveBeenCalledWith("/api/v1/files/from-template", {
        notebook_id: 1,
        workspace_id: 1,
        template_id: "note",
        filename: null,
      })
    })

    it("expands date patterns in filenames", () => {
      // Mock the date for consistent test results
      const mockDate = new Date(2024, 5, 15) // June 15, 2024
      vi.setSystemTime(mockDate)

      const result = templateService.expandPattern("{yyyy}-{mm}-{dd}-{title}.md", "my-note")

      expect(result).toBe("2024-06-15-my-note.md")

      vi.useRealTimers()
    })

    it("expands all date patterns", () => {
      const mockDate = new Date(2024, 0, 5) // January 5, 2024
      vi.setSystemTime(mockDate)

      const result = templateService.expandPattern(
        "{yyyy}/{yy}/{mm}/{dd}/{month}/{mon}/{title}",
        "test"
      )

      expect(result).toBe("2024/24/01/05/January/Jan/test")

      vi.useRealTimers()
    })

    it("uses default title if not provided", () => {
      const mockDate = new Date(2024, 0, 1)
      vi.setSystemTime(mockDate)

      const result = templateService.expandPattern("{title}.md")

      expect(result).toBe("untitled.md")

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

    it("gets folder metadata with URL encoding", async () => {
      ;(apiClient.get as Mock).mockResolvedValue({ data: mockFolder })

      const result = await folderService.get("folder with spaces", 1, 1)

      expect(apiClient.get).toHaveBeenCalledWith(
        "/api/v1/workspaces/1/notebooks/1/folders/folder%20with%20spaces"
      )
      expect(result).toEqual(mockFolder)
    })

    it("updates folder properties", async () => {
      const updatedFolder = { ...mockFolder, title: "Updated Title" }
      ;(apiClient.put as Mock).mockResolvedValue({ data: updatedFolder })

      const result = await folderService.updateProperties("test-folder", 1, 1, {
        title: "Updated Title",
      })

      expect(apiClient.put).toHaveBeenCalledWith(
        "/api/v1/workspaces/1/notebooks/1/folders/test-folder",
        { properties: { title: "Updated Title" } }
      )
      expect(result).toEqual(updatedFolder)
    })

    it("deletes a folder", async () => {
      ;(apiClient.delete as Mock).mockResolvedValue({})

      await folderService.delete("test-folder", 1, 1)

      expect(apiClient.delete).toHaveBeenCalledWith(
        "/api/v1/workspaces/1/notebooks/1/folders/test-folder"
      )
    })
  })

  describe("searchService", () => {
    it("performs a text search", async () => {
      const mockResults = { results: [{ id: 1, title: "Test" }] }
      ;(apiClient.get as Mock).mockResolvedValue({ data: mockResults })

      const result = await searchService.search(1, "test query")

      expect(apiClient.get).toHaveBeenCalledWith("/api/v1/workspaces/1/search/?q=test query")
      expect(result).toEqual(mockResults)
    })

    it("searches by tags", async () => {
      const mockResults = { results: [{ id: 1, title: "Tagged File" }] }
      ;(apiClient.get as Mock).mockResolvedValue({ data: mockResults })

      const result = await searchService.searchByTags(1, ["tag1", "tag2"])

      expect(apiClient.get).toHaveBeenCalledWith(
        "/api/v1/workspaces/1/search/tags?tags=tag1,tag2"
      )
      expect(result).toEqual(mockResults)
    })
  })
})
