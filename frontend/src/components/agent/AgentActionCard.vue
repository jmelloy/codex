<template>
  <div class="action-card">
    <div class="action-header">
      <span class="action-icon">{{ actionIcon }}</span>
      <span class="action-type">{{ formatActionType(action.action_type) }}</span>
      <span v-if="action.target_path" class="action-path">{{ action.target_path }}</span>
      <span :class="['action-status', action.was_allowed ? 'status-allowed' : 'status-denied']">
        {{ action.was_allowed ? 'Allowed' : 'Denied' }}
      </span>
    </div>
    <div v-if="action.input_summary" class="action-detail">
      <span class="detail-label">Input:</span>
      <span class="detail-value">{{ truncate(action.input_summary, 200) }}</span>
    </div>
    <div v-if="action.output_summary" class="action-detail">
      <span class="detail-label">Output:</span>
      <span class="detail-value">{{ truncate(action.output_summary, 200) }}</span>
    </div>
    <div class="action-footer">
      <span class="action-time">{{ formatDuration(action.execution_time_ms) }}</span>
      <span class="action-timestamp">{{ formatTimestamp(action.created_at) }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue"
import type { ActionLog } from "../../services/agent"

const props = defineProps<{
  action: ActionLog
}>()

const actionIcon = computed(() => {
  switch (props.action.action_type) {
    case "file_read":
    case "read_file":
      return "R"
    case "file_write":
    case "write_file":
      return "W"
    case "create_file":
      return "+"
    case "delete_file":
      return "x"
    case "list_files":
      return "L"
    case "search_content":
      return "?"
    case "get_file_metadata":
      return "i"
    default:
      return "*"
  }
})

function formatActionType(type: string): string {
  return type
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase())
}

function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`
  return `${(ms / 1000).toFixed(1)}s`
}

function formatTimestamp(ts: string): string {
  return new Date(ts).toLocaleTimeString()
}

function truncate(str: string, max: number): string {
  if (str.length <= max) return str
  return str.slice(0, max) + "..."
}
</script>

<style scoped>
.action-card {
  padding: 0.75rem 1rem;
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border-light);
  border-radius: 6px;
  font-size: 0.8125rem;
}

.action-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.action-icon {
  width: 1.5rem;
  height: 1.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-bg-tertiary);
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 700;
  font-family: var(--font-mono);
  color: var(--color-text-secondary);
  flex-shrink: 0;
}

.action-type {
  font-weight: 600;
  color: var(--color-text-primary);
}

.action-path {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--color-text-secondary);
  font-family: var(--font-mono);
  font-size: 0.75rem;
}

.action-status {
  font-size: 0.6875rem;
  font-weight: 600;
  padding: 0.125rem 0.375rem;
  border-radius: 3px;
  text-transform: uppercase;
  flex-shrink: 0;
}

.status-allowed {
  background: #d4edda;
  color: #155724;
}

.status-denied {
  background: #f8d7da;
  color: #721c24;
}

.action-detail {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 0.25rem;
  line-height: 1.4;
}

.detail-label {
  font-weight: 500;
  color: var(--color-text-tertiary);
  flex-shrink: 0;
}

.detail-value {
  color: var(--color-text-secondary);
  word-break: break-word;
  font-family: var(--font-mono);
  font-size: 0.75rem;
}

.action-footer {
  display: flex;
  justify-content: space-between;
  margin-top: 0.5rem;
  color: var(--color-text-tertiary);
  font-size: 0.75rem;
}
</style>
