import { describe, it, expect, vi, beforeEach } from "vitest"
import { queryService } from "../../services/queryService"
import apiClient from "../../services/api"

// Mock the API client
vi.mock("../../services/api", () => ({
  default: {
    post: vi.fn(),
  },
}))

describe("Query Service", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe("execute", () => {
    it("should execute a query and return results", async () => {
      const mockResponse = {
        data: {
          files: [
            { id: 1, title: "File 1" },
            { id: 2, title: "File 2" },
          ],
          total: 2,
          limit: 10,
          offset: 0,
        },
      }

      vi.mocked(apiClient.post).mockResolvedValue(mockResponse)

      const query = {
        tags: ["important"],
        limit: 10,
      }

      const result = await queryService.execute(1, query)

      expect(apiClient.post).toHaveBeenCalledWith("/api/v1/query/?workspace_id=1", query)
      expect(result.files).toHaveLength(2)
      expect(result.total).toBe(2)
    })

    it("should pass workspace ID in URL", async () => {
      const mockResponse = {
        data: {
          files: [],
          total: 0,
          limit: 10,
          offset: 0,
        },
      }

      vi.mocked(apiClient.post).mockResolvedValue(mockResponse)

      await queryService.execute(42, { limit: 10 })

      expect(apiClient.post).toHaveBeenCalledWith(
        "/api/v1/query/?workspace_id=42",
        expect.any(Object)
      )
    })

    it("should pass query parameters correctly", async () => {
      const mockResponse = {
        data: {
          files: [],
          total: 0,
          limit: 10,
          offset: 0,
        },
      }

      vi.mocked(apiClient.post).mockResolvedValue(mockResponse)

      const query = {
        tags: ["project", "important"],
        file_types: ["md", "txt"],
        properties: { status: "todo" },
        sort: "created_at desc",
        limit: 50,
        offset: 10,
      }

      await queryService.execute(1, query)

      expect(apiClient.post).toHaveBeenCalledWith("/api/v1/query/?workspace_id=1", query)
    })

    it("should handle API errors", async () => {
      vi.mocked(apiClient.post).mockRejectedValue(new Error("Network error"))

      await expect(queryService.execute(1, { limit: 10 })).rejects.toThrow("Network error")
    })
  })

  describe("queryFiles", () => {
    it("should return only files array", async () => {
      const mockResponse = {
        data: {
          files: [
            { id: 1, title: "File 1" },
            { id: 2, title: "File 2" },
          ],
          total: 2,
          limit: 10,
          offset: 0,
        },
      }

      vi.mocked(apiClient.post).mockResolvedValue(mockResponse)

      const query = {
        tags: ["important"],
        limit: 10,
      }

      const files = await queryService.queryFiles(1, query)

      expect(Array.isArray(files)).toBe(true)
      expect(files).toHaveLength(2)
      expect(files[0].id).toBe(1)
      expect(files[1].id).toBe(2)
    })

    it("should handle empty results", async () => {
      const mockResponse = {
        data: {
          files: [],
          total: 0,
          limit: 10,
          offset: 0,
        },
      }

      vi.mocked(apiClient.post).mockResolvedValue(mockResponse)

      const files = await queryService.queryFiles(1, { limit: 10 })

      expect(files).toHaveLength(0)
    })
  })

  describe("queryWithGroups", () => {
    it("should return groups object", async () => {
      const mockResponse = {
        data: {
          files: [],
          groups: {
            todo: [{ id: 1, title: "Task 1" }],
            done: [{ id: 2, title: "Task 2" }],
          },
          total: 2,
          limit: 10,
          offset: 0,
        },
      }

      vi.mocked(apiClient.post).mockResolvedValue(mockResponse)

      const query = {
        group_by: "properties.status",
        limit: 10,
      }

      const groups = await queryService.queryWithGroups(1, query)

      expect(groups).toHaveProperty("todo")
      expect(groups).toHaveProperty("done")
      expect(groups.todo).toHaveLength(1)
      expect(groups.done).toHaveLength(1)
    })

    it("should return empty object when no groups", async () => {
      const mockResponse = {
        data: {
          files: [{ id: 1, title: "File 1" }],
          total: 1,
          limit: 10,
          offset: 0,
        },
      }

      vi.mocked(apiClient.post).mockResolvedValue(mockResponse)

      const groups = await queryService.queryWithGroups(1, { limit: 10 })

      expect(groups).toEqual({})
    })

    it("should handle multiple groups", async () => {
      const mockResponse = {
        data: {
          files: [],
          groups: {
            high: [{ id: 1 }],
            medium: [{ id: 2 }, { id: 3 }],
            low: [{ id: 4 }],
          },
          total: 4,
          limit: 10,
          offset: 0,
        },
      }

      vi.mocked(apiClient.post).mockResolvedValue(mockResponse)

      const groups = await queryService.queryWithGroups(1, {
        group_by: "properties.priority",
        limit: 10,
      })

      expect(Object.keys(groups)).toHaveLength(3)
      expect(groups.high).toHaveLength(1)
      expect(groups.medium).toHaveLength(2)
      expect(groups.low).toHaveLength(1)
    })
  })

  describe("pagination", () => {
    it("should handle paginated results", async () => {
      const mockResponse = {
        data: {
          files: [{ id: 11 }, { id: 12 }],
          total: 20,
          limit: 2,
          offset: 10,
        },
      }

      vi.mocked(apiClient.post).mockResolvedValue(mockResponse)

      const result = await queryService.execute(1, { limit: 2, offset: 10 })

      expect(result.files).toHaveLength(2)
      expect(result.total).toBe(20)
      expect(result.limit).toBe(2)
      expect(result.offset).toBe(10)
    })
  })

  describe("filtering", () => {
    it("should handle tag filtering", async () => {
      const mockResponse = {
        data: {
          files: [{ id: 1, tags: ["important"] }],
          total: 1,
          limit: 10,
          offset: 0,
        },
      }

      vi.mocked(apiClient.post).mockResolvedValue(mockResponse)

      await queryService.execute(1, {
        tags: ["important"],
        limit: 10,
      })

      expect(apiClient.post).toHaveBeenCalledWith(
        "/api/v1/query/?workspace_id=1",
        expect.objectContaining({
          tags: ["important"],
        })
      )
    })

    it("should handle property filtering", async () => {
      const mockResponse = {
        data: {
          files: [{ id: 1 }],
          total: 1,
          limit: 10,
          offset: 0,
        },
      }

      vi.mocked(apiClient.post).mockResolvedValue(mockResponse)

      await queryService.execute(1, {
        properties: { status: "todo", priority: "high" },
        limit: 10,
      })

      expect(apiClient.post).toHaveBeenCalledWith(
        "/api/v1/query/?workspace_id=1",
        expect.objectContaining({
          properties: { status: "todo", priority: "high" },
        })
      )
    })

    it("should handle date filtering", async () => {
      const mockResponse = {
        data: {
          files: [],
          total: 0,
          limit: 10,
          offset: 0,
        },
      }

      vi.mocked(apiClient.post).mockResolvedValue(mockResponse)

      await queryService.execute(1, {
        created_after: "2024-01-01",
        created_before: "2024-12-31",
        limit: 10,
      })

      expect(apiClient.post).toHaveBeenCalledWith(
        "/api/v1/query/?workspace_id=1",
        expect.objectContaining({
          created_after: "2024-01-01",
          created_before: "2024-12-31",
        })
      )
    })
  })

  describe("sorting", () => {
    it("should handle sorting", async () => {
      const mockResponse = {
        data: {
          files: [{ id: 2 }, { id: 1 }],
          total: 2,
          limit: 10,
          offset: 0,
        },
      }

      vi.mocked(apiClient.post).mockResolvedValue(mockResponse)

      await queryService.execute(1, {
        sort: "created_at desc",
        limit: 10,
      })

      expect(apiClient.post).toHaveBeenCalledWith(
        "/api/v1/query/?workspace_id=1",
        expect.objectContaining({
          sort: "created_at desc",
        })
      )
    })
  })
})
