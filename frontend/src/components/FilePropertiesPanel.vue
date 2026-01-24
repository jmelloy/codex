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

// Get all metadata except standard fields (title, description, tags)
const metadata = computed(() => {
  if (!props.file?.properties) return {}
  
  const result: Record<string, unknown> = {}
  for (const [key, value] of Object.entries(props.file.properties)) {
    if (!STANDARD_FIELDS.includes(key as any)) {
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
  background: white;
  border-left: 1px solid #e2e8f0;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  border-bottom: 1px solid #e2e8f0;
  background: #f7fafc;
}

.panel-header h3 {
  margin: 0;
  font-size: 0.875rem;
  font-weight: 600;
  color: #2d3748;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.btn-close {
  background: none;
  border: none;
  font-size: 1.25rem;
  color: #718096;
  cursor: pointer;
  padding: 0.25rem;
  line-height: 1;
}

.btn-close:hover {
  color: #2d3748;
}

.panel-content {
  flex: 1;
  overflow-y: auto;
  padding: 1rem;
}

.property-group {
  margin-bottom: 1rem;
}

.property-group label {
  display: block;
  font-size: 0.75rem;
  font-weight: 600;
  color: #718096;
  text-transform: uppercase;
  margin-bottom: 0.5rem;
}

.property-input,
.property-textarea {
  width: 100%;
  padding: 0.5rem;
  border: 1px solid #e2e8f0;
  border-radius: 4px;
  font-size: 0.875rem;
  color: #2d3748;
}

.property-input:focus,
.property-textarea:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.2);
}

.property-textarea {
  resize: vertical;
  font-family: inherit;
}

.property-section {
  margin-bottom: 1.5rem;
}

.property-section h4 {
  margin: 0 0 0.75rem;
  font-size: 0.75rem;
  font-weight: 600;
  color: #718096;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.property-row {
  display: flex;
  justify-content: space-between;
  padding: 0.375rem 0;
  border-bottom: 1px solid #f7fafc;
}

.property-label {
  font-size: 0.8125rem;
  color: #718096;
}

.property-value {
  font-size: 0.8125rem;
  color: #2d3748;
  text-align: right;
  max-width: 60%;
  word-break: break-all;
}

.tags-list {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.tag {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.25rem 0.5rem;
  background: #edf2f7;
  color: #4a5568;
  border-radius: 4px;
  font-size: 0.75rem;
}

.tag-remove {
  background: none;
  border: none;
  color: #a0aec0;
  cursor: pointer;
  padding: 0;
  line-height: 1;
  font-size: 0.875rem;
}

.tag-remove:hover {
  color: #e53e3e;
}

.tag-input-wrapper {
  display: flex;
  gap: 0.5rem;
  margin-top: 0.5rem;
}

.tag-input {
  flex: 1;
  padding: 0.375rem 0.5rem;
  border: 1px solid #e2e8f0;
  border-radius: 4px;
  font-size: 0.8125rem;
}

.tag-input:focus {
  outline: none;
  border-color: #667eea;
}

.tag-add-btn {
  padding: 0.375rem 0.75rem;
  background: #667eea;
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 0.8125rem;
  cursor: pointer;
}

.tag-add-btn:hover:not(:disabled) {
  background: #5a67d8;
}

.tag-add-btn:disabled {
  background: #cbd5e0;
  cursor: not-allowed;
}

.property-actions {
  margin-top: auto;
  padding-top: 1rem;
  border-top: 1px solid #e2e8f0;
}

.btn-delete {
  width: 100%;
  padding: 0.625rem 1rem;
  background: white;
  color: #e53e3e;
  border: 1px solid #e53e3e;
  border-radius: 4px;
  font-size: 0.875rem;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-delete:hover {
  background: #e53e3e;
  color: white;
}

.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #a0aec0;
  font-size: 0.875rem;
}
</style>
