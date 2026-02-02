<template>
  <div class="custom-block github-issue-block">
    <div class="block-header">
      <span class="block-icon">🐛</span>
      <span class="block-title">GitHub Issue</span>
    </div>
    <div class="block-content">
      <!-- Loading state -->
      <div v-if="loading" class="loading">
        <div class="loading-spinner"></div>
        <span>Loading issue...</span>
      </div>

      <!-- Error state -->
      <div v-else-if="error" class="error">
        <div class="issue-link">
          <a :href="config.url" target="_blank" rel="noopener noreferrer">{{ config.url }}</a>
        </div>
        <div class="error-message">{{ error }}</div>
      </div>

      <!-- Issue data -->
      <div v-else-if="issue" class="issue-data">
        <div class="issue-header">
          <span :class="['issue-state', issue.state]">{{ issue.state }}</span>
          <a :href="issue.html_url" target="_blank" rel="noopener noreferrer" class="issue-number">
            #{{ issue.number }}
          </a>
        </div>
        <h3 class="issue-title">
          <a :href="issue.html_url" target="_blank" rel="noopener noreferrer">
            {{ issue.title }}
          </a>
        </h3>
        <div v-if="issue.labels && issue.labels.length > 0" class="issue-labels">
          <span
            v-for="label in issue.labels"
            :key="label.id"
            class="label"
            :style="{ backgroundColor: '#' + label.color, color: getContrastColor(label.color) }"
          >
            {{ label.name }}
          </span>
        </div>
        <div class="issue-meta">
          <span class="author">
            <img v-if="issue.user?.avatar_url" :src="issue.user.avatar_url" class="avatar" />
            {{ issue.user?.login }}
          </span>
          <span class="date">opened {{ formatDate(issue.created_at) }}</span>
          <span v-if="issue.comments > 0" class="comments">💬 {{ issue.comments }}</span>
        </div>
      </div>

      <!-- Not configured -->
      <div v-else-if="!config.url" class="error-message">
        No URL provided. Usage: <code>```github-issue\nurl: https://github.com/owner/repo/issues/123\n```</code>
      </div>

      <!-- Not connected -->
      <div v-else class="not-configured">
        <div class="issue-link">
          <a :href="config.url" target="_blank" rel="noopener noreferrer">{{ config.url }}</a>
        </div>
        <div class="block-note">
          <em>Configure the GitHub integration in workspace settings to see issue details.</em>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";

interface GitHubLabel {
  id: number;
  name: string;
  color: string;
}

interface GitHubUser {
  login: string;
  avatar_url: string;
}

interface GitHubIssue {
  number: number;
  title: string;
  state: string;
  html_url: string;
  user: GitHubUser | null;
  labels: GitHubLabel[];
  comments: number;
  created_at: string;
  updated_at: string;
  body: string | null;
}

interface GitHubIssueConfig {
  url?: string;
  [key: string]: any;
}

interface Props {
  config: GitHubIssueConfig;
  workspaceId?: number;
  notebookId?: number;
}

const props = defineProps<Props>();

const loading = ref(false);
const error = ref<string | null>(null);
const issue = ref<GitHubIssue | null>(null);

function parseGitHubUrl(url: string): { owner: string; repo: string; issue_number: number } | null {
  const match = url.match(/github\.com\/([^/]+)\/([^/]+)\/issues\/(\d+)/);
  if (match) {
    return { owner: match[1], repo: match[2], issue_number: parseInt(match[3], 10) };
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

function getContrastColor(hexColor: string): string {
  const r = parseInt(hexColor.slice(0, 2), 16);
  const g = parseInt(hexColor.slice(2, 4), 16);
  const b = parseInt(hexColor.slice(4, 6), 16);
  const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
  return luminance > 0.5 ? "#000000" : "#ffffff";
}

async function fetchIssue() {
  if (!props.workspaceId || !props.config.url) {
    return;
  }

  const parsed = parseGitHubUrl(props.config.url);
  if (!parsed) {
    error.value = "Invalid GitHub issue URL";
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
      `/api/v1/integrations/github/execute?workspace_id=${props.workspaceId}`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          endpoint_id: "get_issue",
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
      issue.value = result.data;
    } else {
      throw new Error(result.error || "Failed to fetch issue");
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : "Failed to fetch issue";
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  fetchIssue();
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

.github-issue-block {
  border-color: #22863a;
  background: linear-gradient(135deg, #dcffe4 0%, #f0fff4 100%);
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

.issue-data {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm, 8px);
}

.issue-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm, 8px);
}

.issue-state {
  padding: 2px 8px;
  border-radius: 12px;
  font-size: var(--text-sm, 0.875rem);
  font-weight: var(--font-semibold, 600);
  text-transform: capitalize;
}

.issue-state.open {
  background: #22863a;
  color: white;
}

.issue-state.closed {
  background: #6f42c1;
  color: white;
}

.issue-number {
  color: var(--color-text-secondary, #6b7280);
  text-decoration: none;
  font-size: var(--text-sm, 0.875rem);
}

.issue-number:hover {
  text-decoration: underline;
}

.issue-title {
  margin: 0;
  font-size: var(--text-lg, 1.125rem);
  font-weight: var(--font-semibold, 600);
  line-height: 1.3;
}

.issue-title a {
  color: var(--color-text-primary, #111827);
  text-decoration: none;
}

.issue-title a:hover {
  color: #0366d6;
  text-decoration: underline;
}

.issue-labels {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.label {
  padding: 2px 8px;
  border-radius: 12px;
  font-size: var(--text-xs, 0.75rem);
  font-weight: var(--font-medium, 500);
}

.issue-meta {
  display: flex;
  align-items: center;
  gap: var(--spacing-md, 12px);
  font-size: var(--text-sm, 0.875rem);
  color: var(--color-text-secondary, #6b7280);
}

.author {
  display: flex;
  align-items: center;
  gap: 4px;
}

.avatar {
  width: 20px;
  height: 20px;
  border-radius: 50%;
}

.issue-link a {
  color: #0366d6;
  text-decoration: none;
  word-break: break-all;
}

.issue-link a:hover {
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
  border-top-color: #22863a;
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
