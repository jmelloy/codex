import apiClient from "./api"

export interface Notification {
  id: number
  event_id: number
  kind: string
  workspace_id: number
  actor_id: number | null
  subject: Record<string, any>
  read_at: string | null
  created_at: string
}

export const notificationService = {
  async list(unreadOnly = false, limit = 50, offset = 0): Promise<Notification[]> {
    const response = await apiClient.get<Notification[]>("/api/v1/notifications/", {
      params: { unread_only: unreadOnly, limit, offset },
    })
    return response.data
  },

  async unreadCount(): Promise<number> {
    const response = await apiClient.get<{ unread_count: number }>("/api/v1/notifications/unread-count")
    return response.data.unread_count
  },

  async markRead(notificationId: number): Promise<Notification> {
    const response = await apiClient.post<Notification>(`/api/v1/notifications/${notificationId}/read`)
    return response.data
  },

  async markAllRead(): Promise<void> {
    await apiClient.post("/api/v1/notifications/mark-all-read")
  },
}
