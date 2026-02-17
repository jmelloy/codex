<template>
  <div class="properties-panel">
    <div class="panel-header">
      <div class="panel-tabs">
        <button
          class="tab-btn"
          :class="{ active: activeTab === 'properties' }"
          @click="activeTab = 'properties'"
        >
          Properties
        </button>
        <button
          class="tab-btn"
          :class="{ active: activeTab === 'history' }"
          @click="switchToHistory"
        >
          History
        </button>
      </div>
      <button @click="$emit('close')" class="btn-close" title="Close">×</button>
    </div>

    <div v-if="file && activeTab === 'properties'" class="panel-content">
      <!-- Title (editable) -->
      <div class="property-group">
        <label>Title</label>
        <input
          v-model="editableTitle"
          @blur="updateTitle"
          @keyup.enter="updateTitle"
          class="property-input"
          placeholder="Untitled"
        />
      </div>

      <!-- Description (editable) -->
      <div class="property-group">
        <label>Description</label>
        <textarea
          v-model="editableDescription"
          @blur="updateDescription"
          class="property-textarea"
          placeholder="Add a description..."
          rows="3"
        ></textarea>
      </div>

      <TagsEditor
        :tags="tags"
        v-model:new-tag="newTag"
        @add="addTag"
        @remove="removeTag"
      />

      <CustomPropertiesEditor
        :metadata="metadata"
        :editing-property="editingProperty"
        v-model:edit-property-value="editPropertyValue"
        v-model:new-property-key="newPropertyKey"
        v-model:new-property-value="newPropertyValue"
        @start-edit="startEditProperty"
        @save-edit="savePropertyEdit"
        @cancel-edit="cancelPropertyEdit"
        @remove-property="removeProperty"
        @add-property="addProperty"
        @focus-value="focusValueInput"
      />

      <!-- File Info (read-only) -->
      <div class="property-section">
        <h4>File Info</h4>
        <div class="property-row">
          <span class="property-label">Path</span>
          <span class="property-value">{{ file.path }}</span>
        </div>
        <div class="property-row">
          <span class="property-label">Filename</span>
          <span class="property-value">{{ file.filename }}</span>
        </div>
        <div class="property-row">
          <span class="property-label">Type</span>
          <span class="property-value">{{ file.content_type }}</span>
        </div>
        <div class="property-row">
          <span class="property-label">Size</span>
          <span class="property-value">{{ formatSize(file.size) }}</span>
        </div>
      </div>

      <!-- Dates -->
      <div class="property-section">
        <h4>Dates</h4>
        <div class="property-row">
          <span class="property-label">Created</span>
          <span class="property-value">{{ formatDate(file.created_at) }}</span>
        </div>
        <div class="property-row">
          <span class="property-label">Modified</span>
          <span class="property-value">{{ formatDate(file.updated_at) }}</span>
        </div>
      </div>

      <!-- Actions -->
      <div class="property-actions">
        <button @click="confirmDelete" class="btn-delete">Delete File</button>
      </div>
    </div>

    <!-- History Tab -->
    <div v-else-if="file && activeTab === 'history'" class="panel-content history-content">
      <div v-if="historyLoading" class="history-loading">
        <span class="loading-spinner"></span>
        Loading history...
      </div>
      <div v-else-if="historyError" class="history-error">
        {{ historyError }}
      </div>
      <div v-else-if="history.length === 0" class="history-empty">
        No history available for this file.
      </div>
      <div v-else class="history-list">
        <div
          v-for="commit in history"
          :key="commit.hash"
          class="history-item"
          @click="selectCommit(commit)"
          :class="{ selected: selectedCommit?.hash === commit.hash }"
        >
          <div class="commit-header">
            <span class="commit-hash" :title="commit.hash">{{ commit.hash.substring(0, 7) }}</span>
            <span class="commit-date">{{ formatCommitDate(commit.date) }}</span>
          </div>
          <div class="commit-message">{{ commit.message }}</div>
          <div class="commit-author">{{ commit.author }}</div>
        </div>
      </div>

      <!-- Commit Preview -->
      <div v-if="selectedCommit" class="commit-preview">
        <div class="preview-header">
          <h4>Preview: {{ selectedCommit.hash.substring(0, 7) }}</h4>
          <button @click="selectedCommit = null" class="btn-close-preview" title="Close preview">
            ×
          </button>
        </div>
        <div v-if="commitContentLoading" class="preview-loading">Loading...</div>
        <div v-else-if="commitContent !== null" class="preview-content">
          <pre><code>{{ commitContent }}</code></pre>
        </div>
        <div class="preview-actions">
          <button @click="restoreCommit" class="btn-restore" title="Restore this version">
            Restore this version
          </button>
        </div>
      </div>
    </div>

    <div v-else class="empty-state">
      <p>No file selected</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from "vue"
import type { FileWithContent, FileHistoryEntry } from "../services/codex"
import { fileService } from "../services/codex"
import { useProperties } from "../composables/useProperties"
import { formatDate, formatCommitDate, formatSize } from "../utils/date"
import TagsEditor from "./TagsEditor.vue"
import CustomPropertiesEditor from "./CustomPropertiesEditor.vue"

interface Props {
  file: FileWithContent | null
  workspaceId: number
  notebookId: number
}

const props = defineProps<Props>()

const emit = defineEmits<{
  close: []
  updateProperties: [properties: Record<string, any>]
  delete: []
  restore: [content: string]
}>()

// Tab state
const activeTab = ref<"properties" | "history">("properties")

// History state
const history = ref<FileHistoryEntry[]>([])
const historyLoading = ref(false)
const historyError = ref<string | null>(null)
const selectedCommit = ref<FileHistoryEntry | null>(null)
const commitContent = ref<string | null>(null)
const commitContentLoading = ref(false)

// Use shared properties composable
const fileRef = computed(() => props.file)
const {
  editableTitle,
  editableDescription,
  newTag,
  newPropertyKey,
  newPropertyValue,
  editingProperty,
  editPropertyValue,
  tags,
  metadata,
  syncFromSource,
  updateTitle,
  updateDescription,
  addTag,
  removeTag,
  addProperty,
  focusValueInput,
  startEditProperty,
  savePropertyEdit,
  cancelPropertyEdit,
  removeProperty,
} = useProperties(fileRef, (event, properties) => emit(event, properties))

// Sync with prop changes
watch(() => props.file, () => syncFromSource(), { immediate: true })

function confirmDelete() {
  const displayName = props.file?.properties?.title || props.file?.title || props.file?.filename
  if (confirm(`Are you sure you want to delete "${displayName}"?`)) {
    emit("delete")
  }
}

// History functions
async function loadHistory() {
  if (!props.file || !props.workspaceId || !props.notebookId) return

  historyLoading.value = true
  historyError.value = null
  history.value = []
  selectedCommit.value = null
  commitContent.value = null

  try {
    const result = await fileService.getHistory(props.file.id, props.workspaceId, props.notebookId)
    history.value = result.history
  } catch (error: any) {
    historyError.value = error.response?.data?.detail || "Failed to load history"
  } finally {
    historyLoading.value = false
  }
}

function switchToHistory() {
  activeTab.value = "history"
  if (history.value.length === 0 && !historyLoading.value) {
    loadHistory()
  }
}

async function selectCommit(commit: FileHistoryEntry) {
  if (selectedCommit.value?.hash === commit.hash) {
    selectedCommit.value = null
    commitContent.value = null
    return
  }

  selectedCommit.value = commit
  commitContent.value = null
  commitContentLoading.value = true

  try {
    const result = await fileService.getAtCommit(
      props.file!.id,
      props.workspaceId,
      props.notebookId,
      commit.hash,
    )
    commitContent.value = result.content
  } catch (error: any) {
    commitContent.value = null
  } finally {
    commitContentLoading.value = false
  }
}

function restoreCommit() {
  if (commitContent.value !== null) {
    const displayName = props.file?.properties?.title || props.file?.title || props.file?.filename
    if (
      confirm(`Restore "${displayName}" to version ${selectedCommit.value?.hash.substring(0, 7)}?`)
    ) {
      emit("restore", commitContent.value)
      activeTab.value = "properties"
      selectedCommit.value = null
      commitContent.value = null
    }
  }
}

// Reset history when file changes
watch(
  () => props.file?.id,
  () => {
    history.value = []
    historyError.value = null
    selectedCommit.value = null
    commitContent.value = null
    if (activeTab.value === "history") {
      loadHistory()
    }
  },
)
</script>

<style scoped>
.properties-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--color-bg-primary);
  border-left: 1px solid var(--color-border-light);
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-sm) var(--spacing-lg);
  border-bottom: 1px solid var(--color-border-light);
  background: var(--color-bg-secondary);
}

.panel-header h3 {
  margin: 0;
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  color: var(--color-text-primary);
  text-transform: uppercase;
  letter-spacing: var(--tracking-wide);
}

/* Tabs */
.panel-tabs {
  display: flex;
  gap: var(--spacing-xs);
}

.tab-btn {
  background: none;
  border: none;
  padding: var(--spacing-sm) var(--spacing-md);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--color-text-tertiary);
  cursor: pointer;
  border-radius: var(--radius-sm);
  transition: all 0.2s;
}

.tab-btn:hover {
  color: var(--color-text-primary);
  background: var(--color-bg-tertiary);
}

.tab-btn.active {
  color: var(--color-primary);
  background: var(--color-bg-primary);
}

.btn-close {
  background: none;
  border: none;
  font-size: var(--text-xl);
  color: var(--color-text-tertiary);
  cursor: pointer;
  padding: var(--spacing-xs);
  line-height: 1;
  transition: color 0.2s;
}

.btn-close:hover {
  color: var(--color-text-primary);
}

.panel-content {
  flex: 1;
  overflow-y: auto;
  padding: var(--spacing-lg);
}

.property-group {
  margin-bottom: var(--spacing-lg);
}

.property-group label {
  display: block;
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  color: var(--color-text-tertiary);
  text-transform: uppercase;
  margin-bottom: var(--spacing-sm);
}

.property-input,
.property-textarea {
  width: 100%;
  padding: var(--spacing-sm);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-sm);
  font-size: var(--text-sm);
  color: var(--color-text-primary);
  background: var(--color-bg-primary);
  font-family: var(--font-sans);
  transition:
    border-color 0.2s,
    box-shadow 0.2s;
}

.property-input:focus,
.property-textarea:focus {
  outline: none;
  border-color: var(--color-border-focus);
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--color-primary) 20%, transparent);
}

.property-textarea {
  resize: vertical;
}

.property-section {
  margin-bottom: var(--spacing-xl);
}

.property-section h4 {
  margin: 0 0 var(--spacing-md);
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  color: var(--color-text-tertiary);
  text-transform: uppercase;
  letter-spacing: var(--tracking-wide);
}

.property-row {
  display: flex;
  justify-content: space-between;
  padding: var(--spacing-sm) 0;
  border-bottom: 1px solid var(--color-bg-secondary);
}

.property-label {
  font-size: var(--text-sm);
  color: var(--color-text-tertiary);
}

.property-value {
  font-size: var(--text-sm);
  color: var(--color-text-primary);
  text-align: right;
  max-width: 60%;
  word-break: break-all;
}

.property-actions {
  margin-top: auto;
  padding-top: var(--spacing-lg);
  border-top: 1px solid var(--color-border-light);
}

.btn-delete {
  width: 100%;
  padding: var(--spacing-md) var(--spacing-lg);
  background: var(--color-bg-primary);
  color: var(--color-error);
  border: 1px solid var(--color-error);
  border-radius: var(--radius-sm);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  cursor: pointer;
  transition: all 0.2s;
}

.btn-delete:hover {
  background: var(--color-error);
  color: var(--color-text-inverse);
}

.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--color-text-placeholder);
  font-size: var(--text-sm);
}

/* History Tab Styles */
.history-content {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.history-loading,
.history-error,
.history-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-xl);
  color: var(--color-text-tertiary);
  font-size: var(--text-sm);
}

.history-error {
  color: var(--color-error);
}

.loading-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid var(--color-border-light);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.history-item {
  padding: var(--spacing-md);
  background: var(--color-bg-secondary);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all 0.2s;
  border: 1px solid transparent;
}

.history-item:hover {
  background: var(--color-bg-tertiary);
}

.history-item.selected {
  border-color: var(--color-primary);
  background: color-mix(in srgb, var(--color-primary) 10%, var(--color-bg-secondary));
}

.commit-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-xs);
}

.commit-hash {
  font-family: var(--font-mono, monospace);
  font-size: var(--text-xs);
  color: var(--color-primary);
  background: var(--color-bg-tertiary);
  padding: 2px var(--spacing-xs);
  border-radius: var(--radius-sm);
}

.commit-date {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
}

.commit-message {
  font-size: var(--text-sm);
  color: var(--color-text-primary);
  margin-bottom: var(--spacing-xs);
  word-break: break-word;
}

.commit-author {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
}

/* Commit Preview */
.commit-preview {
  margin-top: var(--spacing-md);
  border-top: 1px solid var(--color-border-light);
  padding-top: var(--spacing-md);
}

.preview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-sm);
}

.preview-header h4 {
  margin: 0;
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--color-text-primary);
}

.btn-close-preview {
  background: none;
  border: none;
  font-size: var(--text-lg);
  color: var(--color-text-tertiary);
  cursor: pointer;
  padding: var(--spacing-xs);
  line-height: 1;
  transition: color 0.2s;
}

.btn-close-preview:hover {
  color: var(--color-text-primary);
}

.preview-loading {
  padding: var(--spacing-md);
  color: var(--color-text-tertiary);
  font-size: var(--text-sm);
}

.preview-content {
  max-height: 200px;
  overflow: auto;
  background: var(--color-bg-tertiary);
  border-radius: var(--radius-sm);
  padding: var(--spacing-sm);
}

.preview-content pre {
  margin: 0;
  font-size: var(--text-xs);
  font-family: var(--font-mono, monospace);
  white-space: pre-wrap;
  word-break: break-all;
}

.preview-content code {
  color: var(--color-text-secondary);
}

.preview-actions {
  margin-top: var(--spacing-md);
}

.btn-restore {
  width: 100%;
  padding: var(--spacing-md) var(--spacing-lg);
  background: var(--color-primary);
  color: var(--color-text-inverse);
  border: none;
  border-radius: var(--radius-sm);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  cursor: pointer;
  transition: background 0.2s;
}

.btn-restore:hover {
  background: var(--color-primary-hover);
}
</style>
