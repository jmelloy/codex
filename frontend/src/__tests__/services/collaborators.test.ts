import { describe, it, expect, beforeEach, vi, type Mock } from "vitest"
import apiClient from "../../services/api"
import { collaboratorService } from "../../services/collaborators"

vi.mock("../../services/api", () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}))

const mockGet = apiClient.get as Mock
const mockPost = apiClient.post as Mock
const mockPatch = apiClient.patch as Mock
const mockDelete = apiClient.delete as Mock

const mockCollaborator = {
  user_id: 2,
  username: "jane",
  email: "jane@example.com",
  permission_level: "write" as const,
  is_owner: false,
  created_at: "2024-01-01T00:00:00Z",
}

describe("collaboratorService", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("lists collaborators for a workspace", async () => {
    mockGet.mockResolvedValue({ data: [mockCollaborator] })

    const result = await collaboratorService.list("my-workspace")

    expect(result).toEqual([mockCollaborator])
    expect(mockGet).toHaveBeenCalledWith("/api/v1/workspaces/my-workspace/collaborators")
  })

  it("invites a collaborator by username or email", async () => {
    mockPost.mockResolvedValue({ data: mockCollaborator })

    const result = await collaboratorService.invite("my-workspace", "jane", "write")

    expect(result).toEqual(mockCollaborator)
    expect(mockPost).toHaveBeenCalledWith("/api/v1/workspaces/my-workspace/collaborators", {
      username_or_email: "jane",
      permission_level: "write",
    })
  })

  it("updates a collaborator's permission level", async () => {
    const updated = { ...mockCollaborator, permission_level: "admin" as const }
    mockPatch.mockResolvedValue({ data: updated })

    const result = await collaboratorService.updateLevel("my-workspace", 2, "admin")

    expect(result).toEqual(updated)
    expect(mockPatch).toHaveBeenCalledWith("/api/v1/workspaces/my-workspace/collaborators/2", {
      permission_level: "admin",
    })
  })

  it("revokes a collaborator", async () => {
    mockDelete.mockResolvedValue({ data: undefined })

    await collaboratorService.revoke("my-workspace", 2)

    expect(mockDelete).toHaveBeenCalledWith("/api/v1/workspaces/my-workspace/collaborators/2")
  })
})
