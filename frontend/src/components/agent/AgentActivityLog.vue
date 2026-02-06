<template>
  <div class="activity-log">
    <div class="log-header">
      <h4 class="log-title">Activity Log</h4>
      <span v-if="sessions.length > 0" class="log-count">{{ sessions.length }} sessions</span>
    </div>

    <div v-if="loading" class="log-loading">Loading sessions...</div>

    <div v-else-if="sessions.length === 0" class="log-empty">
      No sessions yet. Start a chat to create one.
    </div>

    <div v-else class="session-list">
      <div
        v-for="session in sessions"
        :key="session.id"
        :class="['session-card', { 'session-expanded': expandedSession === session.id }]"
      >
        <div class="session-header" @click="toggleSession(session.id)">
          <div class="session-info">
            <span :class="['session-status', `status-${session.status}`]">
              {{ session.status }}
            </span>
            <span class="session-date">{{ formatDate(session.started_at) }}</span>
          </div>
          <div class="session-meta">
            <span v-if="session.tokens_used > 0" class="meta-item">
              {{ session.tokens_used.toLocaleString() }} tokens
            </span>
            <span v-if="session.api_calls_made > 0" class="meta-item">
              {{ session.api_calls_made }} calls
            </span>
            <span v-if="session.files_modified.length > 0" class="meta-item">
              {{ session.files_modified.length }} files
            </span>
            <span class="expand-icon">{{ expandedSession === session.id ? "v" : ">" }}</span>
          </div>
        </div>

        <div v-if="expandedSession === session.id" class="session-details">
          <div v-if="session.error_message" class="session-error">
            {{ session.error_message }}
          </div>

          <div v-if="session.files_modified.length > 0" class="files-modified">
            <strong>Files modified:</strong>
            <ul>
              <li v-for="f in session.files_modified" :key="f" class="file-path">{{ f }}</li>
            </ul>
          </div>

          <div v-if="sessionLogs.length > 0" class="action-logs">
            <strong>Actions:</strong>
            <AgentActionCard
              v-for="log in sessionLogs"
              :key="log.id"
              :action="log"
            />
          </div>
          <div v-else-if="logsLoading" class="logs-loading">Loading action logs...</div>
          <div v-else class="no-logs">No action logs recorded.</div>

          <div class="session-timing">
            <span>Started: {{ formatDateTime(session.started_at) }}</span>
            <span v-if="session.completed_at">
              Completed: {{ formatDateTime(session.completed_at) }}
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from "vue"
import { useAgentStore } from "../../stores/agent"
import AgentActionCard from "./AgentActionCard.vue"
import type { AgentSession, ActionLog } from "../../services/agent"

const props = defineProps<{
  agentId: number
}>()

const agentStore = useAgentStore()
const sessions = ref<AgentSession[]>([])
const sessionLogs = ref<ActionLog[]>([])
const loading = ref(false)
const logsLoading = ref(false)
const expandedSession = ref<number | null>(null)

async function loadSessions() {
  loading.value = true
  try {
    await agentStore.fetchSessions(props.agentId)
    sessions.value = [...agentStore.sessions]
  } finally {
    loading.value = false
  }
}

async function toggleSession(sessionId: number) {
  if (expandedSession.value === sessionId) {
    expandedSession.value = null
    sessionLogs.value = []
    return
  }

  expandedSession.value = sessionId
  logsLoading.value = true
  try {
    await agentStore.fetchSessionLogs(sessionId)
    sessionLogs.value = [...agentStore.actionLogs]
  } finally {
    logsLoading.value = false
  }
}

function formatDate(dateStr: string): string {
  const d = new Date(dateStr)
  const now = new Date()
  const diff = now.getTime() - d.getTime()
  const hours = Math.floor(diff / (1000 * 60 * 60))

  if (hours < 1) {
    const mins = Math.floor(diff / (1000 * 60))
    return mins < 1 ? "just now" : `${mins}m ago`
  }
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  if (days < 7) return `${days}d ago`
  return d.toLocaleDateString()
}

function formatDateTime(dateStr: string): string {
  return new Date(dateStr).toLocaleString()
}

watch(() => props.agentId, loadSessions, { immediate: true })
</script>

<style scoped>
.activity-log {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.log-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.log-title {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
  color: var(--color-text-primary);
}

.log-count {
  font-size: 0.8125rem;
  color: var(--color-text-tertiary);
}

.log-loading,
.log-empty {
  padding: 2rem;
  text-align: center;
  color: var(--color-text-tertiary);
  font-size: 0.875rem;
}

.session-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.session-card {
  border: 1px solid var(--color-border-light);
  border-radius: 6px;
  overflow: hidden;
  transition: border-color 0.2s;
}

.session-expanded {
  border-color: var(--notebook-accent);
}

.session-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 1rem;
  cursor: pointer;
  transition: background 0.2s;
}

.session-header:hover {
  background: var(--color-bg-secondary);
}

.session-info {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.session-status {
  font-size: 0.75rem;
  font-weight: 600;
  padding: 0.125rem 0.5rem;
  border-radius: 3px;
  text-transform: uppercase;
}

.status-pending { background: #fff3cd; color: #856404; }
.status-running { background: #cce5ff; color: #004085; }
.status-completed { background: #d4edda; color: #155724; }
.status-failed { background: #f8d7da; color: #721c24; }
.status-cancelled { background: var(--color-bg-tertiary); color: var(--color-text-tertiary); }

.session-date {
  font-size: 0.8125rem;
  color: var(--color-text-secondary);
}

.session-meta {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.meta-item {
  font-size: 0.75rem;
  color: var(--color-text-tertiary);
}

.expand-icon {
  font-size: 0.75rem;
  color: var(--color-text-tertiary);
  font-family: var(--font-mono);
}

.session-details {
  padding: 1rem;
  border-top: 1px solid var(--color-border-light);
  background: var(--color-bg-secondary);
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.session-error {
  padding: 0.75rem;
  background: #f8d7da;
  border: 1px solid #f5c6cb;
  border-radius: 4px;
  color: #721c24;
  font-size: 0.875rem;
}

.files-modified {
  font-size: 0.8125rem;
  color: var(--color-text-primary);
}

.files-modified ul {
  margin: 0.25rem 0 0;
  padding-left: 1.25rem;
}

.file-path {
  font-family: var(--font-mono);
  font-size: 0.75rem;
  color: var(--color-text-secondary);
}

.action-logs {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  font-size: 0.8125rem;
  color: var(--color-text-primary);
}

.logs-loading,
.no-logs {
  font-size: 0.8125rem;
  color: var(--color-text-tertiary);
  font-style: italic;
}

.session-timing {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  font-size: 0.75rem;
  color: var(--color-text-tertiary);
}
</style>
