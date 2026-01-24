<template>
  <div class="properties-panel">
    <div class="panel-header">
      <h3>Properties</h3>
      <button @click="$emit('close')" class="btn-close" title="Close">×</button>
    </div>

    <div v-if="file" class="panel-content">
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
          <span class="property-value">{{ file.file_type }}</span>
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

      <!-- Metadata / Frontmatter -->
      <div class="property-section" v-if="metadata && Object.keys(metadata).length > 0">
        <h4>Metadata</h4>
        <div class="property-row" v-for="(value, key) in metadata" :key="key">
          <span class="property-label">{{ key }}</span>
          <span class="property-value">{{ formatMetadataValue(value) }}</span>
        </div>
      </div>

      <!-- Actions -->
      <div class="property-actions">
        <button @click="confirmDelete" class="btn-delete">
          Delete File
        </button>
      </div>
    </div>

    <div v-else class="empty-state">
      <p>No file selected</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import type { FileWithContent } from '../services/codex'

interface Props {
  file: FileWithContent | null
}

const props = defineProps<Props>()

const emit = defineEmits<{
  close: []
  updateProperties: [properties: Record<string, any>]
  delete: []
}>()

const editableTitle = ref('')
const editableDescription = ref('')
const newTag = ref('')

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
      editableTitle.value = newFile.properties?.title || newFile.title || ''
      editableDescription.value = newFile.properties?.description || newFile.description || ''
    }
  },
  { immediate: true }
)

const tags = computed(() => {
  if (props.file?.properties?.tags) {
    return Array.isArray(props.file.properties.tags)
      ? props.file.properties.tags
      : []
  }
  return []
})

// Standard property fields that are handled separately
const STANDARD_FIELDS = ['title', 'description', 'tags'] as const
type StandardField = typeof STANDARD_FIELDS[number]

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
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return dateStr
  }
}

function formatSize(bytes: number): string {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
}

function formatMetadataValue(value: unknown): string {
  if (value === null || value === undefined) return ''
  if (Array.isArray(value)) return value.join(', ')
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}

function emitPropertiesUpdate(updates: Record<string, any>) {
  const newProperties = {
    ...currentProperties.value,
    ...updates
  }
  emit('updateProperties', newProperties)
}

function updateTitle() {
  const currentTitle = props.file?.properties?.title || props.file?.title || ''
  if (props.file && editableTitle.value !== currentTitle) {
    emitPropertiesUpdate({ title: editableTitle.value })
  }
}

function updateDescription() {
  const currentDescription = props.file?.properties?.description || props.file?.description || ''
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
  newTag.value = ''
}

function removeTag(tagToRemove: string) {
  const currentTags = tags.value
  emitPropertiesUpdate({ tags: currentTags.filter(t => t !== tagToRemove) })
}

function confirmDelete() {
  const displayName = props.file?.properties?.title || props.file?.title || props.file?.filename
  if (confirm(`Are you sure you want to delete "${displayName}"?`)) {
    emit('delete')
  }
}
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
  padding: var(--spacing-lg);
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
  transition: border-color 0.2s, box-shadow 0.2s;
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
</style>
