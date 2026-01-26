/**
 * Query service for executing dynamic view queries
 */

import apiClient from "./api"
import type { ViewQuery } from "./viewParser"
import type { FileMetadata } from "./codex"

export interface QueryResult {
  files: FileMetadata[]
  groups?: Record<string, FileMetadata[]>
  total: number
  limit: number
  offset: number
}

export const queryService = {
  /**
   * Execute a view query
   */
  async execute(workspaceId: number, query: ViewQuery): Promise<QueryResult> {
    const response = await apiClient.post<QueryResult>(
      `/api/v1/query/?workspace_id=${workspaceId}`,
      query
    )
    return response.data
  },

  /**
   * Execute a query and return only files (no grouping)
   */
  async queryFiles(workspaceId: number, query: ViewQuery): Promise<FileMetadata[]> {
    const result = await this.execute(workspaceId, query)
    return result.files
  },

  /**
   * Execute a query with grouping
   */
  async queryWithGroups(
    workspaceId: number,
    query: ViewQuery
  ): Promise<Record<string, FileMetadata[]>> {
    const result = await this.execute(workspaceId, query)
    return result.groups || {}
  },
}
