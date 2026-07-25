import { defineStore } from "pinia"
import { ref } from "vue"
import { notificationService, type Notification } from "../services/notifications"
import { websocketService } from "../services/websocket"

export const useNotificationStore = defineStore("notifications", () => {
  const notifications = ref<Notification[]>([])
  const unreadCount = ref(0)
  let unsubscribe: (() => void) | null = null

  async function fetchUnreadCount() {
    try {
      unreadCount.value = await notificationService.unreadCount()
    } catch {
      // Leave the previous count on failure — badge staleness beats a spurious reset to 0.
    }
  }

  async function fetchRecent() {
    try {
      notifications.value = await notificationService.list()
    } catch {
      notifications.value = []
    }
  }

  async function markRead(notificationId: number) {
    const target = notifications.value.find((n) => n.id === notificationId)
    if (target?.read_at) return
    try {
      const updated = await notificationService.markRead(notificationId)
      const idx = notifications.value.findIndex((n) => n.id === notificationId)
      if (idx !== -1) notifications.value[idx] = updated
      unreadCount.value = Math.max(0, unreadCount.value - 1)
    } catch {
      // Leave state as-is; the next fetch will reconcile.
    }
  }

  async function markAllRead() {
    try {
      await notificationService.markAllRead()
      notifications.value = notifications.value.map((n) => ({
        ...n,
        read_at: n.read_at ?? new Date().toISOString(),
      }))
      unreadCount.value = 0
    } catch {
      // Leave state as-is; the next fetch will reconcile.
    }
  }

  function handleIncoming(notification: Notification) {
    notifications.value = [notification, ...notifications.value]
    if (!notification.read_at) {
      unreadCount.value += 1
    }
  }

  /** Wire up the live WebSocket listener. Idempotent — safe to call on every mount. */
  function init() {
    if (unsubscribe) return
    unsubscribe = websocketService.onNotification(handleIncoming)
  }

  function teardown() {
    unsubscribe?.()
    unsubscribe = null
  }

  return {
    notifications,
    unreadCount,
    fetchUnreadCount,
    fetchRecent,
    markRead,
    markAllRead,
    handleIncoming,
    init,
    teardown,
  }
})
