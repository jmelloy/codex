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

    <div v-if="block && activeTab === 'properties'" class="panel-content">
      <!-- Icon & Cover Image -->
      <div class="property-group icon-cover-group">
        <div class="icon-cover-row">
          <!-- Icon picker -->
          <div class="icon-picker-wrapper">
            <label>Icon</label>
            <button class="icon-preview-btn" @click="showEmojiPicker = !showEmojiPicker">
              <span v-if="currentIcon" class="icon-preview-emoji">{{ currentIcon }}</span>
              <span v-else class="icon-preview-placeholder">Add icon</span>
            </button>
            <div v-if="showEmojiPicker" class="emoji-picker-dropdown">
              <EmojiPicker @select="handleIconSelect" />
            </div>
          </div>

          <!-- Cover image -->
          <div class="cover-picker-wrapper">
            <label>Cover image</label>
            <div v-if="currentCoverImage" class="cover-preview">
              <img :src="currentCoverImage" alt="Cover" class="cover-preview-img" />
              <button class="cover-remove-btn" @click="removeCoverImage" title="Remove cover">×</button>
            </div>
            <div class="cover-input-row">
              <input
                v-model="coverImageUrl"
                class="property-input cover-url-input"
                placeholder="Paste image URL..."
                @keyup.enter="setCoverImage"
              />
              <button class="cover-set-btn" @click="setCoverImage" :disabled="!coverImageUrl.trim()">Set</button>
            </div>
          </div>
        </div>
      </div>

      <!-- Title (editable) -->
      <div class="property-group">
        <label>Title</label>
        <input
          v-model="editableTitle"
          @blur="updateTitle"
          @keyup.enter="updateTitle"
          class="property-input title-input"
          placeholder="Untitled"
        />
      </div>

      <!-- Description (editable) -->
      <div class="property-group">
        <label>Description</label>
        <textarea
          v-model="editableDescription"
          @blur="updateDescription"
          class="property-textarea description-input"
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

      <!-- Block Info (read-only) -->
      <div class="property-section">
        <h4>Block Info</h4>
        <div class="property-row">
          <span class="property-label">Path</span>
          <span class="property-value">{{ block.path }}</span>
        </div>
        <div class="property-row">
          <span class="property-label">Name</span>
          <span class="property-value">{{ block.filename || block.path.split('/').pop() || block.path }}</span>
        </div>
        <div class="property-row">
          <span class="property-label">Type</span>
          <span class="property-value">{{ block.content_type || 'unknown' }}</span>
        </div>
        <div class="property-row">
          <span class="property-label">Size</span>
          <span class="property-value">{{ formatSize(block.size || 0) }}</span>
        </div>
      </div>

      <!-- Dates -->
      <div class="property-section">
        <h4>Dates</h4>
        <div class="property-row">
          <span class="property-label">Created</span>
          <span class="property-value">{{ formatDate(block.created_at) }}</span>
        </div>
        <div class="property-row">
          <span class="property-label">Modified</span>
          <span class="property-value">{{ formatDate(block.updated_at) }}</span>
        </div>
      </div>

      <!-- Actions -->
      <div class="property-actions">
        <button @click="confirmDelete" class="btn-delete">Delete Block</button>
      </div>
    </div>

    <!-- History Tab -->
    <div v-else-if="block && activeTab === 'history'" class="panel-content history-content">
      <div v-if="historyLoading" class="history-loading">
        <span class="loading-spinner"></span>
        Loading history...
      </div>
      <div v-else-if="historyError" class="history-error">
        {{ historyError }}
      </div>
      <div v-else-if="history.length === 0" class="history-empty">
        No history available for this page.
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
          <div v-if="commit.files_changed && commit.files_changed.length > 0" class="commit-files-summary">
            {{ commit.files_changed.length }} file{{ commit.files_changed.length !== 1 ? 's' : '' }} changed
          </div>
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
        <!-- Page-level diff view -->
        <div v-else-if="commitFiles.length > 0" class="preview-files">
          <div v-for="file in commitFiles" :key="file.path" class="file-change">
            <div class="file-change-header">
              <span class="change-type" :class="'change-' + file.change_type">{{ file.change_type }}</span>
              <span class="file-path">{{ file.path }}</span>
            </div>
            <div v-if="file.diff" class="file-diff">
              <pre><code>{{ file.diff }}</code></pre>
            </div>
          </div>
        </div>
        <!-- Single file content view (fallback for non-page blocks) -->
        <div v-else-if="commitContent !== null" class="preview-content">
          <pre><code>{{ commitContent }}</code></pre>
          <div class="preview-actions">
            <button @click="restoreCommit" class="btn-restore" title="Restore this version">
              Restore this version
            </button>
          </div>
        </div>
      </div>
    </div>

    <div v-else class="empty-state">
      <p>No block selected</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from "vue"
import type { Block, FileHistoryEntry, FileChangeDetail, PageAtCommit } from "../services/codex"
import { blockService } from "../services/codex"
import { useProperties } from "../composables/useProperties"
import { formatDate, formatCommitDate, formatSize } from "../utils/date"
import TagsEditor from "./TagsEditor.vue"
import CustomPropertiesEditor from "./CustomPropertiesEditor.vue"
import EmojiPicker from "./EmojiPicker.vue"

interface Props {
  block: (Block & { content?: string }) | null
  workspaceId: string
  notebookId: string
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

// Icon & Cover state
const showEmojiPicker = ref(false)
const coverImageUrl = ref("")

const currentIcon = computed(() => props.block?.properties?.icon || "")
const currentCoverImage = computed(() => props.block?.properties?.cover_image || "")

function handleIconSelect(emoji: string) {
  showEmojiPicker.value = false
  emit("updateProperties", { ...props.block?.properties, icon: emoji || undefined })
}

function setCoverImage() {
  const url = coverImageUrl.value.trim()
  if (!url) return
  emit("updateProperties", { ...props.block?.properties, cover_image: url })
  coverImageUrl.value = ""
}

function removeCoverImage() {
  const newProps = { ...props.block?.properties }
  delete newProps.cover_image
  emit("updateProperties", newProps)
}

// History state
const history = ref<FileHistoryEntry[]>([])
const historyLoading = ref(false)
const historyError = ref<string | null>(null)
const selectedCommit = ref<FileHistoryEntry | null>(null)
const commitContent = ref<string | null>(null)
const commitFiles = ref<FileChangeDetail[]>([])
const commitContentLoading = ref(false)

// Use shared properties composable
const fileRef = computed(() => props.block)
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
watch(() => props.block, () => syncFromSource(), { immediate: true })

function confirmDelete() {
  const displayName = props.block?.properties?.title || props.block?.title || props.block?.filename || props.block?.path.split("/").pop()
  if (confirm(`Are you sure you want to delete "${displayName}"?`)) {
    emit("delete")
  }
}

// History functions
async function loadHistory() {
  if (!props.block || !props.workspaceId || !props.notebookId) return

  historyLoading.value = true
  historyError.value = null
  history.value = []
  selectedCommit.value = null
  commitContent.value = null

  try {
    const result = await blockService.getHistory(props.block.block_id, props.notebookId, props.workspaceId)
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
    commitFiles.value = []
    return
  }

  selectedCommit.value = commit
  commitContent.value = null
  commitFiles.value = []
  commitContentLoading.value = true

  try {
    const result = await blockService.getAtCommit(
      props.block!.block_id,
      props.notebookId,
      props.workspaceId,
      commit.hash,
    )
    if ("files" in result) {
      commitFiles.value = (result as PageAtCommit).files
    } else {
      commitContent.value = result.content
    }
  } catch (error: any) {
    commitContent.value = null
    commitFiles.value = []
  } finally {
    commitContentLoading.value = false
  }
}

function restoreCommit() {
  if (commitContent.value !== null) {
    const displayName = props.block?.properties?.title || props.block?.title || props.block?.filename || props.block?.path.split("/").pop()
    if (
      confirm(`Restore "${displayName}" to version ${selectedCommit.value?.hash.substring(0, 7)}?`)
    ) {
      emit("restore", commitContent.value)
      activeTab.value = "properties"
      selectedCommit.value = null
      commitContent.value = null
      commitFiles.value = []
    }
  }
}

// Reset history when file changes
watch(
  () => props.block?.block_id,
  () => {
    history.value = []
    historyError.value = null
    selectedCommit.value = null
    commitContent.value = null
    commitFiles.value = []
    if (activeTab.value === "history") {
      loadHistory()
    }
  },
)
</script>

<style src="./properties-panel.css"></style>
<style scoped>
/* Override panel-header padding for the tabbed layout */
.panel-header {
  padding: var(--spacing-sm) var(--spacing-lg);
}

/* Icon & Cover */
.icon-cover-group {
  border-bottom: 1px solid var(--color-border-light);
  padding-bottom: var(--spacing-md);
}

.icon-cover-row {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.icon-picker-wrapper {
  position: relative;
}

.icon-picker-wrapper label,
.cover-picker-wrapper label {
  display: block;
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
  color: var(--color-text-tertiary);
  margin-bottom: var(--spacing-xs);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.icon-preview-btn {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-sm) var(--spacing-md);
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all 0.2s;
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
  width: 100%;
}

.icon-preview-btn:hover {
  background: var(--color-bg-tertiary);
  border-color: var(--color-border);
}

.icon-preview-emoji {
  font-size: 24px;
  line-height: 1;
}

.icon-preview-placeholder {
  color: var(--color-text-tertiary);
}

.emoji-picker-dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  z-index: 200;
  margin-top: 4px;
}

.cover-preview {
  position: relative;
  margin-bottom: var(--spacing-sm);
  border-radius: var(--radius-sm);
  overflow: hidden;
}

.cover-preview-img {
  width: 100%;
  height: 80px;
  object-fit: cover;
  display: block;
  border-radius: var(--radius-sm);
}

.cover-remove-btn {
  position: absolute;
  top: 4px;
  right: 4px;
  width: 20px;
  height: 20px;
  background: rgba(0, 0, 0, 0.6);
  color: white;
  border: none;
  border-radius: 50%;
  cursor: pointer;
  font-size: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
  opacity: 0;
  transition: opacity 0.2s;
}

.cover-preview:hover .cover-remove-btn {
  opacity: 1;
}

.cover-input-row {
  display: flex;
  gap: var(--spacing-xs);
}

.cover-url-input {
  flex: 1;
  min-width: 0;
}

.cover-set-btn {
  padding: var(--spacing-sm) var(--spacing-md);
  background: var(--color-primary);
  color: var(--color-text-inverse, #fff);
  border: none;
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
  cursor: pointer;
  transition: background 0.2s;
  white-space: nowrap;
}

.cover-set-btn:hover:not(:disabled) {
  background: var(--color-primary-hover);
}

.cover-set-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
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

/* Files changed summary in commit list */
.commit-files-summary {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
  margin-top: var(--spacing-xs);
  font-style: italic;
}

/* Page-level file changes preview */
.preview-files {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
  max-height: 400px;
  overflow: auto;
}

.file-change {
  background: var(--color-bg-tertiary);
  border-radius: var(--radius-sm);
  overflow: hidden;
}

.file-change-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-sm) var(--spacing-md);
  background: var(--color-bg-secondary);
  border-bottom: 1px solid var(--color-border-light);
}

.change-type {
  font-family: var(--font-mono, monospace);
  font-size: var(--text-xs);
  font-weight: var(--font-bold);
  padding: 1px var(--spacing-xs);
  border-radius: var(--radius-sm);
  text-transform: uppercase;
}

.change-A {
  color: #22c55e;
  background: rgba(34, 197, 94, 0.1);
}

.change-M {
  color: #eab308;
  background: rgba(234, 179, 8, 0.1);
}

.change-D {
  color: #ef4444;
  background: rgba(239, 68, 68, 0.1);
}

.change-R {
  color: #3b82f6;
  background: rgba(59, 130, 246, 0.1);
}

.file-path {
  font-size: var(--text-sm);
  color: var(--color-text-primary);
  font-family: var(--font-mono, monospace);
  word-break: break-all;
}

.file-diff {
  padding: var(--spacing-sm);
  max-height: 150px;
  overflow: auto;
}

.file-diff pre {
  margin: 0;
  font-size: var(--text-xs);
  font-family: var(--font-mono, monospace);
  white-space: pre-wrap;
  word-break: break-all;
}

.file-diff code {
  color: var(--color-text-secondary);
}
</style>
