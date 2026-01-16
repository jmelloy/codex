<template>
  <div class="h-screen flex flex-col w-full">
    <nav class="bg-primary text-white px-8 py-4 flex justify-between items-center">
      <h1 class="text-2xl font-semibold m-0">Codex</h1>
      <div class="flex items-center gap-4">
        <span>{{ authStore.user?.username }}</span>
        <button @click="handleLogout" class="bg-white/20 text-white border-none px-4 py-2 rounded cursor-pointer hover:bg-white/30 transition">Logout</button>
      </div>
    </nav>

    <div class="flex flex-1 overflow-hidden">
      <!-- Left: File Browser Sidebar (280px) -->
      <aside class="w-[280px] min-w-[280px] bg-gray-50 border-r border-gray-200 flex flex-col overflow-hidden">
        <div class="flex justify-between items-center px-4 py-4 border-b border-gray-200">
          <h2 class="m-0 text-sm font-semibold text-gray-600 uppercase tracking-wide">Workspaces</h2>
          <button @click="showCreateWorkspace = true" title="Create Workspace" class="bg-primary text-white border-none w-6 h-6 rounded-full cursor-pointer text-base flex items-center justify-center hover:bg-primary-hover transition">+</button>
        </div>
        <ul class="list-none p-0 m-0 max-h-[150px] overflow-y-auto">
          <li
            v-for="workspace in workspaceStore.workspaces"
            :key="workspace.id"
            :class="['py-2.5 px-4 cursor-pointer border-b border-gray-100 text-sm text-gray-700 hover:bg-gray-100 transition', { 'bg-primary text-white hover:bg-primary': workspaceStore.currentWorkspace?.id === workspace.id }]"
            @click="selectWorkspace(workspace)"
          >
            {{ workspace.name }}
          </li>
        </ul>

        <div v-if="workspaceStore.currentWorkspace" class="flex-1 flex flex-col overflow-hidden border-t border-gray-200">
          <div class="flex justify-between items-center px-4 py-4 border-b border-gray-200">
            <h3 class="m-0 text-sm font-semibold text-gray-600 uppercase tracking-wide">Notebooks</h3>
            <button @click="showCreateNotebook = true" title="Create Notebook" class="bg-primary text-white border-none w-6 h-6 rounded-full cursor-pointer text-base flex items-center justify-center hover:bg-primary-hover transition">+</button>
          </div>

          <!-- Notebook Tree with Files -->
          <ul class="list-none p-0 m-0 overflow-y-auto flex-1">
            <li v-for="notebook in workspaceStore.notebooks" :key="notebook.id" class="border-b border-gray-100">
              <div
                :class="['flex items-center py-2 px-4 cursor-pointer text-sm text-gray-700 transition hover:bg-gray-100', {
                  'bg-gray-200': workspaceStore.currentNotebook?.id === notebook.id
                }]"
                @click="toggleNotebook(notebook)"
              >
                <span class="text-[10px] mr-2 text-gray-500 w-3">{{ workspaceStore.expandedNotebooks.has(notebook.id) ? '▼' : '▶' }}</span>
                <span class="flex-1 font-medium">{{ notebook.name }}</span>
                <button
                  v-if="workspaceStore.expandedNotebooks.has(notebook.id)"
                  @click.stop="startCreateFile(notebook)"
                  class="w-5 h-5 text-sm ml-auto opacity-0 hover:opacity-100 transition bg-primary text-white border-none rounded-full cursor-pointer flex items-center justify-center"
                  title="New File"
                >+</button>
              </div>

              <!-- File List -->
              <ul v-if="workspaceStore.expandedNotebooks.has(notebook.id)" class="list-none p-0 m-0 bg-white">
                <li
                  v-for="file in workspaceStore.getFilesForNotebook(notebook.id)"
                  :key="file.id"
                  :class="['flex items-center py-2 px-4 pl-8 cursor-pointer text-[13px] text-gray-600 transition hover:bg-gray-50', { 'bg-gray-100 text-primary font-medium': workspaceStore.currentFile?.id === file.id }]"
                  @click="selectFile(file)"
                >
                  <span class="mr-2 text-sm">📄</span>
                  <span class="overflow-hidden text-ellipsis whitespace-nowrap">{{ file.title || file.filename }}</span>
                </li>
                <li v-if="workspaceStore.getFilesForNotebook(notebook.id).length === 0" class="py-2 px-4 pl-8 text-xs text-gray-400 italic">
                  No files yet
                </li>
              </ul>
            </li>
          </ul>
        </div>
      </aside>

      <!-- Center: Content Pane (flex: 1) -->
      <main class="flex-1 flex flex-col overflow-hidden bg-white">
        <!-- Loading State -->
        <div v-if="workspaceStore.fileLoading" class="flex flex-col items-center justify-center h-full text-gray-500">
          <span>Loading...</span>
        </div>

        <!-- Error State -->
        <div v-else-if="workspaceStore.error" class="flex flex-col items-center justify-center h-full text-red-600">
          <p>{{ workspaceStore.error }}</p>
          <button @click="workspaceStore.error = null" class="mt-4 px-4 py-2 bg-red-600 text-white border-none rounded cursor-pointer">Dismiss</button>
        </div>

        <!-- Editor Mode -->
        <div v-else-if="workspaceStore.isEditing && workspaceStore.currentFile" class="flex-1 flex overflow-hidden p-4">
          <MarkdownEditor
            v-model="editContent"
            :frontmatter="workspaceStore.currentFile.frontmatter"
            :autosave="false"
            @save="handleSaveFile"
            @cancel="handleCancelEdit"
            class="flex-1"
          />
        </div>

        <!-- Viewer Mode -->
        <div v-else-if="workspaceStore.currentFile" class="flex-1 flex overflow-hidden p-4">
          <MarkdownViewer
            :content="workspaceStore.currentFile.content"
            :frontmatter="workspaceStore.currentFile.frontmatter"
            :show-frontmatter="showFrontmatter"
            @edit="startEdit"
            @copy="handleCopy"
            class="flex-1"
          >
            <template #toolbar-actions>
              <button @click="toggleFrontmatter" class="px-4 py-2 border border-gray-300 bg-white rounded cursor-pointer text-sm transition hover:bg-gray-50">
                {{ showFrontmatter ? 'Hide' : 'Show' }} Metadata
              </button>
              <button @click="toggleProperties" class="px-4 py-2 border border-gray-300 bg-white rounded cursor-pointer text-sm transition hover:bg-gray-50">
                Properties
              </button>
            </template>
          </MarkdownViewer>
        </div>

        <!-- Welcome State -->
        <div v-else class="flex flex-col items-center justify-center h-full text-center text-gray-500">
          <h2 class="text-gray-700 mb-2">Welcome to Codex</h2>
          <p v-if="!workspaceStore.currentWorkspace">Select a workspace to get started</p>
          <p v-else-if="workspaceStore.notebooks.length === 0">Create a notebook to start adding files</p>
          <p v-else>Select a notebook and file to view its content</p>
        </div>
      </main>

      <!-- Right: Properties Panel (300px, collapsible) -->
      <FilePropertiesPanel
        v-if="showPropertiesPanel && workspaceStore.currentFile"
        :file="workspaceStore.currentFile"
        class="w-[300px] min-w-[300px]"
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
        <div class="flex gap-2 justify-end mt-6">
          <button type="button" @click="showCreateWorkspace = false" class="px-4 py-2 bg-gray-200 border-none rounded cursor-pointer">Cancel</button>
          <button type="submit" class="px-4 py-2 bg-primary text-white border-none rounded cursor-pointer hover:bg-primary-hover transition">Create</button>
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
        <div class="flex gap-2 justify-end mt-6">
          <button type="button" @click="showCreateNotebook = false" class="px-4 py-2 bg-gray-200 border-none rounded cursor-pointer">Cancel</button>
          <button type="submit" class="px-4 py-2 bg-primary text-white border-none rounded cursor-pointer hover:bg-primary-hover transition">Create</button>
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
        <div class="flex gap-2 justify-end mt-6">
          <button type="button" @click="showCreateFile = false" class="px-4 py-2 bg-gray-200 border-none rounded cursor-pointer">Cancel</button>
          <button type="submit" class="px-4 py-2 bg-primary text-white border-none rounded cursor-pointer hover:bg-primary-hover transition">Create</button>
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
/* Add hover effect for notebook header buttons */
.flex.items-center.py-2:hover button {
  opacity: 1;
}
</style>
