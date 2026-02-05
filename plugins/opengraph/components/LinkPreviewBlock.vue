<template>
  <div class="custom-block link-preview-block">
    <!-- Loading state -->
    <div v-if="loading" class="block-content loading-state">
      <div class="loading-spinner"></div>
      <span>Loading preview...</span>
    </div>

    <!-- Error state -->
    <div v-else-if="error" class="block-content error-state">
      <div class="error-icon">⚠️</div>
      <div class="error-message">{{ error }}</div>
      <a
        :href="config.url"
        target="_blank"
        rel="noopener noreferrer"
        class="fallback-link"
      >
        {{ config.url }}
      </a>
    </div>

    <!-- Success state with metadata -->
    <a
      v-else-if="metadata"
      :href="metadata.url || config.url"
      target="_blank"
      rel="noopener noreferrer"
      class="link-preview-card"
    >
      <div v-if="metadata.image" class="preview-image">
        <img :src="metadata.image" :alt="metadata.title || 'Preview image'" />
      </div>
      <div class="preview-details">
        <div v-if="metadata.site_name" class="site-name">
          {{ metadata.site_name }}
        </div>
        <div class="preview-title">
          {{ metadata.title || config.url }}
        </div>
        <div v-if="metadata.description" class="preview-description">
          {{ metadata.description }}
        </div>
        <div class="preview-url">
          {{ formatUrl(metadata.url || config.url) }}
        </div>
      </div>
    </a>

    <!-- Fallback if no URL -->
    <div v-else class="block-content">
      <div class="error-message">No URL provided</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue"
import { executeIntegrationEndpoint } from "../../../frontend/src/services/integration"

interface LinkPreviewConfig {
  url?: string
  [key: string]: any
}

interface OpenGraphMetadata {
  title?: string
  description?: string
  image?: string
  url?: string
  site_name?: string
}

interface Props {
  config: LinkPreviewConfig
  workspaceId?: number
  notebookId?: number
}

const props = defineProps<Props>()

const loading = ref(false)
const error = ref<string | null>(null)
const metadata = ref<OpenGraphMetadata | null>(null)

const formatUrl = (url: string): string => {
  try {
    const urlObj = new URL(url)
    return urlObj.hostname
  } catch {
    return url
  }
}

const fetchMetadata = async () => {
  if (!props.config.url) {
    error.value = "No URL provided"
    return
  }

  if (!props.workspaceId || !props.notebookId) {
    error.value = "Missing workspace or notebook context"
    return
  }

  loading.value = true
  error.value = null

  try {
    const result = await executeIntegrationEndpoint(
      "opengraph-unfurl",
      props.workspaceId,
      props.notebookId,
      "fetch_metadata",
      { url: props.config.url }
    )

    if (result.success && result.data) {
      metadata.value = result.data
    } else {
      error.value = result.error || "Failed to fetch preview"
    }
  } catch (err: any) {
    console.error("Error fetching link preview:", err)
    error.value = err.response?.data?.detail || err.message || "Failed to load preview"
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchMetadata()
})
</script>

<style scoped>
.custom-block {
  border-radius: var(--radius-md);
  margin: var(--spacing-lg) 0;
  overflow: hidden;
}

.link-preview-block {
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border-light);
  transition: box-shadow 0.2s ease;
}

.link-preview-block:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.loading-state,
.error-state {
  padding: var(--spacing-lg);
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  color: var(--color-text-secondary);
}

.loading-spinner {
  width: 20px;
  height: 20px;
  border: 2px solid var(--color-border-medium);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.error-state {
  color: var(--color-danger, #dc2626);
}

.error-icon {
  font-size: var(--text-xl);
}

.error-message {
  flex: 1;
  font-size: var(--text-sm);
}

.fallback-link {
  color: var(--color-primary);
  text-decoration: none;
  font-size: var(--text-sm);
  word-break: break-all;
}

.fallback-link:hover {
  text-decoration: underline;
}

.link-preview-card {
  display: flex;
  gap: var(--spacing-md);
  text-decoration: none;
  color: inherit;
  transition: background-color 0.2s ease;
}

.link-preview-card:hover {
  background-color: var(--color-bg-tertiary);
}

.preview-image {
  flex-shrink: 0;
  width: 200px;
  height: 150px;
  background: var(--color-bg-tertiary);
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.preview-image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.preview-details {
  flex: 1;
  padding: var(--spacing-md);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
  min-width: 0;
}

.site-name {
  font-size: var(--text-xs);
  color: var(--color-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  font-weight: var(--font-semibold);
}

.preview-title {
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--color-text-primary);
  line-height: 1.3;
  overflow: hidden;
  text-overflow: ellipsis;
  /* Use -webkit- prefixed properties with standard fallback for cross-browser compatibility */
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
}

.preview-description {
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
  line-height: 1.5;
  overflow: hidden;
  text-overflow: ellipsis;
  /* Use -webkit- prefixed properties with standard fallback for cross-browser compatibility */
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
}

.preview-url {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
  margin-top: auto;
}

/* Responsive design */
@media (max-width: 640px) {
  .link-preview-card {
    flex-direction: column;
  }

  .preview-image {
    width: 100%;
    height: 200px;
  }
}
</style>
