import apiClient from "./api"

export type PermissionLevel = "read" | "comment" | "write" | "admin"

export interface Collaborator {
  user_id: number
  username: string
  email: string
  permission_level: PermissionLevel
  is_owner: boolean
  created_at?: string | null
}

export const collaboratorService = {
  async list(workspaceIdentifier: string): Promise<Collaborator[]> {
    const response = await apiClient.get<Collaborator[]>(
      `/api/v1/workspaces/${workspaceIdentifier}/collaborators`
    )
    return response.data
  },

  async invite(
    workspaceIdentifier: string,
    usernameOrEmail: string,
    permissionLevel: PermissionLevel
  ): Promise<Collaborator> {
    const response = await apiClient.post<Collaborator>(
      `/api/v1/workspaces/${workspaceIdentifier}/collaborators`,
      { username_or_email: usernameOrEmail, permission_level: permissionLevel }
    )
    return response.data
  },

  async updateLevel(
    workspaceIdentifier: string,
    userId: number,
    permissionLevel: PermissionLevel
  ): Promise<Collaborator> {
    const response = await apiClient.patch<Collaborator>(
      `/api/v1/workspaces/${workspaceIdentifier}/collaborators/${userId}`,
      { permission_level: permissionLevel }
    )
    return response.data
  },

  async revoke(workspaceIdentifier: string, userId: number): Promise<void> {
    await apiClient.delete(`/api/v1/workspaces/${workspaceIdentifier}/collaborators/${userId}`)
  },
}
