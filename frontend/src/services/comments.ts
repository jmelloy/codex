import apiClient from "./api"
import type { PermissionLevel } from "./collaborators"

export interface CommentMention {
  id: number
  mentioned_principal_id: number
  handle: string
}

export interface Comment {
  id: number
  workspace_id: number
  notebook_id: number
  block_id: string
  thread_id: number | null
  author_id: number
  author_username?: string
  body: string
  resolved_at: string | null
  resolved_by_id: number | null
  created_at: string
  updated_at: string
  mentions: CommentMention[]
}

export interface CommentCount {
  block_id: string
  count: number
}

export interface Principal {
  id: number
  username: string
}

export const commentService = {
  async list(workspaceIdentifier: string, notebookIdentifier: string, blockId: string): Promise<Comment[]> {
    const response = await apiClient.get<Comment[]>(
      `/api/v1/workspaces/${workspaceIdentifier}/notebooks/${notebookIdentifier}/blocks/${blockId}/comments/`,
    )
    return response.data
  },

  async create(
    workspaceIdentifier: string,
    notebookIdentifier: string,
    blockId: string,
    body: string,
    threadId?: number,
  ): Promise<Comment> {
    const response = await apiClient.post<Comment>(
      `/api/v1/workspaces/${workspaceIdentifier}/notebooks/${notebookIdentifier}/blocks/${blockId}/comments/`,
      { body, thread_id: threadId ?? null },
    )
    return response.data
  },

  async update(commentId: number, body: string): Promise<Comment> {
    const response = await apiClient.patch<Comment>(`/api/v1/comments/${commentId}`, { body })
    return response.data
  },

  async delete(commentId: number): Promise<void> {
    await apiClient.delete(`/api/v1/comments/${commentId}`)
  },

  async resolve(commentId: number): Promise<Comment> {
    const response = await apiClient.post<Comment>(`/api/v1/comments/${commentId}/resolve`)
    return response.data
  },

  async counts(workspaceIdentifier: string, notebookIdentifier: string): Promise<CommentCount[]> {
    const response = await apiClient.get<CommentCount[]>(
      `/api/v1/workspaces/${workspaceIdentifier}/notebooks/${notebookIdentifier}/comments/counts`,
    )
    return response.data
  },
}

export const principalService = {
  /** Workspace-visible principals (owner + collaborators), for @mention autocomplete. */
  async list(workspaceIdentifier: string): Promise<Principal[]> {
    const response = await apiClient.get<Principal[]>(`/api/v1/workspaces/${workspaceIdentifier}/principals`)
    return response.data
  },
}

export const permissionService = {
  /** The current user's effective permission level on a workspace. */
  async getMine(workspaceIdentifier: string): Promise<PermissionLevel> {
    const response = await apiClient.get<{ permission_level: PermissionLevel }>(
      `/api/v1/workspaces/${workspaceIdentifier}/permission`,
    )
    return response.data.permission_level
  },
}
