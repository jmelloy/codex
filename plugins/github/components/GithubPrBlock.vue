<template>
  <div class="custom-block github-pr-block">
    <div class="block-header">
      <span class="block-icon">🔀</span>
      <span class="block-title">GitHub Pull Request</span>
    </div>
    <div class="block-content">
      <!-- Loading state -->
      <div v-if="loading" class="loading">
        <div class="loading-spinner"></div>
        <span>Loading pull request...</span>
      </div>

      <!-- Error state -->
      <div v-else-if="error" class="error">
        <div class="pr-link">
          <a :href="config.url" target="_blank" rel="noopener noreferrer">{{
            config.url
          }}</a>
        </div>
        <div class="error-message">{{ error }}</div>
      </div>

      <!-- PR data -->
      <div v-else-if="pr" class="pr-data">
        <div class="pr-header">
          <span :class="['pr-state', prState]">{{ prStateLabel }}</span>
          <a
            :href="pr.html_url"
            target="_blank"
            rel="noopener noreferrer"
            class="pr-number"
          >
            #{{ pr.number }}
          </a>
        </div>
        <h3 class="pr-title">
          <a :href="pr.html_url" target="_blank" rel="noopener noreferrer">
            {{ pr.title }}
          </a>
        </h3>
        <div v-if="pr.labels && pr.labels.length > 0" class="pr-labels">
          <span
            v-for="label in pr.labels"
            :key="label.id"
            class="label"
            :style="{
              backgroundColor: '#' + label.color,
              color: getContrastColor(label.color),
            }"
          >
            {{ label.name }}
          </span>
        </div>
        <div class="pr-meta">
          <span class="author">
            <img
              v-if="pr.user?.avatar_url"
              :src="pr.user.avatar_url"
              class="avatar"
            />
            {{ pr.user?.login }}
          </span>
          <span class="date">opened {{ formatDate(pr.created_at) }}</span>
          <span v-if="pr.comments > 0" class="comments"
            >💬 {{ pr.comments }}</span
          >
        </div>
        <div class="pr-branches">
          <span class="branch">{{ pr.head?.label || pr.head?.ref }}</span>
          <span class="arrow">→</span>
          <span class="branch">{{ pr.base?.label || pr.base?.ref }}</span>
        </div>
        <div class="pr-stats">
          <span class="additions">+{{ pr.additions || 0 }}</span>
          <span class="deletions">-{{ pr.deletions || 0 }}</span>
          <span class="files">{{ pr.changed_files || 0 }} files</span>
        </div>
      </div>

      <!-- Not configured -->
      <div v-else-if="!config.url" class="error-message">
        No URL provided. Usage:
        <code
          >```github-pr\nurl: https://github.com/owner/repo/pull/456\n```</code
        >
      </div>

      <!-- Not connected -->
      <div v-else class="not-configured">
        <div class="pr-link">
          <a :href="config.url" target="_blank" rel="noopener noreferrer">{{
            config.url
          }}</a>
        </div>
        <div class="block-note">
          <em
            >Configure the GitHub integration in workspace settings to see PR
            details.</em
          >
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue";

interface GitHubLabel {
  id: number;
  name: string;
  color: string;
}

interface GitHubUser {
  login: string;
  avatar_url: string;
}

interface GitHubBranch {
  label: string;
  ref: string;
  sha: string;
}

interface GitHubPR {
  number: number;
  title: string;
  state: string;
  merged: boolean;
  draft: boolean;
  html_url: string;
  user: GitHubUser | null;
  labels: GitHubLabel[];
  comments: number;
  created_at: string;
  updated_at: string;
  merged_at: string | null;
  body: string | null;
  head: GitHubBranch | null;
  base: GitHubBranch | null;
  additions: number;
  deletions: number;
  changed_files: number;
}

interface GitHubPRConfig {
  url?: string;
  [key: string]: any;
}

interface Props {
  config: GitHubPRConfig;
  workspaceId?: number;
  notebookId?: number;
}

const props = defineProps<Props>();

const loading = ref(false);
const error = ref<string | null>(null);
const pr = ref<GitHubPR | null>(null);

const prState = computed(() => {
  if (!pr.value) return "open";
  if (pr.value.merged) return "merged";
  if (pr.value.draft) return "draft";
  return pr.value.state;
});

const prStateLabel = computed(() => {
  if (!pr.value) return "Open";
  if (pr.value.merged) return "Merged";
  if (pr.value.draft) return "Draft";
  return pr.value.state === "closed" ? "Closed" : "Open";
});

function parseGitHubUrl(
  url: string,
): { owner: string; repo: string; pull_number: number } | null {
  const match = url.match(/github\.com\/([^/]+)\/([^/]+)\/pull\/(\d+)/);
  if (match) {
    return {
      owner: match[1],
      repo: match[2],
      pull_number: parseInt(match[3], 10),
    };
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

async function fetchPR() {
  if (!props.workspaceId || !props.config.url) {
    return;
  }

  const parsed = parseGitHubUrl(props.config.url);
  if (!parsed) {
    error.value = "Invalid GitHub pull request URL";
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
          endpoint_id: "get_pr",
          parameters: parsed,
        }),
      },
    );

    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      throw new Error(data.error || data.detail || `HTTP ${response.status}`);
    }

    const result = await response.json();
    if (result.success && result.data) {
      pr.value = result.data;
    } else {
      throw new Error(result.error || "Failed to fetch pull request");
    }
  } catch (err) {
    error.value =
      err instanceof Error ? err.message : "Failed to fetch pull request";
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  fetchPR();
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

.github-pr-block {
  border-color: #6f42c1;
  background: linear-gradient(135deg, #e9d8fd 0%, #f3e8ff 100%);
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

.pr-data {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm, 8px);
}

.pr-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm, 8px);
}

.pr-state {
  padding: 2px 8px;
  border-radius: 12px;
  font-size: var(--text-sm, 0.875rem);
  font-weight: var(--font-semibold, 600);
  text-transform: capitalize;
}

.pr-state.open {
  background: #22863a;
  color: white;
}

.pr-state.closed {
  background: #cb2431;
  color: white;
}

.pr-state.merged {
  background: #6f42c1;
  color: white;
}

.pr-state.draft {
  background: #6a737d;
  color: white;
}

.pr-number {
  color: var(--color-text-secondary, #6b7280);
  text-decoration: none;
  font-size: var(--text-sm, 0.875rem);
}

.pr-number:hover {
  text-decoration: underline;
}

.pr-title {
  margin: 0;
  font-size: var(--text-lg, 1.125rem);
  font-weight: var(--font-semibold, 600);
  line-height: 1.3;
}

.pr-title a {
  color: var(--color-text-primary, #111827);
  text-decoration: none;
}

.pr-title a:hover {
  color: #0366d6;
  text-decoration: underline;
}

.pr-labels {
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

.pr-meta {
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

.pr-branches {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm, 8px);
  font-size: var(--text-sm, 0.875rem);
  font-family: monospace;
}

.branch {
  background: rgba(0, 0, 0, 0.08);
  padding: 2px 6px;
  border-radius: 4px;
  color: var(--color-text-secondary, #6b7280);
}

.arrow {
  color: var(--color-text-secondary, #6b7280);
}

.pr-stats {
  display: flex;
  gap: var(--spacing-md, 12px);
  font-size: var(--text-sm, 0.875rem);
}

.additions {
  color: #22863a;
  font-weight: var(--font-medium, 500);
}

.deletions {
  color: #cb2431;
  font-weight: var(--font-medium, 500);
}

.files {
  color: var(--color-text-secondary, #6b7280);
}

.pr-link a {
  color: #0366d6;
  text-decoration: none;
  word-break: break-all;
}

.pr-link a:hover {
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
  border-top-color: #6f42c1;
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
