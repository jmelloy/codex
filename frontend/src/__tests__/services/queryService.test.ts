import { describe, it, expect, vi, beforeEach } from "vitest"
import { queryService } from "../../services/queryService"
import apiClient from "../../services/api"

vi.mock("../../services/api", () => ({
  default: {
    post: vi.fn(),
  },
}))

function mockQueryResponse(overrides = {}) {
  const response = {
    data: { files: [], total: 0, limit: 10, offset: 0, ...overrides },
  }
  vi.mocked(apiClient.post).mockResolvedValue(response)
  return response.data
}

describe("Query Service", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe("execute", () => {
    it("executes queries with correct URL and params", async () => {
      mockQueryResponse({
        files: [{ id: 1, title: "File 1" }, { id: 2, title: "File 2" }],
        total: 2,
      })

      const query = { tags: ["important"], limit: 10 }
      const result = await queryService.execute(1, query)

      expect(apiClient.post).toHaveBeenCalledWith("/api/v1/query/?workspace_id=1", query)
      expect(result.files).toHaveLength(2)
      expect(result.total).toBe(2)
    })

    it("passes all query parameters through", async () => {
      mockQueryResponse()
      const query = {
        tags: ["project", "important"],
        content_types: ["text/markdown", "text/plain"],
        properties: { status: "todo" },
        sort: "created_at desc",
        limit: 50,
        offset: 10,
        created_after: "2024-01-01",
        created_before: "2024-12-31",
      }

      await queryService.execute(1, query)
      expect(apiClient.post).toHaveBeenCalledWith("/api/v1/query/?workspace_id=1", query)
    })

    it("passes workspace ID in URL", async () => {
      mockQueryResponse()
      await queryService.execute(42, { limit: 10 })
      expect(apiClient.post).toHaveBeenCalledWith("/api/v1/query/?workspace_id=42", expect.any(Object))
    })

    it("handles API errors", async () => {
      vi.mocked(apiClient.post).mockRejectedValue(new Error("Network error"))
      await expect(queryService.execute(1, { limit: 10 })).rejects.toThrow("Network error")
    })
  })

  describe("queryFiles", () => {
    it("returns only files array", async () => {
      mockQueryResponse({
        files: [{ id: 1, title: "File 1" }, { id: 2, title: "File 2" }],
        total: 2,
      })

      const files = await queryService.queryFiles(1, { tags: ["important"], limit: 10 })
      expect(files).toHaveLength(2)
      expect(files[0].id).toBe(1)
    })

    it("handles empty results", async () => {
      mockQueryResponse()
      const files = await queryService.queryFiles(1, { limit: 10 })
      expect(files).toHaveLength(0)
    })
  })

  describe("queryWithGroups", () => {
    it("returns groups object", async () => {
      mockQueryResponse({
        groups: {
          todo: [{ id: 1, title: "Task 1" }],
          done: [{ id: 2, title: "Task 2" }],
        },
        total: 2,
      })

      const groups = await queryService.queryWithGroups(1, {
        group_by: "properties.status",
        limit: 10,
      })

      expect(groups).toHaveProperty("todo")
      expect(groups).toHaveProperty("done")
      expect(groups.todo).toHaveLength(1)
    })

    it("returns empty object when no groups", async () => {
      mockQueryResponse({ files: [{ id: 1, title: "File 1" }], total: 1 })
      const groups = await queryService.queryWithGroups(1, { limit: 10 })
      expect(groups).toEqual({})
    })

    it("handles multiple groups", async () => {
      mockQueryResponse({
        groups: {
          high: [{ id: 1 }],
          medium: [{ id: 2 }, { id: 3 }],
          low: [{ id: 4 }],
        },
        total: 4,
      })

      const groups = await queryService.queryWithGroups(1, {
        group_by: "properties.priority",
        limit: 10,
      })

      expect(Object.keys(groups)).toHaveLength(3)
      expect(groups.medium).toHaveLength(2)
    })
  })

  describe("pagination", () => {
    it("handles paginated results", async () => {
      mockQueryResponse({ files: [{ id: 11 }, { id: 12 }], total: 20, limit: 2, offset: 10 })

      const result = await queryService.execute(1, { limit: 2, offset: 10 })
      expect(result.files).toHaveLength(2)
      expect(result.total).toBe(20)
      expect(result.offset).toBe(10)
    })
  })
})
