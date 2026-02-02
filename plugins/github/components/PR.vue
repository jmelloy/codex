<template>
  <div class="custom-block github-pr-block">
    <div class="block-header">
      <span class="block-icon">🔀</span>
      <span class="block-title">GitHub Pull Request</span>
    </div>
    <div class="block-content">
      <div v-if="config.url" class="pr-info">
        <h3 class="pr-title">
          <a :href="config.url" target="_blank" rel="noopener noreferrer">
            {{ config.url }}
          </a>
        </h3>
        <div class="block-note">
          <em>
            Note: This is a placeholder. Enable the GitHub integration and configure your access token to see full PR details including:
          </em>
          <ul>
            <li>PR number and title</li>
            <li>PR description</li>
            <li>State (open/closed/merged)</li>
            <li>Author information</li>
            <li>Review status</li>
            <li>Merge status</li>
            <li>Timestamps</li>
          </ul>
        </div>
      </div>
      <div v-else class="error-message">
        No URL provided. Usage: <code>```github-pr\nurl: https://github.com/owner/repo/pull/456\n```</code>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
interface GitHubPRConfig {
  url?: string;
  [key: string]: any;
}

interface Props {
  config: GitHubPRConfig;
}

defineProps<Props>();
</script>

<style scoped>
.custom-block {
  border: 2px solid var(--color-border-medium);
  border-radius: var(--radius-md);
  padding: var(--spacing-lg);
  margin: var(--spacing-lg) 0;
  background: var(--color-bg-secondary);
}

.github-pr-block {
  border-color: #6f42c1;
  background: linear-gradient(135deg, #e9d8fd 0%, #f3e8ff 100%);
}

.block-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-md);
  font-weight: var(--font-semibold);
  color: var(--color-text-primary);
}

.block-icon {
  font-size: var(--text-xl);
}

.block-title {
  font-size: var(--text-lg);
}

.block-content {
  color: var(--color-text-primary);
}

.pr-info {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.pr-title {
  margin: 0;
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
}

.pr-title a {
  color: var(--color-primary);
  text-decoration: none;
  word-break: break-all;
}

.pr-title a:hover {
  text-decoration: underline;
}

.block-note {
  padding: var(--spacing-sm);
  background: rgba(255, 255, 255, 0.5);
  border-radius: var(--radius-sm);
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
}

.block-note ul {
  margin: var(--spacing-xs) 0 0 var(--spacing-lg);
  padding: 0;
}

.block-note li {
  margin: var(--spacing-xs) 0;
}

.error-message {
  padding: var(--spacing-md);
  background: rgba(239, 68, 68, 0.1);
  border-radius: var(--radius-sm);
  color: var(--color-text-primary);
}

.error-message code {
  display: block;
  margin-top: var(--spacing-sm);
  padding: var(--spacing-sm);
  background: rgba(0, 0, 0, 0.05);
  border-radius: var(--radius-sm);
  font-family: monospace;
  font-size: var(--text-sm);
}
</style>
