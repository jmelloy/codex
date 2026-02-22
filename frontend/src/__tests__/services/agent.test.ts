import { describe, it, expect, beforeEach, vi, type Mock } from "vitest"
import apiClient from "../../services/api"
import { agentService } from "../../services/agent"

vi.mock("../../services/api", () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}))

const mockGet = apiClient.get as Mock
const mockPost = apiClient.post as Mock
const mockPut = apiClient.put as Mock
const mockDelete = apiClient.delete as Mock

const mockAgent = {
  id: 1,
  workspace_id: 1,
  name: "Test Agent",
  description: null,
  provider: "openai",
  model: "gpt-4",
  scope: { notebooks: [], folders: [], file_types: [] },
  can_read: true,
  can_write: false,
  can_create: false,
  can_delete: false,
  can_execute_code: false,
  can_access_integrations: false,
  max_requests_per_hour: 100,
  max_tokens_per_request: 4096,
  is_active: true,
  system_prompt: null,
  created_at: "2024-01-01T00:00:00Z",
  updated_at: "2024-01-01T00:00:00Z",
}

describe("Agent Service", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe("agent CRUD", () => {
    it("lists agents for a workspace", async () => {
      mockGet.mockResolvedValue({ data: [mockAgent] })

      const result = await agentService.list(1)

      expect(result).toEqual([mockAgent])
      expect(mockGet).toHaveBeenCalledWith("/api/v1/agents/?workspace_id=1")
    })

    it("gets a single agent", async () => {
      mockGet.mockResolvedValue({ data: mockAgent })

      const result = await agentService.get(1)

      expect(result).toEqual(mockAgent)
      expect(mockGet).toHaveBeenCalledWith("/api/v1/agents/1")
    })

    it("creates an agent", async () => {
      mockPost.mockResolvedValue({ data: mockAgent })
      const createData = { name: "Test Agent", provider: "openai", model: "gpt-4" }

      const result = await agentService.create(1, createData)

      expect(result).toEqual(mockAgent)
      expect(mockPost).toHaveBeenCalledWith("/api/v1/agents/?workspace_id=1", createData)
    })

    it("updates an agent", async () => {
      const updated = { ...mockAgent, name: "Updated" }
      mockPut.mockResolvedValue({ data: updated })

      const result = await agentService.update(1, { name: "Updated" })

      expect(result).toEqual(updated)
      expect(mockPut).toHaveBeenCalledWith("/api/v1/agents/1", { name: "Updated" })
    })

    it("deletes an agent", async () => {
      mockDelete.mockResolvedValue({})

      await agentService.delete(1)

      expect(mockDelete).toHaveBeenCalledWith("/api/v1/agents/1")
    })

    it("toggles agent active status", async () => {
      const toggled = { ...mockAgent, is_active: false }
      mockPost.mockResolvedValue({ data: toggled })

      const result = await agentService.toggleActive(1, false)

      expect(result).toEqual(toggled)
      expect(mockPost).toHaveBeenCalledWith("/api/v1/agents/1/activate?active=false")
    })
  })

  describe("credentials", () => {
    it("lists credentials", async () => {
      const creds = [{ id: 1, key_name: "API_KEY", created_at: "2024-01-01T00:00:00Z" }]
      mockGet.mockResolvedValue({ data: creds })

      const result = await agentService.listCredentials(1)

      expect(result).toEqual(creds)
      expect(mockGet).toHaveBeenCalledWith("/api/v1/agents/1/credentials")
    })

    it("sets a credential", async () => {
      const cred = { id: 1, key_name: "API_KEY", created_at: "2024-01-01T00:00:00Z" }
      mockPost.mockResolvedValue({ data: cred })

      const result = await agentService.setCredential(1, "API_KEY", "secret")

      expect(result).toEqual(cred)
      expect(mockPost).toHaveBeenCalledWith("/api/v1/agents/1/credentials", {
        key_name: "API_KEY",
        value: "secret",
      })
    })

    it("deletes a credential", async () => {
      mockDelete.mockResolvedValue({})

      await agentService.deleteCredential(1, "API_KEY")

      expect(mockDelete).toHaveBeenCalledWith("/api/v1/agents/1/credentials/API_KEY")
    })
  })

  describe("sessions", () => {
    it("starts a session", async () => {
      const session = { id: 10, agent_id: 1, status: "running" }
      mockPost.mockResolvedValue({ data: session })

      const result = await agentService.startSession(1, "/notebook/path")

      expect(result).toEqual(session)
      expect(mockPost).toHaveBeenCalledWith("/api/v1/agents/1/sessions", {
        notebook_path: "/notebook/path",
        task_id: null,
      })
    })

    it("starts a session with task id", async () => {
      const session = { id: 10, agent_id: 1, status: "running" }
      mockPost.mockResolvedValue({ data: session })

      await agentService.startSession(1, "/notebook/path", 5)

      expect(mockPost).toHaveBeenCalledWith("/api/v1/agents/1/sessions", {
        notebook_path: "/notebook/path",
        task_id: 5,
      })
    })

    it("lists sessions for an agent", async () => {
      const sessions = [{ id: 10, agent_id: 1, status: "completed" }]
      mockGet.mockResolvedValue({ data: sessions })

      const result = await agentService.listSessions(1)

      expect(result).toEqual(sessions)
      expect(mockGet).toHaveBeenCalledWith("/api/v1/agents/1/sessions")
    })

    it("gets a session by id", async () => {
      const session = { id: 10, agent_id: 1, status: "running" }
      mockGet.mockResolvedValue({ data: session })

      const result = await agentService.getSession(10)

      expect(result).toEqual(session)
      expect(mockGet).toHaveBeenCalledWith("/api/v1/sessions/10")
    })

    it("sends a message to a session", async () => {
      const response = {
        session_id: 10,
        status: "running",
        response: "Hello",
        messages: [],
        action_logs: [],
      }
      mockPost.mockResolvedValue({ data: response })

      const result = await agentService.sendMessage(10, "Hello")

      expect(result).toEqual(response)
      expect(mockPost).toHaveBeenCalledWith("/api/v1/sessions/10/message", { content: "Hello" })
    })

    it("cancels a session", async () => {
      const cancelled = { id: 10, status: "cancelled" }
      mockPost.mockResolvedValue({ data: cancelled })

      const result = await agentService.cancelSession(10)

      expect(result).toEqual(cancelled)
      expect(mockPost).toHaveBeenCalledWith("/api/v1/sessions/10/cancel")
    })

    it("gets session logs", async () => {
      const logs = [{ id: 1, session_id: 10, action_type: "read_file" }]
      mockGet.mockResolvedValue({ data: logs })

      const result = await agentService.getSessionLogs(10)

      expect(result).toEqual(logs)
      expect(mockGet).toHaveBeenCalledWith("/api/v1/sessions/10/logs")
    })
  })
})
