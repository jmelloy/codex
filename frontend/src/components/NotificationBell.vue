<template>
  <div class="notification-bell-wrapper">
    <button
      class="notification-bell-btn"
      title="Notifications"
      @click="toggleOpen"
    >
      <svg
        xmlns="http://www.w3.org/2000/svg"
        width="18"
        height="18"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        stroke-linecap="round"
        stroke-linejoin="round"
      >
        <path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"></path>
        <path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"></path>
      </svg>
      <span v-if="store.unreadCount > 0" class="notification-badge">
        {{ store.unreadCount > 99 ? "99+" : store.unreadCount }}
      </span>
    </button>

    <div v-if="open" class="notification-dropdown" @click.stop>
      <div class="notification-dropdown-header">
        <span class="notification-dropdown-title">Notifications</span>
        <button
          v-if="store.unreadCount > 0"
          class="notification-mark-all-btn"
          @click="store.markAllRead()"
        >
          Mark all read
        </button>
      </div>
      <div v-if="store.notifications.length === 0" class="notification-empty">No notifications yet</div>
      <ul v-else class="notification-list">
        <li
          v-for="notification in store.notifications"
          :key="notification.id"
          class="notification-row"
          :class="{ unread: !notification.read_at }"
          @click="store.markRead(notification.id)"
        >
          <span class="notification-summary">{{ describe(notification) }}</span>
          <span class="notification-time">{{ formatTime(notification.created_at) }}</span>
        </li>
      </ul>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref } from "vue"
import { useNotificationStore } from "../stores/notifications"
import type { Notification } from "../services/notifications"

const store = useNotificationStore()
const open = ref(false)

const KIND_LABELS: Record<string, string> = {
  "comment.created": "New comment",
  "comment.mention": "You were mentioned in a comment",
  "comment.resolved": "A comment thread was resolved",
  "permission.granted": "You were granted workspace access",
}

function describe(notification: Notification): string {
  return KIND_LABELS[notification.kind] || notification.kind
}

function formatTime(iso: string): string {
  try {
    return new Date(iso).toLocaleString()
  } catch {
    return iso
  }
}

function toggleOpen() {
  open.value = !open.value
  if (open.value) {
    store.fetchRecent()
  }
}

function handleOutsideClick(event: MouseEvent) {
  if (!(event.target as HTMLElement)?.closest(".notification-bell-wrapper")) {
    open.value = false
  }
}

onMounted(() => {
  store.init()
  store.fetchUnreadCount()
  document.addEventListener("click", handleOutsideClick)
})

onUnmounted(() => {
  document.removeEventListener("click", handleOutsideClick)
  store.teardown()
})
</script>

<style scoped>
.notification-bell-wrapper {
  position: relative;
}

.notification-bell-btn {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: var(--color-text-secondary, #666);
  cursor: pointer;
  transition: background-color 0.15s, color 0.15s;
}

.notification-bell-btn:hover {
  background: var(--color-bg-hover, #f0f0f0);
  color: var(--color-text-primary, #333);
}

.notification-badge {
  position: absolute;
  top: -2px;
  right: -2px;
  min-width: 15px;
  height: 15px;
  padding: 0 3px;
  border-radius: 8px;
  background: var(--color-error, #dc2626);
  color: white;
  font-size: 0.625rem;
  font-weight: 700;
  line-height: 15px;
  text-align: center;
}

.notification-dropdown {
  position: absolute;
  top: calc(100% + 6px);
  right: 0;
  z-index: 60;
  width: 320px;
  max-height: 400px;
  display: flex;
  flex-direction: column;
  background: var(--color-bg-primary, #fff);
  border: 1px solid var(--color-border-light, #e0e0e0);
  border-radius: 8px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
  overflow: hidden;
}

.notification-dropdown-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  border-bottom: 1px solid var(--color-border-light, #e0e0e0);
}

.notification-dropdown-title {
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--color-text-primary, #333);
}

.notification-mark-all-btn {
  border: none;
  background: transparent;
  color: var(--notebook-accent, #2563eb);
  font-size: 0.75rem;
  cursor: pointer;
  padding: 0;
}

.notification-mark-all-btn:hover {
  text-decoration: underline;
}

.notification-empty {
  padding: 20px 12px;
  text-align: center;
  font-size: 0.8125rem;
  color: var(--color-text-tertiary, #999);
}

.notification-list {
  list-style: none;
  margin: 0;
  padding: 0;
  overflow-y: auto;
}

.notification-row {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 10px 12px;
  cursor: pointer;
  border-bottom: 1px solid var(--color-border-light, #f0f0f0);
}

.notification-row:last-child {
  border-bottom: none;
}

.notification-row:hover {
  background: var(--color-bg-hover, #f5f5f5);
}

.notification-row.unread {
  background: color-mix(in srgb, var(--notebook-accent, #2563eb) 6%, transparent);
}

.notification-summary {
  font-size: 0.8125rem;
  color: var(--color-text-primary, #333);
}

.notification-time {
  font-size: 0.6875rem;
  color: var(--color-text-tertiary, #999);
}
</style>
