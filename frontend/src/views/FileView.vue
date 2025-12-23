<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from "vue";
import { useRoute } from "vue-router";
import FrontmatterViewer from "@/components/markdown/FrontmatterViewer.vue";

const route = useRoute();

const filePath = computed(() => {
  const path = route.query.path as string || "";
  // Decode any URL encoding to show clean filesystem paths
  // This handles %20 -> space, and other encoded characters
  try {
    return decodeURIComponent(path);
  } catch {
    // If decoding fails, return the original path
    return path;
  }
});
const loading = ref(true);
const error = ref<string | null>(null);
const fileContent = ref<string | null>(null);
const fileType = ref<string>("unknown");
const markdownData = ref<{
  frontmatter: any;
  rendered: any;
  content: string;
  blocks: any[];
} | null>(null);

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
  
  if (ext === "md" || ext === "markdown") return "markdown";
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
  markdownData.value = null;

  try {
    // For markdown files, try to fetch parsed data first
    if (fileType.value === "markdown") {
      try {
        const renderedResponse = await fetch(
          `/api/markdown/frontmatter/rendered?path=${encodeURIComponent(filePath.value)}`
        );
        
        if (renderedResponse.ok) {
          const renderedData = await renderedResponse.json();
          
          // Also fetch the parsed content
          const parsedResponse = await fetch(
            `/api/markdown/parse?path=${encodeURIComponent(filePath.value)}`
          );
          
          if (parsedResponse.ok) {
            const parsedData = await parsedResponse.json();
            markdownData.value = {
              frontmatter: parsedData.frontmatter,
              rendered: renderedData.rendered,
              content: parsedData.content,
              blocks: parsedData.blocks,
            };
          }
        }
      } catch (e) {
        // If parsing fails, fall back to raw text display
        console.warn("Failed to parse markdown, falling back to raw display", e);
      }
    }

    // Load file content (for text/image display or fallback)
    const response = await fetch(
      `/api/files/notebooks/content?path=${encodeURIComponent(filePath.value)}`
    );

    if (!response.ok) {
      throw new Error(`Failed to load file: ${response.statusText}`);
    }

    if (fileType.value === "text" || fileType.value === "markdown") {
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
      <!-- Markdown with frontmatter -->
      <div v-if="fileType === 'markdown' && markdownData" class="markdown-view">
        <!-- Display rendered frontmatter -->
        <FrontmatterViewer
          v-if="Object.keys(markdownData.rendered).length > 0"
          :rendered="markdownData.rendered"
        />

        <!-- Display content blocks -->
        <div v-if="markdownData.blocks.length > 0" class="content-blocks">
          <h3>Content Blocks</h3>
          <div
            v-for="(block, index) in markdownData.blocks"
            :key="index"
            class="content-block"
          >
            <div class="block-header">
              <span class="block-type">{{ block.type }}</span>
            </div>
            <pre class="block-content">{{ block.content }}</pre>
          </div>
        </div>

        <!-- Display main markdown content -->
        <div v-if="markdownData.content" class="markdown-content">
          <h3>Content</h3>
          <pre class="text-content">{{ markdownData.content }}</pre>
        </div>
      </div>

      <!-- Plain text content (including markdown fallback) -->
      <pre v-else-if="fileType === 'text' || fileType === 'markdown'" class="text-content">{{ fileContent }}</pre>

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

.markdown-view {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.content-blocks {
  background: var(--color-background);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: 1.5rem;
}

.content-blocks h3 {
  margin: 0 0 1rem 0;
  font-size: 1rem;
  font-weight: 600;
}

.content-block {
  margin-bottom: 1.5rem;
}

.content-block:last-child {
  margin-bottom: 0;
}

.block-header {
  display: flex;
  align-items: center;
  margin-bottom: 0.5rem;
}

.block-type {
  display: inline-block;
  padding: 0.125rem 0.625rem;
  background: #3b82f6;
  color: white;
  border-radius: var(--radius-sm);
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.block-content {
  padding: 1rem;
  margin: 0;
  font-family: var(--font-mono);
  font-size: 0.875rem;
  line-height: 1.6;
  background: var(--color-background-soft);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  overflow-x: auto;
  white-space: pre-wrap;
  word-wrap: break-word;
}

.markdown-content {
  background: var(--color-background);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: 1.5rem;
}

.markdown-content h3 {
  margin: 0 0 1rem 0;
  font-size: 1rem;
  font-weight: 600;
}
</style>
