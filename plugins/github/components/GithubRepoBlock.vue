<template>
  <div class="custom-block github-repo-block">
    <div class="block-header">
      <span class="block-icon">📦</span>
      <span class="block-title">GitHub Repository</span>
    </div>
    <div class="block-content">
      <!-- Loading state -->
      <div v-if="loading" class="loading">
        <div class="loading-spinner"></div>
        <span>Loading repository...</span>
      </div>

      <!-- Error state -->
      <div v-else-if="error" class="error">
        <div class="repo-link">
          <a :href="config.url" target="_blank" rel="noopener noreferrer">{{ config.url }}</a>
        </div>
        <div class="error-message">{{ error }}</div>
      </div>

      <!-- Repo data -->
      <div v-else-if="repo" class="repo-data">
        <h3 class="repo-name">
          <a :href="repo.html_url" target="_blank" rel="noopener noreferrer">
            {{ repo.full_name }}
          </a>
          <span v-if="repo.private" class="repo-visibility">Private</span>
          <span v-if="repo.fork" class="repo-fork">Fork</span>
        </h3>
        <p v-if="repo.description" class="repo-description">{{ repo.description }}</p>
        <div class="repo-stats">
          <span class="stat">
            <span class="stat-icon">⭐</span>
            {{ formatNumber(repo.stargazers_count) }}
          </span>
          <span class="stat">
            <span class="stat-icon">🍴</span>
            {{ formatNumber(repo.forks_count) }}
          </span>
          <span v-if="repo.open_issues_count > 0" class="stat">
            <span class="stat-icon">🐛</span>
            {{ formatNumber(repo.open_issues_count) }} issues
          </span>
        </div>
        <div class="repo-meta">
          <span v-if="repo.language" class="language">
            <span class="language-dot" :style="{ backgroundColor: getLanguageColor(repo.language) }"></span>
            {{ repo.language }}
          </span>
          <span v-if="repo.license?.spdx_id" class="license">
            📄 {{ repo.license.spdx_id }}
          </span>
          <span class="updated">Updated {{ formatDate(repo.updated_at) }}</span>
        </div>
        <div v-if="repo.topics && repo.topics.length > 0" class="repo-topics">
          <span v-for="topic in repo.topics.slice(0, 5)" :key="topic" class="topic">
            {{ topic }}
          </span>
          <span v-if="repo.topics.length > 5" class="topic-more">
            +{{ repo.topics.length - 5 }} more
          </span>
        </div>
      </div>

      <!-- Not configured -->
      <div v-else-if="!config.url" class="error-message">
        No URL provided. Usage: <code>```github-repo\nurl: https://github.com/owner/repo\n```</code>
      </div>

      <!-- Not connected -->
      <div v-else class="not-configured">
        <div class="repo-link">
          <a :href="config.url" target="_blank" rel="noopener noreferrer">{{ config.url }}</a>
        </div>
        <div class="block-note">
          <em>Configure the GitHub integration in workspace settings to see repository details.</em>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";

interface GitHubLicense {
  key: string;
  name: string;
  spdx_id: string;
}

interface GitHubRepo {
  name: string;
  full_name: string;
  description: string | null;
  html_url: string;
  private: boolean;
  fork: boolean;
  stargazers_count: number;
  forks_count: number;
  open_issues_count: number;
  language: string | null;
  license: GitHubLicense | null;
  topics: string[];
  updated_at: string;
  created_at: string;
}

interface GitHubRepoConfig {
  url?: string;
  [key: string]: any;
}

interface Props {
  config: GitHubRepoConfig;
  workspaceId?: number;
  notebookId?: number;
}

const props = defineProps<Props>();

const loading = ref(false);
const error = ref<string | null>(null);
const repo = ref<GitHubRepo | null>(null);

const languageColors: Record<string, string> = {
  JavaScript: "#f1e05a",
  TypeScript: "#3178c6",
  Python: "#3572A5",
  Java: "#b07219",
  Go: "#00ADD8",
  Rust: "#dea584",
  Ruby: "#701516",
  PHP: "#4F5D95",
  "C++": "#f34b7d",
  C: "#555555",
  "C#": "#178600",
  Swift: "#F05138",
  Kotlin: "#A97BFF",
  Scala: "#c22d40",
  Vue: "#41b883",
  HTML: "#e34c26",
  CSS: "#563d7c",
  Shell: "#89e051",
};

function parseGitHubUrl(url: string): { owner: string; repo: string } | null {
  // Match github.com/owner/repo (but not /issues, /pull, etc.)
  const match = url.match(/github\.com\/([^/]+)\/([^/]+?)(?:\/|$|\?|#)/);
  if (match) {
    return { owner: match[1], repo: match[2].replace(/\.git$/, "") };
  }
  // Also try without trailing slash
  const match2 = url.match(/github\.com\/([^/]+)\/([^/]+)$/);
  if (match2) {
    return { owner: match2[1], repo: match2[2].replace(/\.git$/, "") };
  }
  return null;
}

function formatDate(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffDays === 0) return "today";
  if (diffDays === 1) return "yesterday";
  if (diffDays < 30) return `${diffDays} days ago`;
  if (diffDays < 365) return `${Math.floor(diffDays / 30)} months ago`;
  return `${Math.floor(diffDays / 365)} years ago`;
}

function formatNumber(num: number): string {
  if (num >= 1000000) return (num / 1000000).toFixed(1) + "M";
  if (num >= 1000) return (num / 1000).toFixed(1) + "k";
  return num.toString();
}

function getLanguageColor(language: string): string {
  return languageColors[language] || "#586069";
}

async function fetchRepo() {
  if (!props.workspaceId || !props.config.url) {
    return;
  }

  const parsed = parseGitHubUrl(props.config.url);
  if (!parsed) {
    error.value = "Invalid GitHub repository URL";
    return;
  }

  loading.value = true;
  error.value = null;

  try {
    const token = localStorage.getItem("access_token");
    if (!token) {
      error.value = "Not authenticated";
      return;
    }

    const response = await fetch(
      `/api/v1/plugins/integrations/github/execute?workspace_id=${props.workspaceId}`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          endpoint_id: "get_repo",
          parameters: parsed,
        }),
      }
    );

    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      throw new Error(data.error || data.detail || `HTTP ${response.status}`);
    }

    const result = await response.json();
    if (result.success && result.data) {
      repo.value = result.data;
    } else {
      throw new Error(result.error || "Failed to fetch repository");
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : "Failed to fetch repository";
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  fetchRepo();
});
</script>

<style scoped>
.custom-block {
  border: 2px solid var(--color-border-medium, #e5e7eb);
  border-radius: var(--radius-md, 8px);
  padding: var(--spacing-lg, 16px);
  margin: var(--spacing-lg, 16px) 0;
  background: var(--color-bg-secondary, #f9fafb);
}

.github-repo-block {
  border-color: #0366d6;
  background: linear-gradient(135deg, #dbeafe 0%, #eff6ff 100%);
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

.block-content {
  color: var(--color-text-primary, #111827);
}

.repo-data {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm, 8px);
}

.repo-name {
  margin: 0;
  font-size: var(--text-lg, 1.125rem);
  font-weight: var(--font-semibold, 600);
  display: flex;
  align-items: center;
  gap: var(--spacing-sm, 8px);
  flex-wrap: wrap;
}

.repo-name a {
  color: #0366d6;
  text-decoration: none;
}

.repo-name a:hover {
  text-decoration: underline;
}

.repo-visibility,
.repo-fork {
  padding: 2px 6px;
  border-radius: 12px;
  font-size: var(--text-xs, 0.75rem);
  font-weight: var(--font-medium, 500);
  background: rgba(0, 0, 0, 0.08);
  color: var(--color-text-secondary, #6b7280);
}

.repo-description {
  margin: 0;
  font-size: var(--text-base, 1rem);
  color: var(--color-text-secondary, #6b7280);
  line-height: 1.5;
}

.repo-stats {
  display: flex;
  gap: var(--spacing-md, 12px);
  font-size: var(--text-sm, 0.875rem);
}

.stat {
  display: flex;
  align-items: center;
  gap: 4px;
  color: var(--color-text-secondary, #6b7280);
}

.stat-icon {
  font-size: var(--text-base, 1rem);
}

.repo-meta {
  display: flex;
  align-items: center;
  gap: var(--spacing-md, 12px);
  font-size: var(--text-sm, 0.875rem);
  color: var(--color-text-secondary, #6b7280);
  flex-wrap: wrap;
}

.language {
  display: flex;
  align-items: center;
  gap: 4px;
}

.language-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
}

.repo-topics {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: var(--spacing-xs, 4px);
}

.topic {
  padding: 2px 8px;
  border-radius: 12px;
  font-size: var(--text-xs, 0.75rem);
  background: #0366d6;
  color: white;
}

.topic-more {
  padding: 2px 8px;
  font-size: var(--text-xs, 0.75rem);
  color: var(--color-text-secondary, #6b7280);
}

.repo-link a {
  color: #0366d6;
  text-decoration: none;
  word-break: break-all;
}

.repo-link a:hover {
  text-decoration: underline;
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
  border-top-color: #0366d6;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.error {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm, 8px);
}

.error-message {
  color: #dc2626;
  font-size: var(--text-sm, 0.875rem);
}

.error-message code {
  display: block;
  margin-top: var(--spacing-sm, 8px);
  padding: var(--spacing-sm, 8px);
  background: rgba(0, 0, 0, 0.05);
  border-radius: var(--radius-sm, 4px);
  font-family: monospace;
  font-size: var(--text-sm, 0.875rem);
  white-space: pre-wrap;
}

.block-note {
  margin-top: var(--spacing-sm, 8px);
  padding: var(--spacing-sm, 8px);
  background: rgba(255, 255, 255, 0.5);
  border-radius: var(--radius-sm, 4px);
  font-size: var(--text-sm, 0.875rem);
  color: var(--color-text-secondary, #6b7280);
}

.not-configured {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm, 8px);
}
</style>
