import apiClient from "./api"

export type OrphanReason = "block_deleted" | "root_deleted"

export interface OrphanedComment {
  id: number
  author_id: number
  author_username?: string | null
  body: string
  created_at: string
  deleted_at: string | null
}

export interface OrphanedThread {
  thread_id: number
  workspace_id: number
  notebook_id: number
  notebook_name: string
  block_id: string
  reason: OrphanReason
  root: OrphanedComment
  replies: OrphanedComment[]
  reply_count: number
  last_activity_at: string
  archived_at: string | null
  archived_by_id: number | null
  archived_by_username?: string | null
}

export interface OrphanedDiscussionFilters {
  notebook_id?: number
  author_id?: number
  start_date?: string
  end_date?: string
  include_archived?: boolean
  limit?: number
  offset?: number
}

export type BulkAction = "archive" | "restore" | "delete"

export interface BulkActionResult {
  thread_id: number
  success: boolean
  detail?: string | null
}

export interface AuditLogEntry {
  id: number
  kind: string
  actor_id: number | null
  actor_username?: string | null
  subject: Record<string, unknown>
  created_at: string
}

export const orphanedDiscussionsService = {
  async list(workspaceIdentifier: string, filters: OrphanedDiscussionFilters = {}): Promise<OrphanedThread[]> {
    const response = await apiClient.get<OrphanedThread[]>(
      `/api/v1/workspaces/${workspaceIdentifier}/orphaned-discussions/`,
      { params: filters },
    )
    return response.data
  },

  async get(workspaceIdentifier: string, threadId: number): Promise<OrphanedThread> {
    const response = await apiClient.get<OrphanedThread>(
      `/api/v1/workspaces/${workspaceIdentifier}/orphaned-discussions/${threadId}`,
    )
    return response.data
  },

  async restore(workspaceIdentifier: string, threadId: number, blockId?: string): Promise<OrphanedThread> {
    const response = await apiClient.post<OrphanedThread>(
      `/api/v1/workspaces/${workspaceIdentifier}/orphaned-discussions/${threadId}/restore`,
      { block_id: blockId ?? null },
    )
    return response.data
  },

  async archive(workspaceIdentifier: string, threadId: number): Promise<OrphanedThread> {
    const response = await apiClient.post<OrphanedThread>(
      `/api/v1/workspaces/${workspaceIdentifier}/orphaned-discussions/${threadId}/archive`,
    )
    return response.data
  },

  async delete(workspaceIdentifier: string, threadId: number): Promise<void> {
    await apiClient.delete(`/api/v1/workspaces/${workspaceIdentifier}/orphaned-discussions/${threadId}`)
  },

  async bulkAction(
    workspaceIdentifier: string,
    threadIds: number[],
    action: BulkAction,
    blockId?: string,
  ): Promise<BulkActionResult[]> {
    const response = await apiClient.post<{ results: BulkActionResult[] }>(
      `/api/v1/workspaces/${workspaceIdentifier}/orphaned-discussions/bulk-action`,
      { thread_ids: threadIds, action, block_id: blockId ?? null },
    )
    return response.data.results
  },

  async auditLog(
    workspaceIdentifier: string,
    params: { limit?: number; offset?: number } = {},
  ): Promise<AuditLogEntry[]> {
    const response = await apiClient.get<AuditLogEntry[]>(
      `/api/v1/workspaces/${workspaceIdentifier}/orphaned-discussions/audit-log`,
      { params },
    )
    return response.data
  },
}
