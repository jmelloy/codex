import { describe, it, expect, beforeEach, vi, type Mock } from "vitest"
import apiClient from "../../services/api"
import { orphanedDiscussionsService } from "../../services/orphanedDiscussions"

vi.mock("../../services/api", () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    delete: vi.fn(),
  },
}))

const mockGet = apiClient.get as Mock
const mockPost = apiClient.post as Mock
const mockDelete = apiClient.delete as Mock

const mockThread = {
  thread_id: 1,
  workspace_id: 1,
  notebook_id: 1,
  notebook_name: "Test Notebook",
  block_id: "01ABC",
  reason: "block_deleted" as const,
  root: {
    id: 1,
    author_id: 2,
    author_username: "jane",
    body: "Original comment",
    created_at: "2024-01-01T00:00:00Z",
    deleted_at: null,
  },
  replies: [],
  reply_count: 0,
  last_activity_at: "2024-01-01T00:00:00Z",
  archived_at: null,
  archived_by_id: null,
  archived_by_username: null,
}

describe("orphanedDiscussionsService", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("lists orphaned discussions with filters", async () => {
    mockGet.mockResolvedValue({ data: [mockThread] })

    const result = await orphanedDiscussionsService.list("my-workspace", { author_id: 2, include_archived: true })

    expect(result).toEqual([mockThread])
    expect(mockGet).toHaveBeenCalledWith("/api/v1/workspaces/my-workspace/orphaned-discussions/", {
      params: { author_id: 2, include_archived: true },
    })
  })

  it("gets a single orphaned discussion", async () => {
    mockGet.mockResolvedValue({ data: mockThread })

    const result = await orphanedDiscussionsService.get("my-workspace", 1)

    expect(result).toEqual(mockThread)
    expect(mockGet).toHaveBeenCalledWith("/api/v1/workspaces/my-workspace/orphaned-discussions/1")
  })

  it("restores a thread with a new block id", async () => {
    mockPost.mockResolvedValue({ data: mockThread })

    const result = await orphanedDiscussionsService.restore("my-workspace", 1, "01NEW")

    expect(result).toEqual(mockThread)
    expect(mockPost).toHaveBeenCalledWith("/api/v1/workspaces/my-workspace/orphaned-discussions/1/restore", {
      block_id: "01NEW",
    })
  })

  it("archives a thread", async () => {
    mockPost.mockResolvedValue({ data: { ...mockThread, archived_at: "2024-01-02T00:00:00Z" } })

    const result = await orphanedDiscussionsService.archive("my-workspace", 1)

    expect(result.archived_at).toBe("2024-01-02T00:00:00Z")
    expect(mockPost).toHaveBeenCalledWith("/api/v1/workspaces/my-workspace/orphaned-discussions/1/archive")
  })

  it("permanently deletes a thread", async () => {
    mockDelete.mockResolvedValue({ data: undefined })

    await orphanedDiscussionsService.delete("my-workspace", 1)

    expect(mockDelete).toHaveBeenCalledWith("/api/v1/workspaces/my-workspace/orphaned-discussions/1")
  })

  it("bulk-acts on multiple threads", async () => {
    mockPost.mockResolvedValue({ data: { results: [{ thread_id: 1, success: true }] } })

    const result = await orphanedDiscussionsService.bulkAction("my-workspace", [1, 2], "archive")

    expect(result).toEqual([{ thread_id: 1, success: true }])
    expect(mockPost).toHaveBeenCalledWith("/api/v1/workspaces/my-workspace/orphaned-discussions/bulk-action", {
      thread_ids: [1, 2],
      action: "archive",
      block_id: null,
    })
  })

  it("fetches the audit log", async () => {
    const entry = { id: 1, kind: "comment.orphan_archived", actor_id: 2, subject: {}, created_at: "2024-01-01" }
    mockGet.mockResolvedValue({ data: [entry] })

    const result = await orphanedDiscussionsService.auditLog("my-workspace")

    expect(result).toEqual([entry])
    expect(mockGet).toHaveBeenCalledWith("/api/v1/workspaces/my-workspace/orphaned-discussions/audit-log", {
      params: {},
    })
  })
})
