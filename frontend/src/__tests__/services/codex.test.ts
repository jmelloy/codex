import { describe, it, expect, beforeEach, vi, type Mock } from "vitest"
import apiClient from "../../services/api"
import {
  workspaceService,
  notebookService,
  searchService,
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
