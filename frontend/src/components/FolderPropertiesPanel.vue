<template>
  <div class="properties-panel">
    <div class="panel-header">
      <h3>Folder Properties</h3>
      <button @click="$emit('close')" class="btn-close" title="Close">×</button>
    </div>

    <div v-if="folder" class="panel-content">
      <!-- Title (editable) -->
      <div class="property-group">
        <label>Title</label>
        <input
          v-model="editableTitle"
          @blur="updateTitle"
          @keyup.enter="updateTitle"
          class="property-input"
          :placeholder="folder.name"
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

      <!-- Folder Info (read-only) -->
      <div class="property-section">
        <h4>Folder Info</h4>
        <div class="property-row">
          <span class="property-label">Path</span>
          <span class="property-value">{{ folder.path }}</span>
        </div>
        <div class="property-row">
          <span class="property-label">Name</span>
          <span class="property-value">{{ folder.name }}</span>
        </div>
        <div class="property-row">
          <span class="property-label">Files</span>
          <span class="property-value">{{ folder.file_count }} items</span>
        </div>
      </div>

      <!-- Dates -->
      <div v-if="folder.created_at || folder.updated_at" class="property-section">
        <h4>Dates</h4>
        <div v-if="folder.created_at" class="property-row">
          <span class="property-label">Created</span>
          <span class="property-value">{{ formatDate(folder.created_at) }}</span>
        </div>
        <div v-if="folder.updated_at" class="property-row">
          <span class="property-label">Modified</span>
          <span class="property-value">{{ formatDate(folder.updated_at) }}</span>
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
              <button @click="savePropertyEdit(key as string)" class="btn-action btn-save" title="Save">✓</button>
              <button @click="cancelPropertyEdit" class="btn-action btn-cancel" title="Cancel">✕</button>
            </div>
          </template>
          <template v-else>
            <!-- Display mode -->
            <span class="property-label">{{ key }}</span>
            <span
              class="property-value editable"
              @click="startEditProperty(key as string, value)"
              title="Click to edit"
            >{{ formatMetadataValue(value) }}</span>
            <button @click="removeProperty(key as string)" class="btn-remove-property" title="Remove property">×</button>
          </template>
        </div>

        <!-- Empty state -->
        <div v-if="Object.keys(metadata).length === 0" class="empty-properties">
          No custom properties
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
          >+</button>
        </div>
      </div>

      <!-- Actions -->
      <div class="property-actions">
        <button @click="confirmDelete" class="btn-delete">
          Delete Folder
        </button>
      </div>
    </div>

    <div v-else class="empty-state">
      <p>No folder selected</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import type { FolderWithFiles } from '../services/codex'

interface Props {
  folder: FolderWithFiles | null
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

// Custom property editing state
const newPropertyKey = ref('')
const newPropertyValue = ref('')
const editingProperty = ref<string | null>(null)
const editPropertyValue = ref('')
const valueInputRef = ref<HTMLInputElement | null>(null)

// Get current properties or empty object
const currentProperties = computed(() => {
  return props.folder?.properties || {}
})

// Sync with prop changes
watch(
  () => props.folder,
  (newFolder) => {
    if (newFolder) {
      editableTitle.value = newFolder.properties?.title || newFolder.title || ''
      editableDescription.value = newFolder.properties?.description || newFolder.description || ''
    }
  },
  { immediate: true }
)

const tags = computed(() => {
  if (props.folder?.properties?.tags) {
    return Array.isArray(props.folder.properties.tags)
      ? props.folder.properties.tags
      : []
  }
  return []
})

// Standard property fields that are handled separately
const STANDARD_FIELDS = ['title', 'description', 'tags'] as const
type StandardField = typeof STANDARD_FIELDS[number]

// Get all metadata except standard fields (title, description, tags)
const metadata = computed(() => {
  if (!props.folder?.properties) return {}

  const result: Record<string, unknown> = {}
  for (const [key, value] of Object.entries(props.folder.properties)) {
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
  const currentTitle = props.folder?.properties?.title || props.folder?.title || ''
  if (props.folder && editableTitle.value !== currentTitle) {
    emitPropertiesUpdate({ title: editableTitle.value })
  }
}

function updateDescription() {
  const currentDescription = props.folder?.properties?.description || props.folder?.description || ''
  if (props.folder && editableDescription.value !== currentDescription) {
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
  newPropertyKey.value = ''
  newPropertyValue.value = ''
}

function focusValueInput() {
  valueInputRef.value?.focus()
}

function startEditProperty(key: string, value: unknown) {
  editingProperty.value = key
  // Format value for editing
  if (typeof value === 'object') {
    editPropertyValue.value = JSON.stringify(value)
  } else {
    editPropertyValue.value = String(value ?? '')
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
  editPropertyValue.value = ''
}

function cancelPropertyEdit() {
  editingProperty.value = null
  editPropertyValue.value = ''
}

function removeProperty(key: string) {
  // Create new properties object without the removed key
  const newProperties = { ...currentProperties.value }
  delete newProperties[key]
  emit('updateProperties', newProperties)
}

function confirmDelete() {
  const displayName = props.folder?.properties?.title || props.folder?.title || props.folder?.name
  if (confirm(`Are you sure you want to delete folder "${displayName}" and all its contents?`)) {
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
  transition: background 0.2s, color 0.2s;
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
</style>
