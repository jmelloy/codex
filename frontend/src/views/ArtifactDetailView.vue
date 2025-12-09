<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useNotebooksStore } from "@/stores/notebooks";
import { artifactsApi, entriesApi } from "@/api";
import type { Artifact, Entry } from "@/types";

const route = useRoute();
const router = useRouter();
const notebooksStore = useNotebooksStore();

const artifactHash = computed(() => route.params.hash as string);
const entryId = computed(() => route.query.entryId as string);

const artifact = ref<Artifact | null>(null);
const entry = ref<Entry | null>(null);
const loading = ref(true);
const error = ref<string | null>(null);

const artifactUrl = computed(() => {
  if (!artifact.value) return "";
  return artifactsApi.getUrl(notebooksStore.workspacePath, artifact.value.hash);
});

const isImage = computed(() => {
  return artifact.value?.type.startsWith("image/") || false;
});

const additionalMetadata = computed(() => {
  if (!artifact.value?.metadata) return {};
  // Filter out metadata fields already displayed elsewhere
  const { width, height, ...rest } = artifact.value.metadata;
  return rest;
});

function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 Bytes";
  const k = 1024;
  const sizes = ["Bytes", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + " " + sizes[i];
}

function formatDate(dateString: string | undefined): string {
  if (!dateString) return "N/A";
  return new Date(dateString).toLocaleString();
}

async function loadArtifact() {
  loading.value = true;
  error.value = null;

  try {
    artifact.value = await artifactsApi.getInfo(
      notebooksStore.workspacePath,
      artifactHash.value
    );

    if (entryId.value) {
      entry.value = await entriesApi.get(
        notebooksStore.workspacePath,
        entryId.value
      );
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed to load artifact";
  } finally {
    loading.value = false;
  }
}

function goBack() {
  router.back();
}

onMounted(loadArtifact);
</script>

<template>
  <div class="artifact-detail">
    <div v-if="loading" class="loading">
      Loading artifact...
    </div>

    <div v-else-if="error" class="error">
      <p>{{ error }}</p>
      <button @click="goBack" class="btn">Go Back</button>
    </div>

    <div v-else-if="artifact" class="artifact-content">
      <header class="artifact-header">
        <button @click="goBack" class="back-button">← Back</button>
        <h1>Artifact Details</h1>
      </header>

      <div class="artifact-body">
        <!-- Image Preview -->
        <div v-if="isImage" class="artifact-preview">
          <img :src="artifactUrl" :alt="`Artifact ${artifact.hash}`" />
        </div>

        <!-- Non-image preview -->
        <div v-else class="artifact-preview non-image">
          <div class="file-icon">📄</div>
          <p class="file-type">{{ artifact.type }}</p>
        </div>

        <!-- Metadata Section -->
        <div class="metadata-section">
          <h2>Metadata</h2>
          
          <div class="metadata-grid">
            <div class="metadata-item">
              <label>Type</label>
              <span>{{ artifact.type }}</span>
            </div>

            <div class="metadata-item">
              <label>Size</label>
              <span>{{ formatBytes(artifact.size_bytes) }}</span>
            </div>

            <div class="metadata-item">
              <label>Hash (SHA-256)</label>
              <code class="hash">{{ artifact.hash }}</code>
            </div>

            <div class="metadata-item">
              <label>Created</label>
              <span>{{ formatDate(artifact.created_at) }}</span>
            </div>

            <div v-if="artifact.archived" class="metadata-item">
              <label>Archive Status</label>
              <span class="archived-badge">Archived</span>
            </div>

            <div v-if="artifact.archive_strategy" class="metadata-item">
              <label>Archive Strategy</label>
              <span>{{ artifact.archive_strategy }}</span>
            </div>

            <div v-if="artifact.original_size_bytes" class="metadata-item">
              <label>Original Size</label>
              <span>{{ formatBytes(artifact.original_size_bytes) }}</span>
            </div>

            <div v-if="artifact.metadata?.width && artifact.metadata?.height" class="metadata-item">
              <label>Dimensions</label>
              <span>{{ artifact.metadata.width }} × {{ artifact.metadata.height }}</span>
            </div>

            <div v-if="entry" class="metadata-item full-width">
              <label>Entry</label>
              <span class="entry-info">{{ entry.title }} ({{ entry.id.substring(0, 12) }})</span>
            </div>
          </div>

          <!-- Additional metadata if present -->
          <div v-if="Object.keys(additionalMetadata).length > 0" class="custom-metadata">
            <h3>Additional Metadata</h3>
            <pre>{{ JSON.stringify(additionalMetadata, null, 2) }}</pre>
          </div>
        </div>

        <!-- Actions -->
        <div class="artifact-actions">
          <a 
            :href="artifactUrl" 
            :download="`artifact-${artifact.hash.substring(0, 8)}`"
            class="btn btn-primary"
          >
            Download
          </a>
          <a 
            :href="artifactUrl" 
            target="_blank"
            class="btn"
          >
            Open in New Tab
          </a>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.artifact-detail {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
}

.loading,
.error {
  text-align: center;
  padding: 3rem;
  color: var(--color-text-secondary);
}

.error {
  color: var(--color-error, #dc3545);
}

.artifact-header {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 2rem;
  padding-bottom: 1rem;
  border-bottom: 2px solid var(--color-border);
}

.back-button {
  background: none;
  border: none;
  font-size: 1rem;
  cursor: pointer;
  color: var(--color-text);
  padding: 0.5rem;
  border-radius: var(--radius-sm);
  transition: background-color 0.2s;
}

.back-button:hover {
  background-color: var(--color-background);
}

.artifact-header h1 {
  font-size: 1.75rem;
  margin: 0;
}

.artifact-body {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.artifact-preview {
  display: flex;
  justify-content: center;
  align-items: center;
  background: repeating-conic-gradient(#ddd 0% 25%, #fff 0% 50%) 50% / 20px 20px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: 2rem;
  min-height: 400px;
}

.artifact-preview img {
  max-width: 100%;
  max-height: 600px;
  object-fit: contain;
  border-radius: var(--radius-sm);
}

.artifact-preview.non-image {
  background: var(--color-background);
  flex-direction: column;
  gap: 1rem;
}

.file-icon {
  font-size: 4rem;
}

.file-type {
  font-family: var(--font-mono);
  color: var(--color-text-secondary);
}

.metadata-section {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: 1.5rem;
}

.metadata-section h2 {
  margin-top: 0;
  margin-bottom: 1.5rem;
  font-size: 1.25rem;
}

.metadata-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1.5rem;
}

.metadata-item {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.metadata-item.full-width {
  grid-column: 1 / -1;
}

.metadata-item label {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--color-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.metadata-item span,
.metadata-item code {
  font-size: 1rem;
  color: var(--color-text);
}

.metadata-item code.hash {
  font-family: var(--font-mono);
  font-size: 0.875rem;
  word-break: break-all;
  background: var(--color-background);
  padding: 0.5rem;
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-border);
}

.archived-badge {
  display: inline-block;
  background: var(--color-warning, #ffc107);
  color: white;
  padding: 0.25rem 0.75rem;
  border-radius: var(--radius-sm);
  font-size: 0.875rem;
  font-weight: 600;
}

.entry-info {
  font-family: var(--font-mono);
  font-size: 0.875rem;
}

.custom-metadata {
  margin-top: 1.5rem;
  padding-top: 1.5rem;
  border-top: 1px solid var(--color-border);
}

.custom-metadata h3 {
  font-size: 1rem;
  margin-bottom: 0.75rem;
}

.custom-metadata pre {
  background: var(--color-background);
  padding: 1rem;
  border-radius: var(--radius-sm);
  overflow-x: auto;
  font-family: var(--font-mono);
  font-size: 0.875rem;
  border: 1px solid var(--color-border);
}

.artifact-actions {
  display: flex;
  gap: 1rem;
  padding-top: 1rem;
}

.btn {
  padding: 0.75rem 1.5rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  color: var(--color-text);
  font-size: 1rem;
  cursor: pointer;
  text-decoration: none;
  display: inline-block;
  transition: all 0.2s;
}

.btn:hover {
  background: var(--color-background);
  border-color: var(--color-text-secondary);
}

.btn-primary {
  background: var(--color-primary, #4f46e5);
  color: white;
  border-color: var(--color-primary, #4f46e5);
}

.btn-primary:hover {
  background: var(--color-primary-dark, #4338ca);
  border-color: var(--color-primary-dark, #4338ca);
}
</style>
