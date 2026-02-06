import apiClient from "./api"

// --- Interfaces ---

export interface AgentScope {
  notebooks: string[]
  folders: string[]
  file_types: string[]
}

export interface Agent {
  id: number
  workspace_id: number
  name: string
  description: string | null
  provider: string
  model: string
  scope: AgentScope
  can_read: boolean
  can_write: boolean
  can_create: boolean
  can_delete: boolean
  can_execute_code: boolean
  can_access_integrations: boolean
  max_requests_per_hour: number
  max_tokens_per_request: number
  is_active: boolean
  system_prompt: string | null
  created_at: string
  updated_at: string
}

export interface AgentCreate {
  name: string
  description?: string
  provider: string
  model: string
  scope?: AgentScope
  can_read?: boolean
  can_write?: boolean
  can_create?: boolean
  can_delete?: boolean
  can_execute_code?: boolean
  can_access_integrations?: boolean
  max_requests_per_hour?: number
  max_tokens_per_request?: number
  system_prompt?: string
}

export interface AgentUpdate {
  name?: string
  description?: string | null
  provider?: string
  model?: string
  scope?: AgentScope
  can_read?: boolean
  can_write?: boolean
  can_create?: boolean
  can_delete?: boolean
  can_execute_code?: boolean
  can_access_integrations?: boolean
  max_requests_per_hour?: number
  max_tokens_per_request?: number
  is_active?: boolean
  system_prompt?: string | null
}

export interface Credential {
  id: number
  key_name: string
  created_at: string
}

export interface AgentSession {
  id: number
  agent_id: number
  task_id: number | null
  user_id: number
  status: "pending" | "running" | "completed" | "failed" | "cancelled"
  tokens_used: number
  api_calls_made: number
  files_modified: string[]
  started_at: string
  completed_at: string | null
  error_message: string | null
}

export interface SessionMessage {
  role: "system" | "user" | "assistant" | "tool"
  content: string | null
  tool_calls?: Array<{
    id: string
    name: string
    arguments: Record<string, any>
  }>
  tool_call_id?: string
}

export interface ActionLog {
  id: number
  session_id: number
  action_type: string
  target_path: string | null
  input_summary: string | null
  output_summary: string | null
  was_allowed: boolean
  execution_time_ms: number
  created_at: string
}

export interface SessionMessageResponse {
  session_id: number
  status: string
  response: string
  messages: SessionMessage[]
  action_logs: Array<Record<string, any>>
}

// --- Service ---

export const agentService = {
  // Agent CRUD

  async list(workspaceId: number): Promise<Agent[]> {
    const response = await apiClient.get<Agent[]>(
      `/api/v1/agents/?workspace_id=${workspaceId}`
    )
    return response.data
  },

  async get(agentId: number): Promise<Agent> {
    const response = await apiClient.get<Agent>(`/api/v1/agents/${agentId}`)
    return response.data
  },

  async create(workspaceId: number, data: AgentCreate): Promise<Agent> {
    const response = await apiClient.post<Agent>(
      `/api/v1/agents/?workspace_id=${workspaceId}`,
      data
    )
    return response.data
  },

  async update(agentId: number, data: AgentUpdate): Promise<Agent> {
    const response = await apiClient.put<Agent>(
      `/api/v1/agents/${agentId}`,
      data
    )
    return response.data
  },

  async delete(agentId: number): Promise<void> {
    await apiClient.delete(`/api/v1/agents/${agentId}`)
  },

  async toggleActive(agentId: number, active: boolean): Promise<Agent> {
    const response = await apiClient.post<Agent>(
      `/api/v1/agents/${agentId}/activate?active=${active}`
    )
    return response.data
  },

  // Credentials

  async setCredential(
    agentId: number,
    keyName: string,
    value: string
  ): Promise<Credential> {
    const response = await apiClient.post<Credential>(
      `/api/v1/agents/${agentId}/credentials`,
      { key_name: keyName, value }
    )
    return response.data
  },

  async listCredentials(agentId: number): Promise<Credential[]> {
    const response = await apiClient.get<Credential[]>(
      `/api/v1/agents/${agentId}/credentials`
    )
    return response.data
  },

  async deleteCredential(agentId: number, keyName: string): Promise<void> {
    await apiClient.delete(`/api/v1/agents/${agentId}/credentials/${keyName}`)
  },

  // Sessions

  async startSession(
    agentId: number,
    notebookPath: string,
    taskId?: number
  ): Promise<AgentSession> {
    const response = await apiClient.post<AgentSession>(
      `/api/v1/agents/${agentId}/sessions`,
      { notebook_path: notebookPath, task_id: taskId ?? null }
    )
    return response.data
  },

  async listSessions(agentId: number): Promise<AgentSession[]> {
    const response = await apiClient.get<AgentSession[]>(
      `/api/v1/agents/${agentId}/sessions`
    )
    return response.data
  },

  async getSession(sessionId: number): Promise<AgentSession> {
    const response = await apiClient.get<AgentSession>(
      `/api/v1/sessions/${sessionId}`
    )
    return response.data
  },

  async sendMessage(
    sessionId: number,
    content: string
  ): Promise<SessionMessageResponse> {
    const response = await apiClient.post<SessionMessageResponse>(
      `/api/v1/sessions/${sessionId}/message`,
      { content }
    )
    return response.data
  },

  async cancelSession(sessionId: number): Promise<AgentSession> {
    const response = await apiClient.post<AgentSession>(
      `/api/v1/sessions/${sessionId}/cancel`
    )
    return response.data
  },

  async getSessionLogs(sessionId: number): Promise<ActionLog[]> {
    const response = await apiClient.get<ActionLog[]>(
      `/api/v1/sessions/${sessionId}/logs`
    )
    return response.data
  },
}
