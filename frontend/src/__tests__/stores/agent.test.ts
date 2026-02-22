import { describe, it, expect, beforeEach, vi } from "vitest"
import { setActivePinia, createPinia } from "pinia"
import { useAgentStore } from "../../stores/agent"
import { agentService, type Agent, type AgentSession, type Credential, type ActionLog } from "../../services/agent"

vi.mock("../../services/agent", () => ({
  agentService: {
    list: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
    delete: vi.fn(),
    toggleActive: vi.fn(),
    listCredentials: vi.fn(),
    setCredential: vi.fn(),
    deleteCredential: vi.fn(),
    listSessions: vi.fn(),
    startSession: vi.fn(),
    sendMessage: vi.fn(),
    cancelSession: vi.fn(),
    getSessionLogs: vi.fn(),
  },
}))

const mockAgent: Agent = {
  id: 1,
  workspace_id: 1,
  name: "Test Agent",
  description: "A test agent",
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

const mockAgent2: Agent = {
  ...mockAgent,
  id: 2,
  name: "Inactive Agent",
  is_active: false,
}

const mockSession: AgentSession = {
  id: 10,
  agent_id: 1,
  task_id: null,
  user_id: 1,
  status: "running",
  tokens_used: 0,
  api_calls_made: 0,
  files_modified: [],
  started_at: "2024-01-01T00:00:00Z",
  completed_at: null,
  error_message: null,
}

const mockCredential: Credential = {
  id: 1,
  key_name: "API_KEY",
  created_at: "2024-01-01T00:00:00Z",
}

describe("Agent Store", () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it("initializes with correct default values", () => {
    const store = useAgentStore()
    expect(store.agents).toEqual([])
    expect(store.currentAgent).toBeNull()
    expect(store.currentSession).toBeNull()
    expect(store.sessions).toEqual([])
    expect(store.chatMessages).toEqual([])
    expect(store.actionLogs).toEqual([])
    expect(store.credentials).toEqual([])
    expect(store.loading).toBe(false)
    expect(store.sessionLoading).toBe(false)
    expect(store.sendingMessage).toBe(false)
    expect(store.error).toBeNull()
    expect(store.chatOpen).toBe(false)
  })

  describe("computed properties", () => {
    it("activeAgents filters only active agents", () => {
      const store = useAgentStore()
      store.agents = [mockAgent, mockAgent2]
      expect(store.activeAgents).toEqual([mockAgent])
    })

    it("hasActiveSession returns true for running session", () => {
      const store = useAgentStore()
      store.currentSession = mockSession
      expect(store.hasActiveSession).toBe(true)
    })

    it("hasActiveSession returns false for completed session", () => {
      const store = useAgentStore()
      store.currentSession = { ...mockSession, status: "completed" }
      expect(store.hasActiveSession).toBe(false)
    })

    it("hasActiveSession returns false for failed/cancelled sessions", () => {
      const store = useAgentStore()
      store.currentSession = { ...mockSession, status: "failed" }
      expect(store.hasActiveSession).toBe(false)
      store.currentSession = { ...mockSession, status: "cancelled" }
      expect(store.hasActiveSession).toBe(false)
    })

    it("hasActiveSession returns false when no session", () => {
      const store = useAgentStore()
      expect(store.hasActiveSession).toBe(false)
    })
  })

  describe("fetchAgents", () => {
    it("fetches agents successfully", async () => {
      const store = useAgentStore()
      vi.mocked(agentService.list).mockResolvedValue([mockAgent, mockAgent2])

      await store.fetchAgents(1)

      expect(agentService.list).toHaveBeenCalledWith(1)
      expect(store.agents).toEqual([mockAgent, mockAgent2])
      expect(store.loading).toBe(false)
      expect(store.error).toBeNull()
    })

    it("sets error on fetch failure", async () => {
      const store = useAgentStore()
      vi.mocked(agentService.list).mockRejectedValue({
        response: { data: { detail: "Unauthorized" } },
      })

      await store.fetchAgents(1)

      expect(store.error).toBe("Unauthorized")
      expect(store.loading).toBe(false)
    })

    it("uses fallback error message when no detail", async () => {
      const store = useAgentStore()
      vi.mocked(agentService.list).mockRejectedValue(new Error("Network"))

      await store.fetchAgents(1)

      expect(store.error).toBe("Failed to fetch agents")
    })
  })

  describe("createAgent", () => {
    it("creates agent and adds to list", async () => {
      const store = useAgentStore()
      vi.mocked(agentService.create).mockResolvedValue(mockAgent)

      const result = await store.createAgent(1, {
        name: "Test Agent",
        provider: "openai",
        model: "gpt-4",
      })

      expect(result).toEqual(mockAgent)
      expect(store.agents).toContainEqual(mockAgent)
      expect(store.loading).toBe(false)
    })

    it("sets error and rethrows on failure", async () => {
      const store = useAgentStore()
      vi.mocked(agentService.create).mockRejectedValue({
        response: { data: { detail: "Validation error" } },
      })

      await expect(
        store.createAgent(1, { name: "Test", provider: "openai", model: "gpt-4" })
      ).rejects.toBeTruthy()

      expect(store.error).toBe("Validation error")
    })
  })

  describe("updateAgent", () => {
    it("updates agent in list", async () => {
      const store = useAgentStore()
      store.agents = [mockAgent]
      const updated = { ...mockAgent, name: "Updated Agent" }
      vi.mocked(agentService.update).mockResolvedValue(updated)

      const result = await store.updateAgent(1, { name: "Updated Agent" })

      expect(result).toEqual(updated)
      expect(store.agents[0].name).toBe("Updated Agent")
    })

    it("updates currentAgent if it matches", async () => {
      const store = useAgentStore()
      store.agents = [mockAgent]
      store.currentAgent = mockAgent
      const updated = { ...mockAgent, name: "Updated" }
      vi.mocked(agentService.update).mockResolvedValue(updated)

      await store.updateAgent(1, { name: "Updated" })

      expect(store.currentAgent!.name).toBe("Updated")
    })

    it("does not update currentAgent if id doesn't match", async () => {
      const store = useAgentStore()
      store.agents = [mockAgent, mockAgent2]
      store.currentAgent = mockAgent2
      const updated = { ...mockAgent, name: "Updated" }
      vi.mocked(agentService.update).mockResolvedValue(updated)

      await store.updateAgent(1, { name: "Updated" })

      expect(store.currentAgent!.name).toBe("Inactive Agent")
    })
  })

  describe("deleteAgent", () => {
    it("removes agent from list", async () => {
      const store = useAgentStore()
      store.agents = [mockAgent, mockAgent2]
      vi.mocked(agentService.delete).mockResolvedValue()

      await store.deleteAgent(1)

      expect(store.agents).toHaveLength(1)
      expect(store.agents[0].id).toBe(2)
    })

    it("clears currentAgent if deleted agent was selected", async () => {
      const store = useAgentStore()
      store.agents = [mockAgent]
      store.currentAgent = mockAgent
      vi.mocked(agentService.delete).mockResolvedValue()

      await store.deleteAgent(1)

      expect(store.currentAgent).toBeNull()
    })

    it("keeps currentAgent if different agent is deleted", async () => {
      const store = useAgentStore()
      store.agents = [mockAgent, mockAgent2]
      store.currentAgent = mockAgent
      vi.mocked(agentService.delete).mockResolvedValue()

      await store.deleteAgent(2)

      expect(store.currentAgent).toEqual(mockAgent)
    })
  })

  describe("toggleAgentActive", () => {
    it("toggles agent active status", async () => {
      const store = useAgentStore()
      store.agents = [mockAgent]
      const toggled = { ...mockAgent, is_active: false }
      vi.mocked(agentService.toggleActive).mockResolvedValue(toggled)

      const result = await store.toggleAgentActive(1, false)

      expect(result).toEqual(toggled)
      expect(store.agents[0].is_active).toBe(false)
    })
  })

  describe("selectAgent", () => {
    it("sets currentAgent", () => {
      const store = useAgentStore()
      store.selectAgent(mockAgent)
      expect(store.currentAgent).toEqual(mockAgent)
    })

    it("clears currentAgent when null", () => {
      const store = useAgentStore()
      store.currentAgent = mockAgent
      store.selectAgent(null)
      expect(store.currentAgent).toBeNull()
    })
  })

  describe("credentials", () => {
    it("fetches credentials", async () => {
      const store = useAgentStore()
      vi.mocked(agentService.listCredentials).mockResolvedValue([mockCredential])

      await store.fetchCredentials(1)

      expect(store.credentials).toEqual([mockCredential])
    })

    it("sets a new credential", async () => {
      const store = useAgentStore()
      vi.mocked(agentService.setCredential).mockResolvedValue(mockCredential)

      const result = await store.setCredential(1, "API_KEY", "secret")

      expect(result).toEqual(mockCredential)
      expect(store.credentials).toContainEqual(mockCredential)
    })

    it("updates existing credential", async () => {
      const store = useAgentStore()
      store.credentials = [mockCredential]
      const updated = { ...mockCredential, id: 2 }
      vi.mocked(agentService.setCredential).mockResolvedValue(updated)

      await store.setCredential(1, "API_KEY", "new-secret")

      expect(store.credentials).toHaveLength(1)
      expect(store.credentials[0].id).toBe(2)
    })

    it("deletes a credential", async () => {
      const store = useAgentStore()
      store.credentials = [mockCredential]
      vi.mocked(agentService.deleteCredential).mockResolvedValue()

      await store.deleteCredential(1, "API_KEY")

      expect(store.credentials).toHaveLength(0)
    })
  })

  describe("sessions", () => {
    it("fetches sessions", async () => {
      const store = useAgentStore()
      vi.mocked(agentService.listSessions).mockResolvedValue([mockSession])

      await store.fetchSessions(1)

      expect(store.sessions).toEqual([mockSession])
      expect(store.sessionLoading).toBe(false)
    })

    it("starts a session and clears chat", async () => {
      const store = useAgentStore()
      store.chatMessages = [{ role: "user", content: "old", timestamp: new Date() }]
      vi.mocked(agentService.startSession).mockResolvedValue(mockSession)

      const result = await store.startSession(1, "/notebook/path")

      expect(result).toEqual(mockSession)
      expect(store.currentSession).toEqual(mockSession)
      expect(store.chatMessages).toEqual([])
      expect(store.actionLogs).toEqual([])
    })

    it("cancels a session", async () => {
      const store = useAgentStore()
      store.currentSession = mockSession
      const cancelled = { ...mockSession, status: "cancelled" as const }
      vi.mocked(agentService.cancelSession).mockResolvedValue(cancelled)

      await store.cancelSession()

      expect(store.currentSession!.status).toBe("cancelled")
    })

    it("does nothing when cancelling without active session", async () => {
      const store = useAgentStore()
      await store.cancelSession()
      expect(agentService.cancelSession).not.toHaveBeenCalled()
    })

    it("fetches session logs", async () => {
      const store = useAgentStore()
      const logs: ActionLog[] = [{
        id: 1,
        session_id: 10,
        action_type: "read_file",
        target_path: "/test.md",
        input_summary: null,
        output_summary: null,
        was_allowed: true,
        execution_time_ms: 50,
        created_at: "2024-01-01T00:00:00Z",
      }]
      vi.mocked(agentService.getSessionLogs).mockResolvedValue(logs)

      await store.fetchSessionLogs(10)

      expect(store.actionLogs).toEqual(logs)
    })
  })

  describe("sendMessage", () => {
    it("throws if no active session", async () => {
      const store = useAgentStore()
      await expect(store.sendMessage("hello")).rejects.toThrow("No active session")
    })

    it("sends message and updates chat", async () => {
      const store = useAgentStore()
      store.currentSession = mockSession

      vi.mocked(agentService.sendMessage).mockResolvedValue({
        session_id: 10,
        status: "running",
        response: "Hello back!",
        messages: [],
        action_logs: [],
      })

      await store.sendMessage("hello")

      expect(store.chatMessages).toHaveLength(2)
      expect(store.chatMessages[0].role).toBe("user")
      expect(store.chatMessages[0].content).toBe("hello")
      expect(store.chatMessages[1].role).toBe("assistant")
      expect(store.chatMessages[1].content).toBe("Hello back!")
      expect(store.sendingMessage).toBe(false)
    })

    it("handles tool calls in response messages", async () => {
      const store = useAgentStore()
      store.currentSession = mockSession

      vi.mocked(agentService.sendMessage).mockResolvedValue({
        session_id: 10,
        status: "running",
        response: "I'll read that file",
        messages: [
          {
            role: "assistant",
            content: "I'll read that file",
            tool_calls: [{ id: "tc1", name: "read_file", arguments: { path: "/test.md" } }],
          },
        ],
        action_logs: [],
      })

      await store.sendMessage("read test.md")

      const assistantMsg = store.chatMessages.find((m) => m.role === "assistant")
      expect(assistantMsg?.toolCalls).toHaveLength(1)
      expect(assistantMsg?.toolCalls![0].name).toBe("read_file")
    })

    it("adds error message to chat on failure", async () => {
      const store = useAgentStore()
      store.currentSession = mockSession

      vi.mocked(agentService.sendMessage).mockRejectedValue({
        response: { data: { detail: "Rate limited" } },
      })

      await expect(store.sendMessage("hello")).rejects.toBeTruthy()

      expect(store.chatMessages).toHaveLength(2)
      expect(store.chatMessages[1].role).toBe("system")
      expect(store.chatMessages[1].content).toContain("Rate limited")
    })
  })

  describe("chat panel", () => {
    it("opens chat", () => {
      const store = useAgentStore()
      store.openChat()
      expect(store.chatOpen).toBe(true)
    })

    it("opens chat with agent", () => {
      const store = useAgentStore()
      store.openChat(mockAgent)
      expect(store.chatOpen).toBe(true)
      expect(store.currentAgent).toEqual(mockAgent)
    })

    it("closes chat", () => {
      const store = useAgentStore()
      store.chatOpen = true
      store.closeChat()
      expect(store.chatOpen).toBe(false)
    })

    it("clears chat state", () => {
      const store = useAgentStore()
      store.chatMessages = [{ role: "user", content: "test", timestamp: new Date() }]
      store.currentSession = mockSession
      store.actionLogs = [{ id: 1 } as ActionLog]

      store.clearChat()

      expect(store.chatMessages).toEqual([])
      expect(store.currentSession).toBeNull()
      expect(store.actionLogs).toEqual([])
    })
  })

  describe("reset", () => {
    it("resets all state to defaults", () => {
      const store = useAgentStore()
      store.agents = [mockAgent]
      store.currentAgent = mockAgent
      store.currentSession = mockSession
      store.sessions = [mockSession]
      store.chatMessages = [{ role: "user", content: "test", timestamp: new Date() }]
      store.actionLogs = [{ id: 1 } as ActionLog]
      store.credentials = [mockCredential]
      store.loading = true
      store.sessionLoading = true
      store.sendingMessage = true
      store.error = "some error"
      store.chatOpen = true

      store.reset()

      expect(store.agents).toEqual([])
      expect(store.currentAgent).toBeNull()
      expect(store.currentSession).toBeNull()
      expect(store.sessions).toEqual([])
      expect(store.chatMessages).toEqual([])
      expect(store.actionLogs).toEqual([])
      expect(store.credentials).toEqual([])
      expect(store.loading).toBe(false)
      expect(store.sessionLoading).toBe(false)
      expect(store.sendingMessage).toBe(false)
      expect(store.error).toBeNull()
      expect(store.chatOpen).toBe(false)
    })
  })
})
