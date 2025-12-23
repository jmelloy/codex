<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from "vue";
import { useRoute } from "vue-router";
import FrontmatterViewer from "@/components/markdown/FrontmatterViewer.vue";
import MarkdownEditor from "@/components/markdown/MarkdownEditor.vue";

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
const isEditingMarkdown = ref(false);
const editableContent = ref<string>("");

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
      if (fileType.value === "markdown") {
        editableContent.value = fileContent.value;
      }
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

async function saveMarkdownFile() {
  if (!filePath.value || fileType.value !== "markdown") return;
  
  try {
    const response = await fetch(
      `/api/files/notebooks/content?path=${encodeURIComponent(filePath.value)}`,
      {
        method: "PUT",
        headers: {
          "Content-Type": "text/plain",
        },
        body: editableContent.value,
      }
    );
    
    if (!response.ok) {
      throw new Error(`Failed to save file: ${response.statusText}`);
    }
    
    fileContent.value = editableContent.value;
    isEditingMarkdown.value = false;
    // Reload to update markdown data
    await loadFile();
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed to save file";
  }
}

function startEditingMarkdown() {
  if (fileContent.value) {
    editableContent.value = fileContent.value;
    isEditingMarkdown.value = true;
  }
}

function cancelEditingMarkdown() {
  editableContent.value = fileContent.value || "";
  isEditingMarkdown.value = false;
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
      <div class="header-content">
        <h1>{{ filePath || "Select a file" }}</h1>
        <div v-if="fileType === 'markdown' && fileContent && !loading" class="header-actions">
          <button
            v-if="!isEditingMarkdown"
            @click="startEditingMarkdown"
            class="btn btn-primary"
          >
            ✏️ Edit
          </button>
          <template v-else>
            <button @click="saveMarkdownFile" class="btn btn-success">
              💾 Save
            </button>
            <button @click="cancelEditingMarkdown" class="btn btn-secondary">
              ❌ Cancel
            </button>
          </template>
        </div>
      </div>
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
      <!-- Markdown files with editor -->
      <div v-if="fileType === 'markdown'" class="markdown-view">
        <!-- Display rendered frontmatter if available -->
        <FrontmatterViewer
          v-if="markdownData && Object.keys(markdownData.rendered).length > 0"
          :rendered="markdownData.rendered"
        />
        
        <!-- Markdown editor/viewer -->
        <div class="markdown-editor-wrapper">
          <MarkdownEditor
            v-if="isEditingMarkdown"
            :model-value="editableContent"
            @update:model-value="editableContent = $event"
            :editable="true"
            :show-preview="true"
            min-height="400px"
            max-height="800px"
          />
          <MarkdownEditor
            v-else
            :model-value="fileContent || ''"
            :editable="false"
            :show-preview="false"
            min-height="400px"
            max-height="none"
          />
        </div>
      </div>

      <!-- Plain text content -->
      <pre v-else-if="fileType === 'text'" class="text-content">{{ fileContent }}</pre>

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

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
  flex-wrap: wrap;
}

.header-actions {
  display: flex;
  gap: 0.5rem;
}

.btn {
  padding: 0.5rem 1rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  font-size: 0.875rem;
  cursor: pointer;
  transition: all 0.2s;
  background: var(--color-surface);
  color: var(--color-text);
}

.btn:hover {
  background: var(--color-background);
}

.btn-primary {
  background: var(--color-primary, #4f46e5);
  color: white;
  border-color: var(--color-primary, #4f46e5);
}

.btn-primary:hover {
  background: #4338ca;
  border-color: #4338ca;
}

.btn-success {
  background: #10b981;
  color: white;
  border-color: #10b981;
}

.btn-success:hover {
  background: #059669;
  border-color: #059669;
}

.btn-secondary {
  background: var(--color-background);
  color: var(--color-text);
  border-color: var(--color-border);
}

.btn-secondary:hover {
  background: #e5e7eb;
}

.file-header h1 {
  font-size: 1.5rem;
  font-family: var(--font-mono);
  word-break: break-all;
  margin: 0;
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

.markdown-editor-wrapper {
  background: var(--color-surface);
  border-radius: var(--radius-md);
  overflow: hidden;
}
</style>
