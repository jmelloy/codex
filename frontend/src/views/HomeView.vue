<template>
  <div class="h-screen flex flex-col w-full">
    <nav class="bg-primary text-white px-8 py-4 flex justify-between items-center">
      <h1 class="text-2xl font-semibold m-0">Codex</h1>
      <div class="flex items-center gap-4">
        <button @click="goToSettings"
          class="bg-white/20 text-white border-none px-4 py-2 rounded cursor-pointer hover:bg-white/30 transition"
          title="User Settings">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none"
            stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="inline-block">
            <circle cx="12" cy="12" r="3"></circle>
            <path d="M12 1v6m0 6v6m9-9h-6m-6 0H3"></path>
          </svg>
          Settings
        </button>
        <span>{{ authStore.user?.username }}</span>
        <button @click="handleLogout"
          class="bg-white/20 text-white border-none px-4 py-2 rounded cursor-pointer hover:bg-white/30 transition">Logout</button>
      </div>
    </nav>

    <div class="flex flex-1 overflow-hidden">
      <!-- Left: File Browser Sidebar (280px) -->
      <aside class="w-[280px] min-w-[280px] notebook-sidebar flex flex-col overflow-hidden">
        <div class="flex justify-between items-center px-4 py-4" style="border-bottom: 1px solid var(--page-border)">
          <h2 class="m-0 text-sm font-semibold uppercase tracking-wide" style="color: var(--pen-gray)">Workspaces</h2>
          <button @click="showCreateWorkspace = true" title="Create Workspace"
            class="notebook-button text-white border-none w-6 h-6 rounded-full cursor-pointer text-base flex items-center justify-center transition">+</button>
        </div>
        <ul class="list-none p-0 m-0 max-h-[150px] overflow-y-auto">
          <li v-for="workspace in workspaceStore.workspaces" :key="workspace.id"
            :class="['workspace-item py-2.5 px-4 cursor-pointer text-sm transition', { 'workspace-active font-semibold': workspaceStore.currentWorkspace?.id === workspace.id }]"
            @click="selectWorkspace(workspace)">
            {{ workspace.name }}
          </li>
        </ul>

        <div v-if="workspaceStore.currentWorkspace" class="flex-1 flex flex-col overflow-hidden"
          style="border-top: 1px solid var(--page-border)">
          <div class="flex justify-between items-center px-4 py-4" style="border-bottom: 1px solid var(--page-border)">
            <h3 class="m-0 text-sm font-semibold uppercase tracking-wide" style="color: var(--pen-gray)">Notebooks</h3>
            <button @click="showCreateNotebook = true" title="Create Notebook"
              class="notebook-button text-white border-none w-6 h-6 rounded-full cursor-pointer text-base flex items-center justify-center transition">+</button>
          </div>

          <!-- Notebook Tree with Files -->
          <ul class="list-none p-0 m-0 overflow-y-auto flex-1">
            <li v-for="notebook in workspaceStore.notebooks" :key="notebook.id"
              style="border-bottom: 1px solid var(--page-border)">
              <div
                :class="['notebook-item flex items-center py-2 px-4 cursor-pointer text-sm transition', { 'notebook-active': workspaceStore.currentNotebook?.id === notebook.id }]"
                @click="toggleNotebook(notebook)">
                <span class="text-[10px] mr-2 w-3" style="color: var(--pen-gray)">{{
                  workspaceStore.expandedNotebooks.has(notebook.id) ? '▼' : '▶' }}</span>
                <span class="flex-1 font-medium">{{ notebook.name }}</span>
                <button v-if="workspaceStore.expandedNotebooks.has(notebook.id)" @click.stop="startCreateFile(notebook)"
                  class="notebook-button w-5 h-5 text-sm ml-auto opacity-0 hover:opacity-100 transition text-white border-none rounded-full cursor-pointer flex items-center justify-center"
                  title="New File">+</button>
              </div>

              <!-- File Tree -->
              <ul v-if="workspaceStore.expandedNotebooks.has(notebook.id)" class="list-none p-0 m-0">
                <template v-if="notebookFileTrees.get(notebook.id)?.length">
                  <template v-for="node in notebookFileTrees.get(notebook.id)" :key="node.path">
                    <!-- Render folder or file -->
                    <li v-if="node.type === 'folder'">
                      <!-- Folder -->
                      <div class="folder-item flex items-center py-2 px-4 pl-8 cursor-pointer text-[13px] transition"
                        @click="toggleFolder(notebook.id, node.path)">
                        <span class="text-[10px] mr-2 w-3" style="color: var(--pen-gray)">{{
                          isFolderExpanded(notebook.id, node.path) ? '▼' : '▶' }}</span>
                        <span class="mr-2 text-sm">📁</span>
                        <span class="overflow-hidden text-ellipsis whitespace-nowrap">{{ node.name }}</span>
                      </div>

                      <!-- Folder contents -->
                      <ul v-if="isFolderExpanded(notebook.id, node.path) && node.children" class="list-none p-0 m-0">
                        <FileTreeItem v-for="child in node.children" :key="child.path" :node="child"
                          :notebook-id="notebook.id" :depth="1" :expanded-folders="expandedFolders"
                          :current-file-id="workspaceStore.currentFile?.id" @toggle-folder="toggleFolder"
                          @select-file="selectFile" />
                      </ul>
                    </li>

                    <!-- Root level file -->
                    <li v-else>
                      <div
                        :class="['file-item flex items-center py-2 px-4 pl-8 cursor-pointer text-[13px] transition', { 'file-active font-medium': workspaceStore.currentFile?.id === node.file?.id }]"
                        @click="node.file && selectFile(node.file)">
                        <span class="mr-2 text-sm">📄</span>
                        <span class="overflow-hidden text-ellipsis whitespace-nowrap">{{ node.file?.title || node.name
                          }}</span>
                      </div>
                    </li>
                  </template>
                </template>
                <li v-else class="py-2 px-4 pl-8 text-xs italic" style="color: var(--pen-gray); opacity: 0.6">
                  No files yet
                </li>
              </ul>
            </li>
          </ul>
        </div>
      </aside>

      <!-- Center: Content Pane (flex: 1) -->
      <main class="flex-1 flex flex-col overflow-hidden">
        <!-- Loading State -->
        <div v-if="workspaceStore.fileLoading" class="flex flex-col items-center justify-center h-full text-gray-500">
          <span>Loading...</span>
        </div>

        <!-- Error State -->
        <div v-else-if="workspaceStore.error" class="flex flex-col items-center justify-center h-full text-red-600">
          <p>{{ workspaceStore.error }}</p>
          <button @click="workspaceStore.error = null"
            class="mt-4 px-4 py-2 bg-red-600 text-white border-none rounded cursor-pointer">Dismiss</button>
        </div>

        <!-- Editor Mode -->
        <div v-else-if="workspaceStore.isEditing && workspaceStore.currentFile" class="flex-1 flex overflow-hidden p-4">
          <MarkdownEditor v-model="editContent" :frontmatter="workspaceStore.currentFile.properties" :autosave="false"
            @save="handleSaveFile" @cancel="handleCancelEdit" class="flex-1" />
        </div>

        <!-- Viewer Mode -->
        <div v-else-if="workspaceStore.currentFile" class="flex-1 flex overflow-hidden p-4">
          <!-- Dynamic View Renderer for .cdx files -->
          <ViewRenderer v-if="workspaceStore.currentFile.file_type === 'view'" :file-id="workspaceStore.currentFile.id"
            :workspace-id="workspaceStore.currentWorkspace!.id" :notebook-id="workspaceStore.currentFile.notebook_id" class="flex-1" />

          <!-- Markdown Viewer for regular files -->
          <MarkdownViewer v-else :content="workspaceStore.currentFile.content"
            :frontmatter="workspaceStore.currentFile.properties" :show-frontmatter="showFrontmatter" @edit="startEdit"
            @copy="handleCopy" class="flex-1">
            <template #toolbar-actions>
              <button @click="toggleFrontmatter"
                class="notebook-button-secondary px-4 py-2 rounded cursor-pointer text-sm transition">
                {{ showFrontmatter ? 'Hide' : 'Show' }} Metadata
              </button>
              <button @click="toggleProperties"
                class="notebook-button-secondary px-4 py-2 rounded cursor-pointer text-sm transition">
                Properties
              </button>
            </template>
          </MarkdownViewer>
        </div>

        <!-- Welcome State -->
        <div v-else class="flex flex-col items-center justify-center h-full text-center" style="color: var(--pen-gray)">
          <h2 class="mb-2" style="color: var(--notebook-text)">Welcome to Codex</h2>
          <p v-if="!workspaceStore.currentWorkspace">Select a workspace to get started</p>
          <p v-else-if="workspaceStore.notebooks.length === 0">Create a notebook to start adding files</p>
          <p v-else>Select a notebook and file to view its content</p>
        </div>
      </main>

      <!-- Right: Properties Panel (300px, collapsible) -->
      <FilePropertiesPanel v-if="showPropertiesPanel && workspaceStore.currentFile" :file="workspaceStore.currentFile"
        class="w-[300px] min-w-[300px]" @close="showPropertiesPanel = false" @update-properties="handleUpdateProperties"
        @delete="handleDeleteFile" />
    </div>

    <!-- Create Workspace Modal -->
    <Modal v-model="showCreateWorkspace" title="Create Workspace" confirm-text="Create" hide-actions>
      <form @submit.prevent="handleCreateWorkspace">
        <FormGroup label="Name" v-slot="{ inputId }">
          <input :id="inputId" v-model="newWorkspaceName" required />
        </FormGroup>
        <div class="flex gap-2 justify-end mt-6">
          <button type="button" @click="showCreateWorkspace = false"
            class="notebook-button-secondary px-4 py-2 border-none rounded cursor-pointer">Cancel</button>
          <button type="submit"
            class="notebook-button px-4 py-2 text-white border-none rounded cursor-pointer transition">Create</button>
        </div>
      </form>
    </Modal>

    <!-- Create Notebook Modal -->
    <Modal v-model="showCreateNotebook" title="Create Notebook" confirm-text="Create" hide-actions>
      <form @submit.prevent="handleCreateNotebook">
        <FormGroup label="Name" v-slot="{ inputId }">
          <input :id="inputId" v-model="newNotebookName" required />
        </FormGroup>
        <div class="flex gap-2 justify-end mt-6">
          <button type="button" @click="showCreateNotebook = false"
            class="notebook-button-secondary px-4 py-2 border-none rounded cursor-pointer">Cancel</button>
          <button type="submit"
            class="notebook-button px-4 py-2 text-white border-none rounded cursor-pointer transition">Create</button>
        </div>
      </form>
    </Modal>

    <!-- Create File Modal -->
    <Modal v-model="showCreateFile" title="Create File" confirm-text="Create" hide-actions>
      <form @submit.prevent="handleCreateFile">
        <FormGroup label="Filename" v-slot="{ inputId }">
          <input :id="inputId" v-model="newFileName" placeholder="example.md" required />
        </FormGroup>
        <div class="flex gap-2 justify-end mt-6">
          <button type="button" @click="showCreateFile = false"
            class="notebook-button-secondary px-4 py-2 border-none rounded cursor-pointer">Cancel</button>
          <button type="submit"
            class="notebook-button px-4 py-2 text-white border-none rounded cursor-pointer transition">Create</button>
        </div>
      </form>
    </Modal>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useWorkspaceStore } from '../stores/workspace'
import type { Workspace, Notebook, FileMetadata } from '../services/codex'
import Modal from '../components/Modal.vue'
import FormGroup from '../components/FormGroup.vue'
import MarkdownViewer from '../components/MarkdownViewer.vue'
import MarkdownEditor from '../components/MarkdownEditor.vue'
import ViewRenderer from '../components/views/ViewRenderer.vue'
import FilePropertiesPanel from '../components/FilePropertiesPanel.vue'
import FileTreeItem from '../components/FileTreeItem.vue'
import { showToast } from '../utils/toast'
import { buildFileTree, type FileTreeNode } from '../utils/fileTree'

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

// Folder expansion state - tracks which folder paths are expanded
const expandedFolders = ref<Map<number, Set<string>>>(new Map())

// Build file trees for each notebook
const notebookFileTrees = computed(() => {
  const trees = new Map<number, FileTreeNode[]>()
  workspaceStore.notebooks.forEach(notebook => {
    const files = workspaceStore.getFilesForNotebook(notebook.id)
    trees.set(notebook.id, buildFileTree(files))
  })
  return trees
})

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

function goToSettings() {
  router.push('/settings')
}

function selectWorkspace(workspace: Workspace) {
  workspaceStore.setCurrentWorkspace(workspace)
  showPropertiesPanel.value = false
}

function toggleNotebook(notebook: Notebook) {
  workspaceStore.toggleNotebookExpansion(notebook)
}

function toggleFolder(notebookId: number, folderPath: string) {
  if (!expandedFolders.value.has(notebookId)) {
    expandedFolders.value.set(notebookId, new Set())
  }
  const folders = expandedFolders.value.get(notebookId)!
  if (folders.has(folderPath)) {
    folders.delete(folderPath)
  } else {
    folders.add(folderPath)
  }
}

function isFolderExpanded(notebookId: number, folderPath: string): boolean {
  return expandedFolders.value.get(notebookId)?.has(folderPath) || false
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

async function handleUpdateProperties(properties: Record<string, any>) {
  if (workspaceStore.currentFile) {
    try {
      await workspaceStore.saveFile(
        workspaceStore.currentFile.content,
        properties
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
/* Add hover effect for notebook header buttons */
.flex.items-center.py-2:hover button {
  opacity: 1;
}

/* Workspace items */
.workspace-item {
  color: var(--notebook-text);
  border-bottom: 1px solid var(--page-border);
}

.workspace-item:hover:not(.workspace-active) {
  background: color-mix(in srgb, var(--notebook-text) var(--hover-opacity), transparent);
}

.workspace-active {
  background: var(--notebook-accent);
  color: white;
  border-bottom: 1px solid color-mix(in srgb, var(--notebook-accent) 80%, black);
}

/* Notebook items */
.notebook-item {
  color: var(--notebook-text);
}

.notebook-item:hover:not(.notebook-active) {
  background: color-mix(in srgb, var(--notebook-text) var(--hover-opacity), transparent);
}

.notebook-active {
  background: color-mix(in srgb, var(--notebook-text) var(--active-opacity), transparent);
}

/* Folder items */
.folder-item {
  color: var(--pen-gray);
}

.folder-item:hover {
  background: color-mix(in srgb, var(--notebook-text) var(--subtle-hover-opacity), transparent);
}

/* File items */
.file-item {
  color: var(--pen-gray);
}

.file-item:hover:not(.file-active) {
  background: color-mix(in srgb, var(--notebook-text) var(--subtle-hover-opacity), transparent);
}

.file-active {
  background: color-mix(in srgb, var(--notebook-accent) var(--selected-opacity), transparent);
  color: var(--notebook-accent);
}
</style>
