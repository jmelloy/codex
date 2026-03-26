<template>
  <div class="custom-block github-block">
    <div class="block-header">
      <span class="block-icon">&#x1F500;</span>
      <span class="block-title">Pull Requests</span>
      <span v-if="repoLabel" class="repo-label">{{ repoLabel }}</span>
      <button v-if="!loading" class="refresh-btn" @click="fetchPulls" title="Refresh">&#x21bb;</button>
      <button class="edit-btn" @click="$emit('edit')" title="Edit config">&#x270E;</button>
    </div>
    <div class="block-content">
      <div v-if="loading" class="loading">
        <div class="loading-spinner"></div>
        <span>Loading pull requests...</span>
      </div>

      <div v-else-if="error" class="error">
        <div class="error-message">{{ error }}</div>
        <button class="retry-btn" @click="fetchPulls">Retry</button>
      </div>

      <div v-else-if="pulls.length > 0" class="pulls-list">
        <div v-for="pr in pulls" :key="pr.number" class="pull-item">
          <span class="pull-icon" :class="pr.state">{{ pr.state === 'open' ? '&#x1F7E2;' : (pr.merged_at ? '&#x1F7E3;' : '&#x1F534;') }}</span>
          <div class="pull-info">
            <a :href="pr.html_url" target="_blank" rel="noopener" class="pull-title">
              #{{ pr.number }} {{ pr.title }}
            </a>
            <div class="pull-meta">
              <span class="pull-author">{{ pr.user?.login }}</span>
              <span v-if="pr.draft" class="pull-draft">Draft</span>
            </div>
          </div>
        </div>
      </div>

      <div v-else-if="pulls.length === 0 && !loading" class="empty">
        No {{ config.state || 'open' }} pull requests found.
      </div>

      <div v-else class="not-configured">
        <div class="block-note">
          <em>Configure the GitHub integration in workspace settings to see pull requests.</em>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue"
import { executeIntegrationEndpoint } from "../../services/integration"

interface GitHubPullsConfig {
  owner?: string
  repo?: string
  state?: string
  [key: string]: any
}

interface Props {
  config: GitHubPullsConfig
  workspaceId?: string
  notebookId?: string
}

const props = defineProps<Props>()

defineEmits<{
  edit: []
}>()

const loading = ref(false)
const error = ref<string | null>(null)
const pulls = ref<any[]>([])

const repoLabel = computed(() => {
  if (props.config.owner && props.config.repo) {
    return `${props.config.owner}/${props.config.repo}`
  }
  return null
})

async function fetchPulls() {
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
      "list_pulls",
      {
        owner: props.config.owner,
        repo: props.config.repo,
        state: props.config.state || "open",
        per_page: 10,
      },
    )

    if (result.success && result.data) {
      pulls.value = Array.isArray(result.data) ? result.data : result.data.content || []
    } else {
      error.value = result.error || "Failed to fetch pull requests"
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : "Failed to fetch pull requests"
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchPulls()
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

.pulls-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.pull-item {
  display: flex;
  gap: 8px;
  padding: 8px;
  border-radius: var(--radius-sm, 4px);
  background: var(--color-bg-primary, #fff);
  border: 1px solid var(--color-border-light, #e5e7eb);
}

.pull-icon {
  flex-shrink: 0;
  font-size: 0.75rem;
  margin-top: 3px;
}

.pull-info {
  flex: 1;
  min-width: 0;
}

.pull-title {
  color: var(--color-text-primary, #111827);
  text-decoration: none;
  font-weight: 500;
  font-size: var(--text-sm, 0.875rem);
  display: block;
}

.pull-title:hover {
  color: #2563eb;
  text-decoration: underline;
}

.pull-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 4px;
  font-size: var(--text-xs, 0.75rem);
  color: var(--color-text-secondary, #6b7280);
}

.pull-draft {
  padding: 1px 6px;
  border-radius: 12px;
  background: #fef3c7;
  color: #92400e;
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
