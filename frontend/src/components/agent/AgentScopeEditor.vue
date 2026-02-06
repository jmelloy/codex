<template>
  <div class="scope-editor">
    <h4 class="scope-title">Access Scope</h4>

    <!-- Capability Toggles -->
    <div class="capability-grid">
      <label class="capability-item">
        <input type="checkbox" v-model="localScope.can_read" @change="emitUpdate" />
        <span class="capability-label">Read</span>
        <span class="capability-desc">Read file contents</span>
      </label>
      <label class="capability-item">
        <input type="checkbox" v-model="localScope.can_write" @change="emitUpdate" />
        <span class="capability-label">Write</span>
        <span class="capability-desc">Modify existing files</span>
      </label>
      <label class="capability-item">
        <input type="checkbox" v-model="localScope.can_create" @change="emitUpdate" />
        <span class="capability-label">Create</span>
        <span class="capability-desc">Create new files</span>
      </label>
      <label class="capability-item">
        <input type="checkbox" v-model="localScope.can_delete" @change="emitUpdate" />
        <span class="capability-label">Delete</span>
        <span class="capability-desc">Delete files</span>
      </label>
    </div>

    <!-- Notebooks -->
    <div class="scope-section">
      <label class="scope-section-label">Notebooks</label>
      <div class="scope-tag-input">
        <label class="all-access-toggle">
          <input
            type="checkbox"
            :checked="notebooksAllAccess"
            @change="toggleAllNotebooks"
          />
          <span>All notebooks</span>
        </label>
        <div v-if="!notebooksAllAccess" class="tag-list">
          <span v-for="(nb, i) in localScope.notebooks" :key="i" class="tag-chip">
            {{ nb }}
            <button @click="removeNotebook(i)" class="tag-remove">&times;</button>
          </span>
          <input
            v-model="newNotebook"
            @keydown.enter.prevent="addNotebook"
            placeholder="Add notebook ID..."
            class="tag-input"
          />
        </div>
      </div>
    </div>

    <!-- Folders -->
    <div class="scope-section">
      <label class="scope-section-label">Folders</label>
      <div class="scope-tag-input">
        <label class="all-access-toggle">
          <input
            type="checkbox"
            :checked="foldersAllAccess"
            @change="toggleAllFolders"
          />
          <span>All folders</span>
        </label>
        <div v-if="!foldersAllAccess" class="tag-list">
          <span v-for="(folder, i) in localScope.folders" :key="i" class="tag-chip">
            {{ folder }}
            <button @click="removeFolder(i)" class="tag-remove">&times;</button>
          </span>
          <input
            v-model="newFolder"
            @keydown.enter.prevent="addFolder"
            placeholder="/path/pattern..."
            class="tag-input"
          />
        </div>
      </div>
    </div>

    <!-- File Types -->
    <div class="scope-section">
      <label class="scope-section-label">File Types</label>
      <div class="scope-tag-input">
        <label class="all-access-toggle">
          <input
            type="checkbox"
            :checked="fileTypesAllAccess"
            @change="toggleAllFileTypes"
          />
          <span>All file types</span>
        </label>
        <div v-if="!fileTypesAllAccess" class="tag-list">
          <span v-for="(ft, i) in localScope.fileTypes" :key="i" class="tag-chip">
            {{ ft }}
            <button @click="removeFileType(i)" class="tag-remove">&times;</button>
          </span>
          <input
            v-model="newFileType"
            @keydown.enter.prevent="addFileType"
            placeholder="*.md, *.py..."
            class="tag-input"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, watch, computed } from "vue"
import type { AgentScope } from "../../services/agent"

const props = defineProps<{
  scope: AgentScope
  canRead: boolean
  canWrite: boolean
  canCreate: boolean
  canDelete: boolean
}>()

const emit = defineEmits<{
  update: [value: {
    scope: AgentScope
    can_read: boolean
    can_write: boolean
    can_create: boolean
    can_delete: boolean
  }]
}>()

const localScope = reactive({
  notebooks: [...(props.scope.notebooks || ["*"])],
  folders: [...(props.scope.folders || ["*"])],
  fileTypes: [...(props.scope.file_types || ["*"])],
  can_read: props.canRead,
  can_write: props.canWrite,
  can_create: props.canCreate,
  can_delete: props.canDelete,
})

const newNotebook = ref("")
const newFolder = ref("")
const newFileType = ref("")

const notebooksAllAccess = computed(
  () => localScope.notebooks.length === 1 && localScope.notebooks[0] === "*"
)
const foldersAllAccess = computed(
  () => localScope.folders.length === 1 && localScope.folders[0] === "*"
)
const fileTypesAllAccess = computed(
  () => localScope.fileTypes.length === 1 && localScope.fileTypes[0] === "*"
)

watch(
  () => props,
  (newProps) => {
    localScope.notebooks = [...(newProps.scope.notebooks || ["*"])]
    localScope.folders = [...(newProps.scope.folders || ["*"])]
    localScope.fileTypes = [...(newProps.scope.file_types || ["*"])]
    localScope.can_read = newProps.canRead
    localScope.can_write = newProps.canWrite
    localScope.can_create = newProps.canCreate
    localScope.can_delete = newProps.canDelete
  },
  { deep: true }
)

function emitUpdate() {
  emit("update", {
    scope: {
      notebooks: [...localScope.notebooks],
      folders: [...localScope.folders],
      file_types: [...localScope.fileTypes],
    },
    can_read: localScope.can_read,
    can_write: localScope.can_write,
    can_create: localScope.can_create,
    can_delete: localScope.can_delete,
  })
}

function toggleAllNotebooks(e: Event) {
  const checked = (e.target as HTMLInputElement).checked
  localScope.notebooks = checked ? ["*"] : []
  emitUpdate()
}

function toggleAllFolders(e: Event) {
  const checked = (e.target as HTMLInputElement).checked
  localScope.folders = checked ? ["*"] : []
  emitUpdate()
}

function toggleAllFileTypes(e: Event) {
  const checked = (e.target as HTMLInputElement).checked
  localScope.fileTypes = checked ? ["*"] : []
  emitUpdate()
}

function addNotebook() {
  const val = newNotebook.value.trim()
  if (val && !localScope.notebooks.includes(val)) {
    localScope.notebooks = localScope.notebooks.filter((n) => n !== "*")
    localScope.notebooks.push(val)
    newNotebook.value = ""
    emitUpdate()
  }
}

function removeNotebook(i: number) {
  localScope.notebooks.splice(i, 1)
  if (localScope.notebooks.length === 0) localScope.notebooks = ["*"]
  emitUpdate()
}

function addFolder() {
  const val = newFolder.value.trim()
  if (val && !localScope.folders.includes(val)) {
    localScope.folders = localScope.folders.filter((f) => f !== "*")
    localScope.folders.push(val)
    newFolder.value = ""
    emitUpdate()
  }
}

function removeFolder(i: number) {
  localScope.folders.splice(i, 1)
  if (localScope.folders.length === 0) localScope.folders = ["*"]
  emitUpdate()
}

function addFileType() {
  const val = newFileType.value.trim()
  if (val && !localScope.fileTypes.includes(val)) {
    localScope.fileTypes = localScope.fileTypes.filter((ft) => ft !== "*")
    localScope.fileTypes.push(val)
    newFileType.value = ""
    emitUpdate()
  }
}

function removeFileType(i: number) {
  localScope.fileTypes.splice(i, 1)
  if (localScope.fileTypes.length === 0) localScope.fileTypes = ["*"]
  emitUpdate()
}
</script>

<style scoped>
.scope-editor {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.scope-title {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
  color: var(--color-text-primary);
}

.capability-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 0.75rem;
}

.capability-item {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  cursor: pointer;
  padding: 0.625rem;
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border-light);
  border-radius: 6px;
  transition: border-color 0.2s;
}

.capability-item:hover {
  border-color: var(--notebook-accent);
}

.capability-item input[type="checkbox"] {
  margin-top: 0.125rem;
  cursor: pointer;
}

.capability-label {
  font-weight: 600;
  font-size: 0.875rem;
  color: var(--color-text-primary);
}

.capability-desc {
  display: block;
  font-size: 0.75rem;
  color: var(--color-text-tertiary);
}

.scope-section {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.scope-section-label {
  font-weight: 500;
  font-size: 0.875rem;
  color: var(--color-text-primary);
}

.scope-tag-input {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.all-access-toggle {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
  color: var(--color-text-secondary);
  cursor: pointer;
}

.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 0.375rem;
  padding: 0.5rem;
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border-medium);
  border-radius: 6px;
  min-height: 2.5rem;
  align-items: center;
}

.tag-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.1875rem 0.5rem;
  background: var(--notebook-accent);
  color: white;
  border-radius: 3px;
  font-size: 0.8125rem;
  font-family: var(--font-mono);
}

.tag-remove {
  background: none;
  border: none;
  color: rgba(255, 255, 255, 0.7);
  cursor: pointer;
  padding: 0;
  font-size: 1rem;
  line-height: 1;
}

.tag-remove:hover {
  color: white;
}

.tag-input {
  flex: 1;
  min-width: 120px;
  border: none;
  background: transparent;
  font-size: 0.8125rem;
  color: var(--color-text-primary);
  outline: none;
  padding: 0.25rem;
  font-family: var(--font-mono);
}

.tag-input::placeholder {
  color: var(--color-text-tertiary);
}
</style>
