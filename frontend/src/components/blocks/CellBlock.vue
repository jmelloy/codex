<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import { marked } from "marked";
import DOMPurify from "dompurify";
import { useNotebooksStore } from "@/stores/notebooks";
import { artifactsApi, entriesApi } from "@/api";
import type { Entry, Artifact } from "@/types";

const props = defineProps<{
  entry: Entry;
  executing?: boolean;
}>();

const emit = defineEmits<{
  (e: "execute"): void;
  (e: "update", data: Partial<Entry>): void;
  (e: "delete"): void;
  (e: "create-variation"): void;
}>();

const router = useRouter();
const notebooksStore = useNotebooksStore();

const isExpanded = ref(true);
const isEditing = ref(false);
const editInputs = ref({ ...props.entry.inputs });
const editInputsJson = ref(JSON.stringify(props.entry.inputs, null, 2));
const artifacts = ref<Artifact[]>([]);
const loadingArtifacts = ref(false);

const entryTypeIcon = computed(() => {
  const icons: Record<string, string> = {
    text: "📝",
    custom: "🔧",
    api_call: "🌐",
    database_query: "🗃️",
    graphql: "◈",
  };
  return icons[props.entry.entry_type] || "📄";
});

const isTextEntry = computed(() => props.entry.entry_type === "text");

const textContent = computed(() => {
  if (isTextEntry.value && props.entry.inputs?.content) {
    return props.entry.inputs.content as string;
  }
  return "";
});

const sanitizedTextContent = computed(() => {
  if (!textContent.value) return "";
  const rawHtml = marked(textContent.value) as string;
  return DOMPurify.sanitize(rawHtml);
});

const statusClass = computed(() => {
  return {
    created: "status-created",
    running: "status-running",
    completed: "status-completed",
    failed: "status-failed",
  }[props.entry.status] || "";
});

const canExecute = computed(() => props.entry.status === "created");

const imageArtifacts = computed(() => {
  return artifacts.value.filter((a) => a.type.startsWith("image/"));
});

function toggleExpand() {
  isExpanded.value = !isExpanded.value;
}

function startEditing() {
  editInputs.value = { ...props.entry.inputs };
  editInputsJson.value = JSON.stringify(props.entry.inputs, null, 2);
  isEditing.value = true;
}

function cancelEditing() {
  isEditing.value = false;
  editInputs.value = { ...props.entry.inputs };
  editInputsJson.value = JSON.stringify(props.entry.inputs, null, 2);
}

function saveEditing() {
  try {
    const parsed = JSON.parse(editInputsJson.value);
    emit("update", { inputs: parsed });
    isEditing.value = false;
  } catch (e) {
    alert("Invalid JSON");
  }
}

function formatOutput(outputs: Record<string, unknown>): string {
  return JSON.stringify(outputs, null, 2);
}

function getThumbnailUrl(artifact: Artifact): string {
  return artifactsApi.getUrl(notebooksStore.workspacePath, artifact.hash, true);
}

function viewArtifactDetail(artifact: Artifact) {
  router.push({
    name: "artifact-detail",
    params: { hash: artifact.hash },
    query: { entryId: props.entry.id },
  });
}

async function loadArtifacts() {
  if (props.entry.artifacts && props.entry.artifacts.length > 0) {
    artifacts.value = props.entry.artifacts;
    return;
  }

  loadingArtifacts.value = true;
  try {
    artifacts.value = await entriesApi.getArtifacts(
      notebooksStore.workspacePath,
      props.entry.id
    );
  } catch (e) {
    console.error("Failed to load artifacts:", e);
  } finally {
    loadingArtifacts.value = false;
  }
}

onMounted(() => {
  if (props.entry.status === "completed") {
    loadArtifacts();
  }
});
</script>

<template>
  <div class="cell-block" :class="[statusClass, { expanded: isExpanded }]">
    <div class="cell-header" @click="toggleExpand">
      <div class="cell-info">
        <span class="cell-icon">{{ entryTypeIcon }}</span>
        <span class="cell-title">{{ entry.title }}</span>
        <span class="cell-id">{{ entry.id.slice(0, 8) }}</span>
      </div>
      <div class="cell-status-row">
        <span class="cell-status" :class="statusClass">{{ entry.status }}</span>
        <span class="cell-expand">{{ isExpanded ? "▼" : "▶" }}</span>
      </div>
    </div>

    <div v-if="isExpanded" class="cell-body">
      <!-- Text entry: show content as rendered markdown -->
      <div v-if="isTextEntry" class="cell-section text-content-section">
        <div class="text-content-rendered" v-html="sanitizedTextContent"></div>
      </div>

      <!-- Non-text entries: show inputs/outputs as before -->
      <template v-else>
        <div class="cell-section inputs-section">
          <div class="section-header">
            <h4>Inputs</h4>
            <button
              v-if="!isEditing && entry.status === 'created'"
              class="btn-icon"
              @click.stop="startEditing"
              title="Edit inputs"
            >
              ✏️
            </button>
          </div>

          <div v-if="isEditing" class="edit-form">
            <textarea
              v-model="editInputsJson"
              class="json-editor"
              rows="8"
              placeholder='{"key": "value"}'
            ></textarea>
            <div class="edit-actions">
              <button class="btn btn-secondary" @click="cancelEditing">Cancel</button>
              <button class="btn btn-primary" @click="saveEditing">Save</button>
            </div>
          </div>

          <pre v-else class="code-block">{{ JSON.stringify(entry.inputs, null, 2) }}</pre>
        </div>

        <div v-if="entry.outputs && Object.keys(entry.outputs).length" class="cell-section outputs-section">
          <h4>Outputs</h4>
          <pre class="code-block output-block">{{ formatOutput(entry.outputs) }}</pre>
        </div>

        <div v-if="entry.execution?.error" class="cell-section error-section">
          <h4>Error</h4>
          <pre class="code-block error-block">{{ entry.execution.error }}</pre>
        </div>

        <div v-if="entry.execution?.duration_seconds" class="cell-section meta-section">
          <span class="meta-item">
            ⏱️ {{ entry.execution.duration_seconds.toFixed(2) }}s
          </span>
          <span v-if="entry.execution?.started_at" class="meta-item">
            🕐 {{ new Date(entry.execution.started_at).toLocaleString() }}
          </span>
        </div>
      </template>

      <!-- Artifacts Section (for all entry types) -->
      <div v-if="imageArtifacts.length > 0" class="cell-section artifacts-section">
        <h4>Artifacts ({{ artifacts.length }})</h4>
        <div class="artifacts-gallery">
          <div
            v-for="artifact in imageArtifacts"
            :key="artifact.id"
            class="artifact-item"
            @click="viewArtifactDetail(artifact)"
            role="button"
            tabindex="0"
            @keydown.enter="viewArtifactDetail(artifact)"
          >
            <img
              :src="getThumbnailUrl(artifact)"
              :alt="`Artifact ${artifact.hash.substring(0, 8)}`"
              class="artifact-thumbnail"
            />
            <div class="artifact-overlay">
              <span class="artifact-type">{{ artifact.type }}</span>
            </div>
          </div>
        </div>
        <p v-if="artifacts.length > imageArtifacts.length" class="non-image-note">
          + {{ artifacts.length - imageArtifacts.length }} non-image artifact(s)
        </p>
      </div>
      <div v-else-if="loadingArtifacts" class="cell-section artifacts-section">
        <p class="loading-text">Loading artifacts...</p>
      </div>

      <div class="cell-actions">
        <!-- Text entries are content-only and don't need execution like API calls or queries -->
        <button
          v-if="canExecute && !isTextEntry"
          class="btn btn-primary"
          :disabled="executing"
          @click.stop="emit('execute')"
        >
          {{ executing ? "Running..." : "▶ Run" }}
        </button>
        <button
          class="btn btn-secondary"
          @click.stop="emit('create-variation')"
        >
          📋 Variation
        </button>
        <button
          class="btn btn-danger"
          @click.stop="emit('delete')"
        >
          🗑️ Delete
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.cell-block {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  overflow: hidden;
  transition: border-color 0.2s, box-shadow 0.2s;
  position: relative;
}

.cell-block:hover {
  box-shadow: var(--shadow-md);
}

.cell-block.status-running {
  border-color: var(--color-warning);
  animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.85; }
}

/* Respect user's motion preferences for accessibility */
@media (prefers-reduced-motion: reduce) {
  .cell-block.status-running {
    animation: none;
  }
}

.cell-block.status-completed {
  border-left: 4px solid var(--color-success);
}

.cell-block.status-failed {
  border-left: 4px solid var(--color-error);
}

.cell-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 1rem;
  background: linear-gradient(to bottom, var(--color-background), rgba(245, 240, 230, 0.5));
  cursor: pointer;
  user-select: none;
  border-bottom: 1px dashed var(--color-border);
}

.cell-header:hover {
  background: var(--color-background);
}

.cell-info {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.cell-icon {
  font-size: 1rem;
}

.cell-title {
  font-weight: 500;
  color: var(--color-text);
  font-family: var(--font-body);
}

.cell-id {
  font-family: var(--font-mono);
  font-size: 0.7rem;
  color: var(--color-text-secondary);
  background: var(--color-border);
  padding: 0.125rem 0.375rem;
  border-radius: var(--radius-sm);
}

.cell-status-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.cell-status {
  font-size: 0.7rem;
  font-weight: 600;
  padding: 0.25rem 0.5rem;
  border-radius: var(--radius-sm);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  font-family: var(--font-mono);
}

.status-created {
  background: #e8f0e3;
  color: var(--color-primary);
}

.status-running {
  background: #fef3cd;
  color: var(--color-warning);
}

.status-completed {
  background: #e8f5e3;
  color: var(--color-success);
}

.status-failed {
  background: #fbe8e8;
  color: var(--color-error);
}

.cell-expand {
  font-size: 0.625rem;
  color: var(--color-text-secondary);
}

.cell-body {
  padding: 1rem;
  background: var(--color-surface);
}

.cell-section {
  margin-bottom: 1rem;
}

.cell-section:last-child {
  margin-bottom: 0;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}

.cell-section h4 {
  font-size: 0.7rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--color-text-secondary);
  font-family: var(--font-mono);
}

.btn-icon {
  background: none;
  border: none;
  padding: 0.25rem;
  cursor: pointer;
  font-size: 0.875rem;
  opacity: 0.6;
}

.btn-icon:hover {
  opacity: 1;
}

.code-block {
  background: var(--color-background);
  padding: 0.75rem;
  border-radius: var(--radius-sm);
  font-family: var(--font-mono);
  font-size: 0.8rem;
  line-height: 1.5;
  overflow-x: auto;
  white-space: pre-wrap;
  word-break: break-word;
  border-left: 3px solid var(--color-border);
}

.output-block {
  background: #f5faf3;
  border-left-color: var(--color-success);
}

.error-block {
  background: #fdf5f5;
  border-left-color: var(--color-error);
  color: var(--color-error);
}

.meta-section {
  display: flex;
  gap: 1rem;
  padding-top: 0.5rem;
  border-top: 1px dashed var(--color-border);
}

.meta-item {
  font-size: 0.75rem;
  color: var(--color-text-secondary);
  font-family: var(--font-mono);
}

.cell-actions {
  display: flex;
  gap: 0.5rem;
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px dashed var(--color-border);
}

.edit-form {
  margin-bottom: 1rem;
}

.json-editor {
  width: 100%;
  font-family: var(--font-mono);
  font-size: 0.8rem;
  padding: 0.75rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-background);
  resize: vertical;
  color: var(--color-text);
}

.edit-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
  margin-top: 1rem;
}

.btn-danger {
  background: #fbe8e8;
  color: var(--color-error);
  border: 1px solid #e8c4c4;
}

.btn-danger:hover {
  background: #f5d5d5;
}

/* Text content section styles */
.text-content-section {
  padding: 0;
}

.text-content-rendered {
  line-height: 1.7;
  font-family: var(--font-body);
}

.text-content-rendered :deep(h1),
.text-content-rendered :deep(h2),
.text-content-rendered :deep(h3) {
  margin-top: 1rem;
  margin-bottom: 0.5rem;
  font-family: var(--font-handwritten);
  color: var(--color-primary);
}

.text-content-rendered :deep(h1:first-child),
.text-content-rendered :deep(h2:first-child),
.text-content-rendered :deep(h3:first-child) {
  margin-top: 0;
}

.text-content-rendered :deep(p) {
  margin-bottom: 0.75rem;
}

.text-content-rendered :deep(p:last-child) {
  margin-bottom: 0;
}

.text-content-rendered :deep(ul),
.text-content-rendered :deep(ol) {
  margin-left: 1.5rem;
  margin-bottom: 0.75rem;
}

.text-content-rendered :deep(code) {
  background: var(--color-background);
  padding: 0.125rem 0.375rem;
  border-radius: var(--radius-sm);
  font-size: 0.875em;
  font-family: var(--font-mono);
}

.text-content-rendered :deep(pre) {
  background: var(--color-background);
  padding: 1rem;
  border-radius: var(--radius-md);
  overflow-x: auto;
  margin-bottom: 0.75rem;
  border-left: 3px solid var(--color-primary);
}

.text-content-rendered :deep(pre code) {
  background: none;
  padding: 0;
}

.text-content-rendered :deep(blockquote) {
  border-left: 3px solid var(--color-primary);
  padding-left: 1rem;
  margin: 0.75rem 0;
  color: var(--color-text-secondary);
  font-style: italic;
}

/* Artifacts Section */
.artifacts-section {
  margin-top: 1rem;
}

.artifacts-gallery {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 0.75rem;
  margin-top: 0.75rem;
}

.artifact-item {
  position: relative;
  aspect-ratio: 1;
  border-radius: var(--radius-sm);
  overflow: hidden;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
  background: repeating-conic-gradient(#e0e0e0 0% 25%, #f5f5f5 0% 50%) 50% / 10px 10px;
  border: 1px solid var(--color-border);
}

.artifact-item:hover {
  transform: scale(1.05);
  box-shadow: var(--shadow-md);
  z-index: 1;
}

.artifact-item:focus {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}

.artifact-thumbnail {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.artifact-overlay {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  background: linear-gradient(to top, rgba(0, 0, 0, 0.7), transparent);
  padding: 0.5rem;
  opacity: 0;
  transition: opacity 0.2s;
}

.artifact-item:hover .artifact-overlay {
  opacity: 1;
}

.artifact-type {
  font-size: 0.625rem;
  color: white;
  font-family: var(--font-mono);
}

.non-image-note {
  font-size: 0.75rem;
  color: var(--color-text-secondary);
  margin-top: 0.5rem;
  font-style: italic;
}

.loading-text {
  color: var(--color-text-secondary);
  font-size: 0.875rem;
  font-style: italic;
}
</style>
