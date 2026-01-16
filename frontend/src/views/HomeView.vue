<template>
  <div class="home">
    <nav class="navbar">
      <h1>Codex</h1>
      <div class="user-info">
        <span>{{ authStore.user?.username }}</span>
        <button @click="handleLogout">Logout</button>
      </div>
    </nav>

    <div class="main-content">
      <!-- Left: File Browser Sidebar (280px) -->
      <aside class="sidebar">
        <div class="sidebar-header">
          <h2>Workspaces</h2>
          <button @click="showCreateWorkspace = true" title="Create Workspace">+</button>
        </div>
        <ul class="workspace-list">
          <li
            v-for="workspace in workspaceStore.workspaces"
            :key="workspace.id"
            :class="{ active: workspaceStore.currentWorkspace?.id === workspace.id }"
            @click="selectWorkspace(workspace)"
          >
            {{ workspace.name }}
          </li>
        </ul>

        <div v-if="workspaceStore.currentWorkspace" class="notebooks-section">
          <div class="sidebar-header">
            <h3>Notebooks</h3>
            <button @click="showCreateNotebook = true" title="Create Notebook">+</button>
          </div>

          <!-- Notebook Tree with Files -->
          <ul class="notebook-tree">
            <li v-for="notebook in workspaceStore.notebooks" :key="notebook.id" class="notebook-item">
              <div
                class="notebook-header"
                :class="{
                  expanded: workspaceStore.expandedNotebooks.has(notebook.id),
                  selected: workspaceStore.currentNotebook?.id === notebook.id
                }"
                @click="toggleNotebook(notebook)"
              >
                <span class="expand-icon">{{ workspaceStore.expandedNotebooks.has(notebook.id) ? '▼' : '▶' }}</span>
                <span class="notebook-name">{{ notebook.name }}</span>
                <button
                  v-if="workspaceStore.expandedNotebooks.has(notebook.id)"
                  @click.stop="startCreateFile(notebook)"
                  class="btn-add-file"
                  title="New File"
                >+</button>
              </div>

              <!-- File List -->
              <ul v-if="workspaceStore.expandedNotebooks.has(notebook.id)" class="file-list">
                <li
                  v-for="file in workspaceStore.getFilesForNotebook(notebook.id)"
                  :key="file.id"
                  class="file-item"
                  :class="{ active: workspaceStore.currentFile?.id === file.id }"
                  @click="selectFile(file)"
                >
                  <span class="file-icon">📄</span>
                  <span class="file-name">{{ file.title || file.filename }}</span>
                </li>
                <li v-if="workspaceStore.getFilesForNotebook(notebook.id).length === 0" class="empty-files">
                  No files yet
                </li>
              </ul>
            </li>
          </ul>
        </div>
      </aside>

      <!-- Center: Content Pane (flex: 1) -->
      <main class="content">
        <!-- Loading State -->
        <div v-if="workspaceStore.fileLoading" class="loading-state">
          <span>Loading...</span>
        </div>

        <!-- Error State -->
        <div v-else-if="workspaceStore.error" class="error-state">
          <p>{{ workspaceStore.error }}</p>
          <button @click="workspaceStore.error = null">Dismiss</button>
        </div>

        <!-- Editor Mode -->
        <div v-else-if="workspaceStore.isEditing && workspaceStore.currentFile" class="editor-container">
          <MarkdownEditor
            v-model="editContent"
            :frontmatter="workspaceStore.currentFile.frontmatter"
            :autosave="false"
            @save="handleSaveFile"
            @cancel="handleCancelEdit"
          />
        </div>

        <!-- Viewer Mode -->
        <div v-else-if="workspaceStore.currentFile" class="viewer-container">
          <MarkdownViewer
            :content="workspaceStore.currentFile.content"
            :frontmatter="workspaceStore.currentFile.frontmatter"
            :show-frontmatter="showFrontmatter"
            @edit="startEdit"
            @copy="handleCopy"
          >
            <template #toolbar-actions>
              <button @click="toggleFrontmatter" class="btn-metadata">
                {{ showFrontmatter ? 'Hide' : 'Show' }} Metadata
              </button>
              <button @click="toggleProperties" class="btn-properties">
                Properties
              </button>
            </template>
          </MarkdownViewer>
        </div>

        <!-- Welcome State -->
        <div v-else class="welcome">
          <h2>Welcome to Codex</h2>
          <p v-if="!workspaceStore.currentWorkspace">Select a workspace to get started</p>
          <p v-else-if="workspaceStore.notebooks.length === 0">Create a notebook to start adding files</p>
          <p v-else>Select a notebook and file to view its content</p>
        </div>
      </main>

      <!-- Right: Properties Panel (300px, collapsible) -->
      <FilePropertiesPanel
        v-if="showPropertiesPanel && workspaceStore.currentFile"
        :file="workspaceStore.currentFile"
        class="properties-pane"
        @close="showPropertiesPanel = false"
        @update-title="handleUpdateTitle"
        @update-description="handleUpdateDescription"
        @delete="handleDeleteFile"
      />
    </div>

    <!-- Create Workspace Modal -->
    <Modal
      v-model="showCreateWorkspace"
      title="Create Workspace"
      confirm-text="Create"
      hide-actions
    >
      <form @submit.prevent="handleCreateWorkspace">
        <FormGroup label="Name" v-slot="{ inputId }">
          <input :id="inputId" v-model="newWorkspaceName" required />
        </FormGroup>
        <div class="modal-actions">
          <button type="button" @click="showCreateWorkspace = false">Cancel</button>
          <button type="submit">Create</button>
        </div>
      </form>
    </Modal>

    <!-- Create Notebook Modal -->
    <Modal
      v-model="showCreateNotebook"
      title="Create Notebook"
      confirm-text="Create"
      hide-actions
    >
      <form @submit.prevent="handleCreateNotebook">
        <FormGroup label="Name" v-slot="{ inputId }">
          <input :id="inputId" v-model="newNotebookName" required />
        </FormGroup>
        <div class="modal-actions">
          <button type="button" @click="showCreateNotebook = false">Cancel</button>
          <button type="submit">Create</button>
        </div>
      </form>
    </Modal>

    <!-- Create File Modal -->
    <Modal
      v-model="showCreateFile"
      title="Create File"
      confirm-text="Create"
      hide-actions
    >
      <form @submit.prevent="handleCreateFile">
        <FormGroup label="Filename" v-slot="{ inputId }">
          <input :id="inputId" v-model="newFileName" placeholder="example.md" required />
        </FormGroup>
        <div class="modal-actions">
          <button type="button" @click="showCreateFile = false">Cancel</button>
          <button type="submit">Create</button>
        </div>
      </form>
    </Modal>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useWorkspaceStore } from '../stores/workspace'
import type { Workspace, Notebook, FileMetadata } from '../services/codex'
import Modal from '../components/Modal.vue'
import FormGroup from '../components/FormGroup.vue'
import MarkdownViewer from '../components/MarkdownViewer.vue'
import MarkdownEditor from '../components/MarkdownEditor.vue'
import FilePropertiesPanel from '../components/FilePropertiesPanel.vue'
import { showToast } from '../utils/toast'

const router = useRouter()
const authStore = useAuthStore()
const workspaceStore = useWorkspaceStore()

// Modal state
const showCreateWorkspace = ref(false)
const showCreateNotebook = ref(false)
const showCreateFile = ref(false)

// Form state
const newWorkspaceName = ref('')
const newNotebookName = ref('')
const newFileName = ref('')
const createFileNotebook = ref<Notebook | null>(null)

// View state
const showFrontmatter = ref(false)
const showPropertiesPanel = ref(false)
const editContent = ref('')

// Sync edit content when file changes
watch(
  () => workspaceStore.currentFile,
  (file) => {
    if (file) {
      editContent.value = file.content
    }
  },
  { immediate: true }
)

onMounted(async () => {
  await workspaceStore.fetchWorkspaces()
})

function handleLogout() {
  authStore.logout()
  router.push('/login')
}

function selectWorkspace(workspace: Workspace) {
  workspaceStore.setCurrentWorkspace(workspace)
  showPropertiesPanel.value = false
}

function toggleNotebook(notebook: Notebook) {
  workspaceStore.toggleNotebookExpansion(notebook)
}

function selectFile(file: FileMetadata) {
  workspaceStore.selectFile(file)
}

function startEdit() {
  if (workspaceStore.currentFile) {
    editContent.value = workspaceStore.currentFile.content
    workspaceStore.setEditing(true)
  }
}

function handleCancelEdit() {
  workspaceStore.setEditing(false)
  if (workspaceStore.currentFile) {
    editContent.value = workspaceStore.currentFile.content
  }
}

async function handleSaveFile(content: string) {
  try {
    await workspaceStore.saveFile(content)
    showToast({ message: 'File saved successfully' })
  } catch {
    // Error handled in store
  }
}

function handleCopy() {
  showToast({ message: 'Content copied to clipboard!' })
}

function toggleFrontmatter() {
  showFrontmatter.value = !showFrontmatter.value
}

function toggleProperties() {
  showPropertiesPanel.value = !showPropertiesPanel.value
}

async function handleUpdateTitle(title: string) {
  if (workspaceStore.currentFile) {
    try {
      await workspaceStore.saveFile(
        workspaceStore.currentFile.content,
        title,
        workspaceStore.currentFile.description
      )
    } catch {
      // Error handled in store
    }
  }
}

async function handleUpdateDescription(description: string) {
  if (workspaceStore.currentFile) {
    try {
      await workspaceStore.saveFile(
        workspaceStore.currentFile.content,
        workspaceStore.currentFile.title,
        description
      )
    } catch {
      // Error handled in store
    }
  }
}

async function handleDeleteFile() {
  if (workspaceStore.currentFile) {
    try {
      await workspaceStore.deleteFile(workspaceStore.currentFile.id)
      showPropertiesPanel.value = false
      showToast({ message: 'File deleted' })
    } catch {
      // Error handled in store
    }
  }
}

function startCreateFile(notebook: Notebook) {
  createFileNotebook.value = notebook
  newFileName.value = ''
  showCreateFile.value = true
}

async function handleCreateWorkspace() {
  try {
    await workspaceStore.createWorkspace(newWorkspaceName.value)
    showCreateWorkspace.value = false
    newWorkspaceName.value = ''
  } catch {
    // Error handled in store
  }
}

async function handleCreateNotebook() {
  if (!workspaceStore.currentWorkspace) return

  try {
    await workspaceStore.createNotebook(
      workspaceStore.currentWorkspace.id,
      newNotebookName.value
    )
    showCreateNotebook.value = false
    newNotebookName.value = ''
  } catch {
    // Error handled in store
  }
}

async function handleCreateFile() {
  if (!createFileNotebook.value) return

  try {
    const path = newFileName.value.endsWith('.md')
      ? newFileName.value
      : `${newFileName.value}.md`
    await workspaceStore.createFile(
      createFileNotebook.value.id,
      path,
      `# ${newFileName.value.replace('.md', '')}\n\nStart writing here...`
    )
    showCreateFile.value = false
    newFileName.value = ''
    createFileNotebook.value = null
  } catch {
    // Error handled in store
  }
}
</script>

<style scoped>
.home {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.navbar {
  background: #667eea;
  color: white;
  padding: 1rem 2rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.navbar h1 {
  margin: 0;
  font-size: 1.5rem;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.user-info button {
  background: rgba(255, 255, 255, 0.2);
  color: white;
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 4px;
  cursor: pointer;
}

.main-content {
  display: flex;
  flex: 1;
  overflow: hidden;
}

/* Left Sidebar */
.sidebar {
  width: 280px;
  min-width: 280px;
  background: #f7fafc;
  border-right: 1px solid #e2e8f0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.sidebar-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  border-bottom: 1px solid #e2e8f0;
}

.sidebar-header h2,
.sidebar-header h3 {
  margin: 0;
  font-size: 0.875rem;
  font-weight: 600;
  color: #4a5568;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.sidebar-header button {
  background: #667eea;
  color: white;
  border: none;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  cursor: pointer;
  font-size: 1rem;
  display: flex;
  align-items: center;
  justify-content: center;
}

.sidebar-header button:hover {
  background: #5a67d8;
}

.workspace-list {
  list-style: none;
  padding: 0;
  margin: 0;
  max-height: 150px;
  overflow-y: auto;
}

.workspace-list li {
  padding: 0.625rem 1rem;
  cursor: pointer;
  border-bottom: 1px solid #edf2f7;
  font-size: 0.875rem;
  color: #2d3748;
}

.workspace-list li:hover {
  background: #edf2f7;
}

.workspace-list li.active {
  background: #667eea;
  color: white;
}

.notebooks-section {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border-top: 1px solid #e2e8f0;
}

/* Notebook Tree */
.notebook-tree {
  list-style: none;
  padding: 0;
  margin: 0;
  overflow-y: auto;
  flex: 1;
}

.notebook-item {
  border-bottom: 1px solid #edf2f7;
}

.notebook-header {
  display: flex;
  align-items: center;
  padding: 0.5rem 1rem;
  cursor: pointer;
  font-size: 0.875rem;
  color: #2d3748;
  transition: background 0.15s;
}

.notebook-header:hover {
  background: #edf2f7;
}

.notebook-header.selected {
  background: #e2e8f0;
}

.expand-icon {
  font-size: 0.625rem;
  margin-right: 0.5rem;
  color: #718096;
  width: 12px;
}

.notebook-name {
  flex: 1;
  font-weight: 500;
}

.btn-add-file {
  width: 20px;
  height: 20px;
  font-size: 0.875rem;
  margin-left: auto;
  opacity: 0;
  transition: opacity 0.15s;
}

.notebook-header:hover .btn-add-file {
  opacity: 1;
}

/* File List */
.file-list {
  list-style: none;
  padding: 0;
  margin: 0;
  background: #fff;
}

.file-item {
  display: flex;
  align-items: center;
  padding: 0.5rem 1rem 0.5rem 2rem;
  cursor: pointer;
  font-size: 0.8125rem;
  color: #4a5568;
  transition: background 0.15s;
}

.file-item:hover {
  background: #f7fafc;
}

.file-item.active {
  background: #edf2f7;
  color: #667eea;
  font-weight: 500;
}

.file-icon {
  margin-right: 0.5rem;
  font-size: 0.875rem;
}

.file-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.empty-files {
  padding: 0.5rem 1rem 0.5rem 2rem;
  font-size: 0.75rem;
  color: #a0aec0;
  font-style: italic;
}

/* Center Content Pane */
.content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: #fff;
}

.loading-state,
.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #718096;
}

.error-state {
  color: #e53e3e;
}

.error-state button {
  margin-top: 1rem;
  padding: 0.5rem 1rem;
  background: #e53e3e;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.editor-container,
.viewer-container {
  flex: 1;
  display: flex;
  overflow: hidden;
  padding: 1rem;
}

.editor-container > *,
.viewer-container > * {
  flex: 1;
}

.welcome {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  text-align: center;
  color: #718096;
}

.welcome h2 {
  color: #2d3748;
  margin-bottom: 0.5rem;
}

/* Right Properties Pane */
.properties-pane {
  width: 300px;
  min-width: 300px;
}

/* Toolbar buttons */
.btn-metadata,
.btn-properties {
  padding: 0.5rem 1rem;
  border: 1px solid #cbd5e0;
  background: white;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.875rem;
  transition: all 0.2s;
}

.btn-metadata:hover,
.btn-properties:hover {
  background: #edf2f7;
}

/* Modal Actions */
.modal-actions {
  display: flex;
  gap: 0.5rem;
  justify-content: flex-end;
  margin-top: 1.5rem;
}

.modal-actions button {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.modal-actions button[type='button'] {
  background: #e2e8f0;
}

.modal-actions button[type='submit'] {
  background: #667eea;
  color: white;
}
</style>
