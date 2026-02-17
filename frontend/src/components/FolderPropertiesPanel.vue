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

      <!-- Display Settings -->
      <div class="property-section">
        <h4>Display Settings</h4>
        <div class="property-group">
          <label>View Mode</label>
          <select
            :value="folder.properties?.view_mode || 'grid'"
            @change="updateDisplaySetting('view_mode', ($event.target as HTMLSelectElement).value)"
            class="property-select"
          >
            <option value="grid">Grid</option>
            <option value="list">List</option>
            <option value="compact">Compact</option>
            <option value="rendered">Rendered</option>
          </select>
        </div>
        <div class="property-group">
          <label>Sort By</label>
          <select
            :value="folder.properties?.sort_by || 'name'"
            @change="updateDisplaySetting('sort_by', ($event.target as HTMLSelectElement).value)"
            class="property-select"
          >
            <option value="name">Name</option>
            <option value="date">Date Modified</option>
            <option value="type">Type</option>
            <option value="size">Size</option>
          </select>
        </div>
        <div class="property-group">
          <label>Sort Direction</label>
          <select
            :value="folder.properties?.sort_direction || 'asc'"
            @change="updateDisplaySetting('sort_direction', ($event.target as HTMLSelectElement).value)"
            class="property-select"
          >
            <option value="asc">Ascending</option>
            <option value="desc">Descending</option>
          </select>
        </div>
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

      <!-- Actions -->
      <div class="property-actions">
        <button @click="confirmDelete" class="btn-delete">Delete Folder</button>
      </div>
    </div>

    <div v-else class="empty-state">
      <p>No folder selected</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, watch } from "vue"
import type { FolderWithFiles } from "../services/codex"
import { useProperties } from "../composables/useProperties"
import { formatDate } from "../utils/date"
import TagsEditor from "./TagsEditor.vue"
import CustomPropertiesEditor from "./CustomPropertiesEditor.vue"

interface Props {
  folder: FolderWithFiles | null
}

const props = defineProps<Props>()

const emit = defineEmits<{
  close: []
  updateProperties: [properties: Record<string, any>]
  delete: []
}>()

// Use shared properties composable
const folderRef = computed(() => props.folder)
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
  emitPropertiesUpdate,
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
} = useProperties(folderRef, (event, properties) => emit(event, properties))

function updateDisplaySetting(key: string, value: string) {
  emitPropertiesUpdate({ [key]: value })
}

// Sync with prop changes
watch(() => props.folder, () => syncFromSource(), { immediate: true })

function confirmDelete() {
  const displayName = props.folder?.properties?.title || props.folder?.title || props.folder?.name
  if (confirm(`Are you sure you want to delete folder "${displayName}" and all its contents?`)) {
    emit("delete")
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

.property-select {
  width: 100%;
  padding: var(--spacing-sm);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-sm);
  font-size: var(--text-sm);
  color: var(--color-text-primary);
  background: var(--color-bg-primary);
  font-family: var(--font-sans);
  cursor: pointer;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.property-select:focus {
  outline: none;
  border-color: var(--color-border-focus);
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--color-primary) 20%, transparent);
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
</style>
