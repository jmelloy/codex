<template>
  <div class="custom-block github-block github-repo-block">
    <div class="block-header">
      <span class="block-icon">&#x1F4E6;</span>
      <span class="block-title">Repository</span>
      <button v-if="!loading" class="refresh-btn" @click="fetchRepo" title="Refresh">&#x21bb;</button>
      <button class="edit-btn" @click="$emit('edit')" title="Edit config">&#x270E;</button>
    </div>
    <div class="block-content">
      <div v-if="loading" class="loading">
        <div class="loading-spinner"></div>
        <span>Loading repository...</span>
      </div>

      <div v-else-if="error" class="error">
        <div class="error-message">{{ error }}</div>
        <button class="retry-btn" @click="fetchRepo">Retry</button>
      </div>

      <div v-else-if="repo" class="repo-card">
        <a :href="repo.html_url" target="_blank" rel="noopener" class="repo-name">
          {{ repo.full_name }}
        </a>
        <p v-if="repo.description" class="repo-description">{{ repo.description }}</p>
        <div class="repo-stats">
          <span v-if="repo.language" class="stat">
            <span class="stat-dot" :style="{ backgroundColor: langColor(repo.language) }"></span>
            {{ repo.language }}
          </span>
          <span class="stat">&#x2B50; {{ formatCount(repo.stargazers_count) }}</span>
          <span class="stat">&#x1F500; {{ formatCount(repo.forks_count) }}</span>
          <span class="stat">&#x1F41B; {{ repo.open_issues_count }} open issues</span>
        </div>
      </div>

      <div v-else class="not-configured">
        <div class="block-note">
          <em>Configure the GitHub integration in workspace settings to see repository info.</em>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue"
import { executeIntegrationEndpoint } from "../../services/integration"

interface GitHubRepoConfig {
  owner?: string
  repo?: string
  [key: string]: any
}

interface Props {
  config: GitHubRepoConfig
  workspaceId?: string
  notebookId?: string
}

const props = defineProps<Props>()

defineEmits<{
  edit: []
}>()

const loading = ref(false)
const error = ref<string | null>(null)
const repo = ref<any>(null)

const LANG_COLORS: Record<string, string> = {
  JavaScript: "#f1e05a",
  TypeScript: "#3178c6",
  Python: "#3572A5",
  Rust: "#dea584",
  Go: "#00ADD8",
  Java: "#b07219",
  Ruby: "#701516",
  "C++": "#f34b7d",
  C: "#555555",
  "C#": "#178600",
  PHP: "#4F5D95",
  Swift: "#F05138",
  Kotlin: "#A97BFF",
  Vue: "#41b883",
  Shell: "#89e051",
  HTML: "#e34c26",
  CSS: "#563d7c",
}

function langColor(language: string): string {
  return LANG_COLORS[language] || "#8b8b8b"
}

function formatCount(n: number): string {
  if (n >= 1000) return (n / 1000).toFixed(1) + "k"
  return String(n)
}

async function fetchRepo() {
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
      "get_repo",
      {
        owner: props.config.owner,
        repo: props.config.repo,
      },
    )

    if (result.success && result.data) {
      repo.value = result.data.full_name ? result.data : result.data.content || null
    } else {
      error.value = result.error || "Failed to fetch repository"
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : "Failed to fetch repository"
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchRepo()
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

.github-repo-block {
  border-color: #6366f1;
  background: linear-gradient(135deg, #eef2ff 0%, #f5f3ff 100%);
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

.repo-card {
  padding: 4px 0;
}

.repo-name {
  font-size: var(--text-lg, 1.125rem);
  font-weight: 600;
  color: #2563eb;
  text-decoration: none;
}

.repo-name:hover {
  text-decoration: underline;
}

.repo-description {
  margin: 8px 0;
  color: var(--color-text-secondary, #6b7280);
  font-size: var(--text-sm, 0.875rem);
}

.repo-stats {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  font-size: var(--text-sm, 0.875rem);
  color: var(--color-text-secondary, #6b7280);
}

.stat {
  display: flex;
  align-items: center;
  gap: 4px;
}

.stat-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  display: inline-block;
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

.block-note {
  padding: var(--spacing-sm, 8px);
  font-size: var(--text-sm, 0.875rem);
  color: var(--color-text-secondary, #6b7280);
}
</style>
