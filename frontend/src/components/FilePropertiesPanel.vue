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
      <!-- Tags (editable) -->
      <div class="property-section">
        <h4>Tags</h4>
        <div class="tags-list">
          <span v-for="tag in tags" :key="tag" class="tag">
            {{ tag }}
            <button @click="removeTag(tag)" class="tag-remove" title="Remove tag">×</button>
          </span>
        </div>
        <div class="tag-input-wrapper">
          <input
            v-model="newTag"
            @keyup.enter="addTag"
            class="tag-input"
            placeholder="Add a tag..."
          />
          <button @click="addTag" class="tag-add-btn" :disabled="!newTag.trim()">Add</button>
        </div>
      </div>

      <!-- Custom Properties (editable) -->
      <div class="property-section">
        <h4>Custom Properties</h4>

        <!-- Existing custom properties -->
        <div class="custom-property-row" v-for="(value, key) in metadata" :key="key">
          <template v-if="editingProperty === key">
            <!-- Editing mode -->
            <input
              v-model="editPropertyValue"
              @blur="savePropertyEdit(key as string)"
              @keyup.enter="savePropertyEdit(key as string)"
              @keyup.escape="cancelPropertyEdit"
              class="property-edit-input"
              ref="editInput"
            />
            <div class="property-actions-inline">
              <button
                @click="savePropertyEdit(key as string)"
                class="btn-action btn-save"
                title="Save"
              >
                ✓
              </button>
              <button @click="cancelPropertyEdit" class="btn-action btn-cancel" title="Cancel">
                ✕
              </button>
            </div>
          </template>
          <template v-else>
            <!-- Display mode -->
            <span class="property-label">{{ key }}</span>
            <span
              class="property-value editable"
              @click="startEditProperty(key as string, value)"
              title="Click to edit"
              >{{ formatMetadataValue(value) }}</span
            >
            <button
              @click="removeProperty(key as string)"
              class="btn-remove-property"
              title="Remove property"
            >
              ×
            </button>
          </template>
        </div>
        <!-- Add new property -->
        <div class="add-property-form">
          <input
            v-model="newPropertyKey"
            class="property-key-input"
            placeholder="Property name"
            @keyup.enter="focusValueInput"
          />
          <input
            v-model="newPropertyValue"
            class="property-value-input"
            placeholder="Value"
            ref="valueInputRef"
            @keyup.enter="addProperty"
          />
          <button
            @click="addProperty"
            class="btn-add-property"
            :disabled="!newPropertyKey.trim()"
            title="Add property"
          >
            +
          </button>
        </div>

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

const editableTitle = ref("")
const editableDescription = ref("")
const newTag = ref("")

// Custom property editing state
const newPropertyKey = ref("")
const newPropertyValue = ref("")
const editingProperty = ref<string | null>(null)
const editPropertyValue = ref("")
const valueInputRef = ref<HTMLInputElement | null>(null)

// Get current properties or empty object
const currentProperties = computed(() => {
  return props.file?.properties || {}
})

// Sync with prop changes
watch(
  () => props.file,
  (newFile) => {
    if (newFile) {
      // Read from properties first, fall back to direct fields
      editableTitle.value = newFile.properties?.title || newFile.title || ""
      editableDescription.value = newFile.properties?.description || newFile.description || ""
    }
  },
  { immediate: true },
)

const tags = computed(() => {
  if (props.file?.properties?.tags) {
    return Array.isArray(props.file.properties.tags) ? props.file.properties.tags : []
  }
  return []
})

// Standard property fields that are handled separately
const STANDARD_FIELDS = ["title", "description", "tags"] as const
type StandardField = (typeof STANDARD_FIELDS)[number]

// Get all metadata except standard fields (title, description, tags)
const metadata = computed(() => {
  if (!props.file?.properties) return {}

  const result: Record<string, unknown> = {}
  for (const [key, value] of Object.entries(props.file.properties)) {
    if (!STANDARD_FIELDS.includes(key as StandardField)) {
      result[key] = value
    }
  }
  return result
})

function formatDate(dateStr: string): string {
  try {
    const date = new Date(dateStr)
    return date.toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    })
  } catch {
    return dateStr
  }
}

function formatSize(bytes: number): string {
  if (bytes === 0) return "0 B"
  const k = 1024
  const sizes = ["B", "KB", "MB", "GB"]
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i]
}

function formatMetadataValue(value: unknown): string {
  if (value === null || value === undefined) return ""
  if (Array.isArray(value)) return value.join(", ")
  if (typeof value === "object") return JSON.stringify(value)
  return String(value)
}

function emitPropertiesUpdate(updates: Record<string, any>) {
  const newProperties = {
    ...currentProperties.value,
    ...updates,
  }
  emit("updateProperties", newProperties)
}

function updateTitle() {
  const currentTitle = props.file?.properties?.title || props.file?.title || ""
  if (props.file && editableTitle.value !== currentTitle) {
    emitPropertiesUpdate({ title: editableTitle.value })
  }
}

function updateDescription() {
  const currentDescription = props.file?.properties?.description || props.file?.description || ""
  if (props.file && editableDescription.value !== currentDescription) {
    emitPropertiesUpdate({ description: editableDescription.value })
  }
}

function addTag() {
  const tagToAdd = newTag.value.trim()
  if (!tagToAdd) return

  const currentTags = tags.value
  if (!currentTags.includes(tagToAdd)) {
    emitPropertiesUpdate({ tags: [...currentTags, tagToAdd] })
  }
  newTag.value = ""
}

function removeTag(tagToRemove: string) {
  const currentTags = tags.value
  emitPropertiesUpdate({ tags: currentTags.filter((t) => t !== tagToRemove) })
}

// Custom property management
function addProperty() {
  const key = newPropertyKey.value.trim()
  if (!key) return

  // Parse value - try to detect type
  let value: unknown = newPropertyValue.value.trim()

  // Try to parse as JSON (for numbers, booleans, arrays, objects)
  if (value) {
    try {
      const parsed = JSON.parse(value as string)
      value = parsed
    } catch {
      // Keep as string if not valid JSON
    }
  }

  emitPropertiesUpdate({ [key]: value })
  newPropertyKey.value = ""
  newPropertyValue.value = ""
}

function focusValueInput() {
  valueInputRef.value?.focus()
}

function startEditProperty(key: string, value: unknown) {
  editingProperty.value = key
  // Format value for editing
  if (typeof value === "object") {
    editPropertyValue.value = JSON.stringify(value)
  } else {
    editPropertyValue.value = String(value ?? "")
  }
}

function savePropertyEdit(key: string) {
  if (editingProperty.value !== key) return

  // Parse value - try to detect type
  let value: unknown = editPropertyValue.value.trim()

  // Try to parse as JSON (for numbers, booleans, arrays, objects)
  if (value) {
    try {
      const parsed = JSON.parse(value as string)
      value = parsed
    } catch {
      // Keep as string if not valid JSON
    }
  }

  emitPropertiesUpdate({ [key]: value })
  editingProperty.value = null
  editPropertyValue.value = ""
}

function cancelPropertyEdit() {
  editingProperty.value = null
  editPropertyValue.value = ""
}

function removeProperty(key: string) {
  // Create new properties object without the removed key
  const newProperties = { ...currentProperties.value }
  delete newProperties[key]
  emit("updateProperties", newProperties)
}

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

function formatCommitDate(dateStr: string): string {
  try {
    const date = new Date(dateStr)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))

    if (diffDays === 0) {
      return date.toLocaleTimeString("en-US", {
        hour: "2-digit",
        minute: "2-digit",
      })
    } else if (diffDays === 1) {
      return "Yesterday"
    } else if (diffDays < 7) {
      return `${diffDays} days ago`
    } else {
      return date.toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
      })
    }
  } catch {
    return dateStr
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
    // If we're on the history tab when file changes, reload history
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

.tags-list {
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-sm);
}

.tag {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-xs);
  padding: var(--spacing-xs) var(--spacing-sm);
  background: var(--color-bg-tertiary);
  color: var(--color-text-secondary);
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
}

.tag-remove {
  background: none;
  border: none;
  color: var(--color-text-placeholder);
  cursor: pointer;
  padding: 0;
  line-height: 1;
  font-size: var(--text-sm);
  transition: color 0.2s;
}

.tag-remove:hover {
  color: var(--color-error);
}

.tag-input-wrapper {
  display: flex;
  gap: var(--spacing-sm);
  margin-top: var(--spacing-sm);
}

.tag-input {
  flex: 1;
  padding: var(--spacing-sm);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-sm);
  font-size: var(--text-sm);
  background: var(--color-bg-primary);
  color: var(--color-text-primary);
  transition: border-color 0.2s;
}

.tag-input:focus {
  outline: none;
  border-color: var(--color-border-focus);
}

.tag-add-btn {
  padding: var(--spacing-sm) var(--spacing-md);
  background: var(--color-primary);
  color: var(--color-text-inverse);
  border: none;
  border-radius: var(--radius-sm);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  cursor: pointer;
  transition: background 0.2s;
}

.tag-add-btn:hover:not(:disabled) {
  background: var(--color-primary-hover);
}

.tag-add-btn:disabled {
  background: var(--color-bg-disabled);
  color: var(--color-text-disabled);
  cursor: not-allowed;
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

/* Custom Properties Styles */
.custom-property-row {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-sm) 0;
  border-bottom: 1px solid var(--color-bg-secondary);
}

.custom-property-row .property-label {
  font-size: var(--text-sm);
  color: var(--color-text-tertiary);
  min-width: 80px;
  flex-shrink: 0;
}

.custom-property-row .property-value {
  flex: 1;
  font-size: var(--text-sm);
  color: var(--color-text-primary);
  word-break: break-all;
  text-align: left;
}

.custom-property-row .property-value.editable {
  cursor: pointer;
  padding: var(--spacing-xs) var(--spacing-sm);
  border-radius: var(--radius-sm);
  transition: background 0.2s;
}

.custom-property-row .property-value.editable:hover {
  background: var(--color-bg-secondary);
}

.property-edit-input {
  flex: 1;
  padding: var(--spacing-xs) var(--spacing-sm);
  border: 1px solid var(--color-border-focus);
  border-radius: var(--radius-sm);
  font-size: var(--text-sm);
  color: var(--color-text-primary);
  background: var(--color-bg-primary);
}

.property-edit-input:focus {
  outline: none;
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--color-primary) 20%, transparent);
}

.property-actions-inline {
  display: flex;
  gap: var(--spacing-xs);
}

.btn-action {
  background: none;
  border: none;
  padding: var(--spacing-xs);
  cursor: pointer;
  font-size: var(--text-sm);
  line-height: 1;
  border-radius: var(--radius-sm);
  transition:
    background 0.2s,
    color 0.2s;
}

.btn-save {
  color: var(--color-success, #22c55e);
}

.btn-save:hover {
  background: color-mix(in srgb, var(--color-success, #22c55e) 10%, transparent);
}

.btn-cancel {
  color: var(--color-text-tertiary);
}

.btn-cancel:hover {
  color: var(--color-text-primary);
  background: var(--color-bg-secondary);
}

.btn-remove-property {
  background: none;
  border: none;
  color: var(--color-text-placeholder);
  cursor: pointer;
  padding: var(--spacing-xs);
  line-height: 1;
  font-size: var(--text-sm);
  transition: color 0.2s;
  opacity: 0;
  flex-shrink: 0;
}

.custom-property-row:hover .btn-remove-property {
  opacity: 1;
}

.btn-remove-property:hover {
  color: var(--color-error);
}

.empty-properties {
  font-size: var(--text-sm);
  color: var(--color-text-placeholder);
  font-style: italic;
  padding: var(--spacing-md) 0;
}

.add-property-form {
  display: flex;
  gap: var(--spacing-sm);
  margin-top: var(--spacing-md);
  padding-top: var(--spacing-md);
  border-top: 1px solid var(--color-bg-secondary);
}

.property-key-input,
.property-value-input {
  flex: 1;
  padding: var(--spacing-sm);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-sm);
  font-size: var(--text-sm);
  background: var(--color-bg-primary);
  color: var(--color-text-primary);
  transition: border-color 0.2s;
}

.property-key-input {
  max-width: 40%;
}

.property-key-input:focus,
.property-value-input:focus {
  outline: none;
  border-color: var(--color-border-focus);
}

.btn-add-property {
  padding: var(--spacing-sm) var(--spacing-md);
  background: var(--color-primary);
  color: var(--color-text-inverse);
  border: none;
  border-radius: var(--radius-sm);
  font-size: var(--text-lg);
  font-weight: var(--font-medium);
  cursor: pointer;
  transition: background 0.2s;
  line-height: 1;
}

.btn-add-property:hover:not(:disabled) {
  background: var(--color-primary-hover);
}

.btn-add-property:disabled {
  background: var(--color-bg-disabled);
  color: var(--color-text-disabled);
  cursor: not-allowed;
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
