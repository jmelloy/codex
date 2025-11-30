<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from "vue";
import { useRoute } from "vue-router";
import { useNotebooksStore } from "@/stores/notebooks";

const route = useRoute();
const notebooksStore = useNotebooksStore();

const filePath = computed(() => route.query.path as string || "");
const loading = ref(true);
const error = ref<string | null>(null);
const fileContent = ref<string | null>(null);
const fileType = ref<string>("unknown");

// Track the current object URL to clean up on changes
let currentObjectUrl: string | null = null;

function revokeCurrentObjectUrl() {
  if (currentObjectUrl) {
    URL.revokeObjectURL(currentObjectUrl);
    currentObjectUrl = null;
  }
}

// Determine file type from extension
function getFileType(path: string): string {
  const ext = path.split(".").pop()?.toLowerCase() || "";
  const textTypes = ["md", "txt", "json", "py", "js", "ts", "html", "css", "yaml", "yml", "toml", "xml", "csv"];
  const imageTypes = ["png", "jpg", "jpeg", "gif", "svg", "webp"];
  
  if (textTypes.includes(ext)) return "text";
  if (imageTypes.includes(ext)) return "image";
  if (ext === "pdf") return "pdf";
  return "binary";
}

async function loadFile() {
  if (!filePath.value) {
    loading.value = false;
    return;
  }

  // Clean up previous object URL before loading new file
  revokeCurrentObjectUrl();

  loading.value = true;
  error.value = null;
  fileType.value = getFileType(filePath.value);

  try {
    const response = await fetch(
      `/api/files/notebooks/content?workspace_path=${encodeURIComponent(notebooksStore.workspacePath)}&path=${encodeURIComponent(filePath.value)}`
    );

    if (!response.ok) {
      throw new Error(`Failed to load file: ${response.statusText}`);
    }

    if (fileType.value === "text") {
      fileContent.value = await response.text();
    } else if (fileType.value === "image") {
      const blob = await response.blob();
      currentObjectUrl = URL.createObjectURL(blob);
      fileContent.value = currentObjectUrl;
    } else {
      fileContent.value = null;
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed to load file";
  } finally {
    loading.value = false;
  }
}

onMounted(loadFile);
watch(filePath, loadFile);

// Clean up object URLs when component unmounts
onUnmounted(() => {
  revokeCurrentObjectUrl();
});
</script>

<template>
  <div class="file-view">
    <div class="file-header">
      <h1>{{ filePath || "Select a file" }}</h1>
    </div>

    <div v-if="loading" class="loading">
      Loading file...
    </div>

    <div v-else-if="error" class="error">
      {{ error }}
    </div>

    <div v-else-if="!filePath" class="no-file">
      <p>Select a file from the sidebar to view it here.</p>
    </div>

    <div v-else class="file-content">
      <!-- Text content -->
      <pre v-if="fileType === 'text'" class="text-content">{{ fileContent }}</pre>

      <!-- Image content -->
      <div v-else-if="fileType === 'image'" class="image-content">
        <img :src="fileContent || ''" :alt="filePath" />
      </div>

      <!-- Unsupported file type -->
      <div v-else class="unsupported">
        <p>This file type cannot be previewed.</p>
        <p class="file-type">File type: {{ fileType }}</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.file-view {
  padding: 2rem;
  max-width: 1200px;
  margin: 0 auto;
}

.file-header {
  margin-bottom: 2rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid var(--color-border);
}

.file-header h1 {
  font-size: 1.5rem;
  font-family: var(--font-mono);
  word-break: break-all;
}

.loading,
.error,
.no-file {
  padding: 2rem;
  text-align: center;
  color: var(--color-text-secondary);
}

.error {
  color: var(--color-error, #dc3545);
}

.file-content {
  background: var(--color-background);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.text-content {
  padding: 1rem;
  margin: 0;
  font-family: var(--font-mono);
  font-size: 0.875rem;
  line-height: 1.6;
  overflow-x: auto;
  white-space: pre-wrap;
  word-wrap: break-word;
}

.image-content {
  display: flex;
  justify-content: center;
  padding: 1rem;
  background: repeating-conic-gradient(#ddd 0% 25%, #fff 0% 50%) 50% / 20px 20px;
}

.image-content img {
  max-width: 100%;
  max-height: 80vh;
  object-fit: contain;
}

.unsupported {
  padding: 2rem;
  text-align: center;
}

.file-type {
  color: var(--color-text-secondary);
  font-size: 0.875rem;
  font-family: var(--font-mono);
}
</style>
