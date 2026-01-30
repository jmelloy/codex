<template>
  <div class="custom-block link-preview-block">
    <div class="block-header">
      <span class="block-icon">🔗</span>
      <span class="block-title">Link Preview</span>
    </div>
    <div class="block-content">
      <a :href="config.url" target="_blank" rel="noopener noreferrer" class="preview-link">
        {{ config.url || 'No URL provided' }}
      </a>
      <div class="block-note">
        <em>Note: This is a placeholder. Enable the Open Graph integration to see rich previews.</em>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
interface LinkPreviewConfig {
  url?: string
  [key: string]: any
}

interface Props {
  config: LinkPreviewConfig
}

defineProps<Props>()
</script>

<style scoped>
.custom-block {
  border: 2px solid var(--color-border-medium);
  border-radius: var(--radius-md);
  padding: var(--spacing-lg);
  margin: var(--spacing-lg) 0;
  background: var(--color-bg-secondary);
}

.link-preview-block {
  border-color: #3b82f6;
  background: linear-gradient(135deg, #dbeafe 0%, #eff6ff 100%);
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

.preview-link {
  display: block;
  font-size: var(--text-base);
  color: var(--color-primary);
  text-decoration: none;
  word-break: break-all;
  margin-bottom: var(--spacing-md);
  font-weight: var(--font-medium);
}

.preview-link:hover {
  text-decoration: underline;
}

.block-note {
  padding: var(--spacing-sm);
  background: rgba(255, 255, 255, 0.5);
  border-radius: var(--radius-sm);
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
}
</style>
