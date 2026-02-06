import { defineStore } from "pinia"
import { ref, computed } from "vue"
import {
  agentService,
  type Agent,
  type AgentCreate,
  type AgentUpdate,
  type AgentSession,
  type SessionMessageResponse,
  type ActionLog,
  type Credential,
} from "../services/agent"

export interface ChatMessage {
  role: "user" | "assistant" | "tool" | "system"
  content: string
  toolCalls?: Array<{
    id: string
    name: string
    arguments: Record<string, any>
  }>
  toolCallId?: string
  timestamp: Date
}

export const useAgentStore = defineStore("agent", () => {
  // State
  const agents = ref<Agent[]>([])
  const currentAgent = ref<Agent | null>(null)
  const currentSession = ref<AgentSession | null>(null)
  const sessions = ref<AgentSession[]>([])
  const chatMessages = ref<ChatMessage[]>([])
  const actionLogs = ref<ActionLog[]>([])
  const credentials = ref<Credential[]>([])
  const loading = ref(false)
  const sessionLoading = ref(false)
  const sendingMessage = ref(false)
  const error = ref<string | null>(null)
  const chatOpen = ref(false)

  // Computed
  const activeAgents = computed(() => agents.value.filter((a) => a.is_active))
  const hasActiveSession = computed(
    () =>
      currentSession.value !== null &&
      !["completed", "failed", "cancelled"].includes(currentSession.value.status)
  )

  // Agent CRUD

  async function fetchAgents(workspaceId: number) {
    loading.value = true
    error.value = null
    try {
      agents.value = await agentService.list(workspaceId)
    } catch (e: any) {
      error.value = e.response?.data?.detail || "Failed to fetch agents"
    } finally {
      loading.value = false
    }
  }

  async function createAgent(workspaceId: number, data: AgentCreate) {
    loading.value = true
    error.value = null
    try {
      const agent = await agentService.create(workspaceId, data)
      agents.value.push(agent)
      return agent
    } catch (e: any) {
      error.value = e.response?.data?.detail || "Failed to create agent"
      throw e
    } finally {
      loading.value = false
    }
  }

  async function updateAgent(agentId: number, data: AgentUpdate) {
    loading.value = true
    error.value = null
    try {
      const updated = await agentService.update(agentId, data)
      const idx = agents.value.findIndex((a) => a.id === agentId)
      if (idx !== -1) {
        agents.value[idx] = updated
      }
      if (currentAgent.value?.id === agentId) {
        currentAgent.value = updated
      }
      return updated
    } catch (e: any) {
      error.value = e.response?.data?.detail || "Failed to update agent"
      throw e
    } finally {
      loading.value = false
    }
  }

  async function deleteAgent(agentId: number) {
    loading.value = true
    error.value = null
    try {
      await agentService.delete(agentId)
      agents.value = agents.value.filter((a) => a.id !== agentId)
      if (currentAgent.value?.id === agentId) {
        currentAgent.value = null
      }
    } catch (e: any) {
      error.value = e.response?.data?.detail || "Failed to delete agent"
      throw e
    } finally {
      loading.value = false
    }
  }

  async function toggleAgentActive(agentId: number, active: boolean) {
    error.value = null
    try {
      const updated = await agentService.toggleActive(agentId, active)
      const idx = agents.value.findIndex((a) => a.id === agentId)
      if (idx !== -1) {
        agents.value[idx] = updated
      }
      if (currentAgent.value?.id === agentId) {
        currentAgent.value = updated
      }
      return updated
    } catch (e: any) {
      error.value = e.response?.data?.detail || "Failed to toggle agent"
      throw e
    }
  }

  function selectAgent(agent: Agent | null) {
    currentAgent.value = agent
  }

  // Credentials

  async function fetchCredentials(agentId: number) {
    error.value = null
    try {
      credentials.value = await agentService.listCredentials(agentId)
    } catch (e: any) {
      error.value = e.response?.data?.detail || "Failed to fetch credentials"
    }
  }

  async function setCredential(agentId: number, keyName: string, value: string) {
    error.value = null
    try {
      const cred = await agentService.setCredential(agentId, keyName, value)
      const idx = credentials.value.findIndex((c) => c.key_name === keyName)
      if (idx !== -1) {
        credentials.value[idx] = cred
      } else {
        credentials.value.push(cred)
      }
      return cred
    } catch (e: any) {
      error.value = e.response?.data?.detail || "Failed to set credential"
      throw e
    }
  }

  async function deleteCredential(agentId: number, keyName: string) {
    error.value = null
    try {
      await agentService.deleteCredential(agentId, keyName)
      credentials.value = credentials.value.filter((c) => c.key_name !== keyName)
    } catch (e: any) {
      error.value = e.response?.data?.detail || "Failed to delete credential"
      throw e
    }
  }

  // Sessions

  async function fetchSessions(agentId: number) {
    sessionLoading.value = true
    error.value = null
    try {
      sessions.value = await agentService.listSessions(agentId)
    } catch (e: any) {
      error.value = e.response?.data?.detail || "Failed to fetch sessions"
    } finally {
      sessionLoading.value = false
    }
  }

  async function startSession(agentId: number, notebookPath: string) {
    sessionLoading.value = true
    error.value = null
    try {
      const session = await agentService.startSession(agentId, notebookPath)
      currentSession.value = session
      chatMessages.value = []
      actionLogs.value = []
      return session
    } catch (e: any) {
      error.value = e.response?.data?.detail || "Failed to start session"
      throw e
    } finally {
      sessionLoading.value = false
    }
  }

  async function sendMessage(content: string): Promise<SessionMessageResponse> {
    if (!currentSession.value) throw new Error("No active session")

    sendingMessage.value = true
    error.value = null

    // Add user message to chat
    chatMessages.value.push({
      role: "user",
      content,
      timestamp: new Date(),
    })

    try {
      const response = await agentService.sendMessage(
        currentSession.value.id,
        content
      )

      // Update session state
      currentSession.value = {
        ...currentSession.value,
        status: response.status as AgentSession["status"],
      }

      // Add assistant response to chat
      if (response.response) {
        chatMessages.value.push({
          role: "assistant",
          content: response.response,
          timestamp: new Date(),
        })
      }

      // Process messages for tool call display
      for (const msg of response.messages) {
        if (msg.role === "assistant" && msg.tool_calls && msg.tool_calls.length > 0) {
          // Find existing assistant message or add tool call info
          const lastAssistant = [...chatMessages.value]
            .reverse()
            .find((m) => m.role === "assistant")
          if (lastAssistant) {
            lastAssistant.toolCalls = msg.tool_calls
          }
        }
      }

      return response
    } catch (e: any) {
      error.value = e.response?.data?.detail || "Failed to send message"

      // Add error message to chat
      chatMessages.value.push({
        role: "system",
        content: `Error: ${error.value}`,
        timestamp: new Date(),
      })

      throw e
    } finally {
      sendingMessage.value = false
    }
  }

  async function cancelSession() {
    if (!currentSession.value) return
    error.value = null
    try {
      const cancelled = await agentService.cancelSession(currentSession.value.id)
      currentSession.value = cancelled
    } catch (e: any) {
      error.value = e.response?.data?.detail || "Failed to cancel session"
      throw e
    }
  }

  async function fetchSessionLogs(sessionId: number) {
    error.value = null
    try {
      actionLogs.value = await agentService.getSessionLogs(sessionId)
    } catch (e: any) {
      error.value = e.response?.data?.detail || "Failed to fetch logs"
    }
  }

  // Chat panel

  function openChat(agent?: Agent) {
    if (agent) {
      currentAgent.value = agent
    }
    chatOpen.value = true
  }

  function closeChat() {
    chatOpen.value = false
  }

  function clearChat() {
    chatMessages.value = []
    currentSession.value = null
    actionLogs.value = []
  }

  function reset() {
    agents.value = []
    currentAgent.value = null
    currentSession.value = null
    sessions.value = []
    chatMessages.value = []
    actionLogs.value = []
    credentials.value = []
    loading.value = false
    sessionLoading.value = false
    sendingMessage.value = false
    error.value = null
    chatOpen.value = false
  }

  return {
    // State
    agents,
    currentAgent,
    currentSession,
    sessions,
    chatMessages,
    actionLogs,
    credentials,
    loading,
    sessionLoading,
    sendingMessage,
    error,
    chatOpen,
    // Computed
    activeAgents,
    hasActiveSession,
    // Agent CRUD
    fetchAgents,
    createAgent,
    updateAgent,
    deleteAgent,
    toggleAgentActive,
    selectAgent,
    // Credentials
    fetchCredentials,
    setCredential,
    deleteCredential,
    // Sessions
    fetchSessions,
    startSession,
    sendMessage,
    cancelSession,
    fetchSessionLogs,
    // Chat
    openChat,
    closeChat,
    clearChat,
    reset,
  }
})
