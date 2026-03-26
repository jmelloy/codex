<template>
  <div class="custom-block github-block">
    <div class="block-header">
      <span class="block-icon">&#x1F41B;</span>
      <span class="block-title">GitHub Issues</span>
      <span v-if="repoLabel" class="repo-label">{{ repoLabel }}</span>
      <button v-if="!loading" class="refresh-btn" @click="fetchIssues" title="Refresh">&#x21bb;</button>
      <button class="edit-btn" @click="$emit('edit')" title="Edit config">&#x270E;</button>
    </div>
    <div class="block-content">
      <div v-if="loading" class="loading">
        <div class="loading-spinner"></div>
        <span>Loading issues...</span>
      </div>

      <div v-else-if="error" class="error">
        <div class="error-message">{{ error }}</div>
        <button class="retry-btn" @click="fetchIssues">Retry</button>
      </div>

      <div v-else-if="issues.length > 0" class="issues-list">
        <div v-for="issue in issues" :key="issue.number" class="issue-item">
          <span class="issue-icon" :class="issue.state">{{ issue.pull_request ? '&#x1F500;' : (issue.state === 'open' ? '&#x1F7E2;' : '&#x1F534;') }}</span>
          <div class="issue-info">
            <a :href="issue.html_url" target="_blank" rel="noopener" class="issue-title">
              #{{ issue.number }} {{ issue.title }}
            </a>
            <div class="issue-meta">
              <span class="issue-author">{{ issue.user?.login }}</span>
              <span v-for="label in issue.labels" :key="label.name" class="issue-label" :style="{ backgroundColor: '#' + label.color, color: labelTextColor(label.color) }">{{ label.name }}</span>
            </div>
          </div>
        </div>
      </div>

      <div v-else-if="issues.length === 0 && !loading" class="empty">
        No {{ config.state || 'open' }} issues found.
      </div>

      <div v-else class="not-configured">
        <div class="block-note">
          <em>Configure the GitHub integration in workspace settings to see issues.</em>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue"
import { executeIntegrationEndpoint } from "../../services/integration"

interface GitHubIssuesConfig {
  owner?: string
  repo?: string
  state?: string
  [key: string]: any
}

interface Props {
  config: GitHubIssuesConfig
  workspaceId?: string
  notebookId?: string
}

const props = defineProps<Props>()

defineEmits<{
  edit: []
}>()

const loading = ref(false)
const error = ref<string | null>(null)
const issues = ref<any[]>([])

const repoLabel = computed(() => {
  if (props.config.owner && props.config.repo) {
    return `${props.config.owner}/${props.config.repo}`
  }
  return null
})

function labelTextColor(hexColor: string): string {
  if (!hexColor) return "#000"
  const r = parseInt(hexColor.substring(0, 2), 16)
  const g = parseInt(hexColor.substring(2, 4), 16)
  const b = parseInt(hexColor.substring(4, 6), 16)
  const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
  return luminance > 0.5 ? "#000" : "#fff"
}

async function fetchIssues() {
  if (!props.workspaceId || !props.config.owner || !props.config.repo) {
    return
  }

  loading.value = true
  error.value = null

  try {
    const result = await executeIntegrationEndpoint(
      "github",
      props.workspaceId,
      props.notebookId || "",
      "list_issues",
      {
        owner: props.config.owner,
        repo: props.config.repo,
        state: props.config.state || "open",
        per_page: 10,
      },
    )

    if (result.success && result.data) {
      issues.value = Array.isArray(result.data) ? result.data : result.data.content || []
    } else {
      error.value = result.error || "Failed to fetch issues"
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : "Failed to fetch issues"
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchIssues()
})
</script>

<style scoped>
.github-block {
  border: 2px solid var(--color-border-medium, #e5e7eb);
  border-radius: var(--radius-md, 8px);
  padding: var(--spacing-lg, 16px);
  margin: var(--spacing-lg, 16px) 0;
  background: var(--color-bg-secondary, #f9fafb);
}

.block-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm, 8px);
  margin-bottom: var(--spacing-md, 12px);
  font-weight: var(--font-semibold, 600);
  color: var(--color-text-primary, #111827);
}

.block-icon {
  font-size: var(--text-xl, 1.25rem);
}

.block-title {
  font-size: var(--text-lg, 1.125rem);
}

.repo-label {
  font-size: var(--text-sm, 0.875rem);
  color: var(--color-text-secondary, #6b7280);
  font-weight: normal;
  font-family: monospace;
}

.refresh-btn,
.edit-btn {
  margin-left: auto;
  background: none;
  border: 1px solid var(--color-border-medium, #d1d5db);
  border-radius: var(--radius-sm, 4px);
  padding: 2px 8px;
  cursor: pointer;
  font-size: var(--text-sm, 0.875rem);
  color: var(--color-text-secondary, #6b7280);
}

.edit-btn {
  margin-left: 4px;
}

.refresh-btn:hover,
.edit-btn:hover {
  background: var(--color-bg-tertiary, #f3f4f6);
}

.issues-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.issue-item {
  display: flex;
  gap: 8px;
  padding: 8px;
  border-radius: var(--radius-sm, 4px);
  background: var(--color-bg-primary, #fff);
  border: 1px solid var(--color-border-light, #e5e7eb);
}

.issue-icon {
  flex-shrink: 0;
  font-size: 0.75rem;
  margin-top: 3px;
}

.issue-info {
  flex: 1;
  min-width: 0;
}

.issue-title {
  color: var(--color-text-primary, #111827);
  text-decoration: none;
  font-weight: 500;
  font-size: var(--text-sm, 0.875rem);
  display: block;
}

.issue-title:hover {
  color: #2563eb;
  text-decoration: underline;
}

.issue-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 4px;
  font-size: var(--text-xs, 0.75rem);
  color: var(--color-text-secondary, #6b7280);
}

.issue-label {
  padding: 1px 6px;
  border-radius: 12px;
  font-size: 0.7rem;
  font-weight: 500;
}

.loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-sm, 8px);
  padding: var(--spacing-lg, 16px);
  color: var(--color-text-secondary, #6b7280);
}

.loading-spinner {
  width: 20px;
  height: 20px;
  border: 2px solid var(--color-border-medium, #e5e7eb);
  border-top-color: #6366f1;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.error-message {
  color: #dc2626;
  font-size: var(--text-sm, 0.875rem);
}

.retry-btn {
  margin-top: 8px;
  padding: 4px 12px;
  background: var(--color-bg-primary, #fff);
  border: 1px solid var(--color-border-medium, #d1d5db);
  border-radius: var(--radius-sm, 4px);
  cursor: pointer;
  font-size: var(--text-sm, 0.875rem);
}

.empty {
  text-align: center;
  padding: var(--spacing-lg, 16px);
  color: var(--color-text-secondary, #6b7280);
  font-size: var(--text-sm, 0.875rem);
}

.block-note {
  padding: var(--spacing-sm, 8px);
  font-size: var(--text-sm, 0.875rem);
  color: var(--color-text-secondary, #6b7280);
}
</style>
