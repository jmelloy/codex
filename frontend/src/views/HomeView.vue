<template>
  <div class="h-screen flex flex-col w-full">
    <nav class="main-navbar">
      <h1 class="text-2xl font-semibold m-0">Codex</h1>
      <div class="flex items-center gap-4">
        <button @click="goToSettings"
          class="navbar-button"
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
          class="navbar-button">Logout</button>
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

              <!-- File Tree with drop zone -->
              <ul v-if="workspaceStore.expandedNotebooks.has(notebook.id)"
                class="list-none p-0 m-0"
                :class="{ 'bg-primary/10': dragOverNotebook === notebook.id }"
                @dragover.prevent="handleNotebookDragOver($event, notebook.id)"
                @dragenter.prevent="handleNotebookDragEnter(notebook.id)"
                @dragleave="handleNotebookDragLeave"
                @drop.prevent="handleNotebookDrop($event, notebook.id)">
                <template v-if="notebookFileTrees.get(notebook.id)?.length">
                  <template v-for="node in notebookFileTrees.get(notebook.id)" :key="node.path">
                    <!-- Render folder or file -->
                    <li v-if="node.type === 'folder'">
                      <!-- Folder -->
                      <div
                        :class="[
                          'folder-item flex items-center py-2 px-4 pl-8 cursor-pointer text-[13px] transition',
                          { 'bg-primary/20 border-t-2 border-primary': dragOverFolder === `${notebook.id}:${node.path}` }
                        ]"
                        @click="toggleFolder(notebook.id, node.path)"
                        @dragover.prevent="handleFolderDragOver($event, notebook.id, node.path)"
                        @dragenter.prevent="handleFolderDragEnter(notebook.id, node.path)"
                        @dragleave="handleFolderDragLeave"
                        @drop.prevent.stop="handleFolderDrop($event, notebook.id, node.path)">
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
                          @select-file="selectFile" @move-file="handleMoveFile" />
                      </ul>
                    </li>

                    <!-- Root level file -->
                    <li v-else>
                      <div
                        :class="['file-item flex items-center py-2 px-4 pl-8 cursor-grab text-[13px] transition', { 'file-active font-medium': workspaceStore.currentFile?.id === node.file?.id }]"
                        draggable="true"
                        @click="node.file && selectFile(node.file)"
                        @dragstart="handleFileDragStart($event, node.file!, notebook.id)">
                        <span class="mr-2 text-sm">{{ getFileIcon(node.file) }}</span>
                        <span class="overflow-hidden text-ellipsis whitespace-nowrap">{{ node.file?.title || node.name
                          }}</span>
                      </div>
                    </li>
                  </template>
                </template>
                <li v-else class="py-2 px-4 pl-8 text-xs italic" style="color: var(--pen-gray); opacity: 0.6">
                  {{ dragOverNotebook === notebook.id ? 'Drop files here to upload' : 'No files yet' }}
                </li>
              </ul>
            </li>
          </ul>
        </div>
      </aside>

      <!-- Center: Content Pane (flex: 1) -->
      <main class="flex-1 flex flex-col overflow-hidden">
        <!-- Loading State -->
        <div v-if="workspaceStore.fileLoading" class="flex flex-col items-center justify-center h-full text-text-tertiary">
          <span>Loading...</span>
        </div>

        <!-- Error State -->
        <div v-else-if="workspaceStore.error" class="flex flex-col items-center justify-center h-full text-error">
          <p>{{ workspaceStore.error }}</p>
          <button @click="workspaceStore.error = null"
            class="mt-4 px-4 py-2 bg-error text-text-inverse border-none rounded cursor-pointer font-medium">Dismiss</button>
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

          <!-- Image Viewer for image files -->
          <div v-else-if="workspaceStore.currentFile.file_type === 'image'" class="flex-1 flex flex-col overflow-hidden">
            <div class="flex justify-between items-center mb-4">
              <h2 class="text-xl font-semibold m-0">{{ workspaceStore.currentFile.title || workspaceStore.currentFile.filename }}</h2>
              <div class="flex gap-2">
                <button @click="openInNewTab"
                  class="notebook-button-secondary px-4 py-2 rounded cursor-pointer text-sm transition"
                  title="Open in new tab">
                  Open
                </button>
                <button @click="toggleProperties"
                  class="notebook-button-secondary px-4 py-2 rounded cursor-pointer text-sm transition">
                  Properties
                </button>
              </div>
            </div>
            <div class="flex-1 flex items-center justify-center overflow-auto bg-bg-secondary rounded-lg">
              <img
                :src="currentContentUrl"
                :alt="workspaceStore.currentFile.title || workspaceStore.currentFile.filename"
                class="max-w-full max-h-full object-contain"
              />
            </div>
          </div>

          <!-- PDF Viewer -->
          <div v-else-if="workspaceStore.currentFile.file_type === 'pdf'" class="flex-1 flex flex-col overflow-hidden">
            <div class="flex justify-between items-center mb-4">
              <h2 class="text-xl font-semibold m-0">{{ workspaceStore.currentFile.title || workspaceStore.currentFile.filename }}</h2>
              <div class="flex gap-2">
                <button @click="openInNewTab"
                  class="notebook-button-secondary px-4 py-2 rounded cursor-pointer text-sm transition"
                  title="Open in new tab">
                  Open
                </button>
                <button @click="toggleProperties"
                  class="notebook-button-secondary px-4 py-2 rounded cursor-pointer text-sm transition">
                  Properties
                </button>
              </div>
            </div>
            <div class="flex-1 overflow-hidden bg-bg-secondary rounded-lg">
              <iframe
                :src="currentContentUrl"
                class="w-full h-full border-0"
                :title="workspaceStore.currentFile.title || workspaceStore.currentFile.filename"
              />
            </div>
          </div>

          <!-- Audio Player -->
          <div v-else-if="workspaceStore.currentFile.file_type === 'audio'" class="flex-1 flex flex-col overflow-hidden">
            <div class="flex justify-between items-center mb-4">
              <h2 class="text-xl font-semibold m-0">{{ workspaceStore.currentFile.title || workspaceStore.currentFile.filename }}</h2>
              <div class="flex gap-2">
                <button @click="openInNewTab"
                  class="notebook-button-secondary px-4 py-2 rounded cursor-pointer text-sm transition"
                  title="Open in new tab">
                  Open
                </button>
                <button @click="toggleProperties"
                  class="notebook-button-secondary px-4 py-2 rounded cursor-pointer text-sm transition">
                  Properties
                </button>
              </div>
            </div>
            <div class="flex-1 flex items-center justify-center bg-bg-secondary rounded-lg">
              <div class="text-center">
                <div class="text-6xl mb-4">🎵</div>
                <audio
                  :src="currentContentUrl"
                  controls
                  class="w-full max-w-md"
                >
                  Your browser does not support the audio element.
                </audio>
              </div>
            </div>
          </div>

          <!-- Video Player -->
          <div v-else-if="workspaceStore.currentFile.file_type === 'video'" class="flex-1 flex flex-col overflow-hidden">
            <div class="flex justify-between items-center mb-4">
              <h2 class="text-xl font-semibold m-0">{{ workspaceStore.currentFile.title || workspaceStore.currentFile.filename }}</h2>
              <div class="flex gap-2">
                <button @click="openInNewTab"
                  class="notebook-button-secondary px-4 py-2 rounded cursor-pointer text-sm transition"
                  title="Open in new tab">
                  Open
                </button>
                <button @click="toggleProperties"
                  class="notebook-button-secondary px-4 py-2 rounded cursor-pointer text-sm transition">
                  Properties
                </button>
              </div>
            </div>
            <div class="flex-1 flex items-center justify-center overflow-auto bg-bg-secondary rounded-lg">
              <video
                :src="currentContentUrl"
                controls
                class="max-w-full max-h-full"
              >
                Your browser does not support the video element.
              </video>
            </div>
          </div>

          <!-- HTML Viewer -->
          <div v-else-if="workspaceStore.currentFile.file_type === 'html'" class="flex-1 flex flex-col overflow-hidden">
            <div class="flex justify-between items-center mb-4">
              <h2 class="text-xl font-semibold m-0">{{ workspaceStore.currentFile.title || workspaceStore.currentFile.filename }}</h2>
              <div class="flex gap-2">
                <button @click="openInNewTab"
                  class="notebook-button-secondary px-4 py-2 rounded cursor-pointer text-sm transition"
                  title="Open in new tab">
                  Open
                </button>
                <button @click="toggleProperties"
                  class="notebook-button-secondary px-4 py-2 rounded cursor-pointer text-sm transition">
                  Properties
                </button>
              </div>
            </div>
            <div class="flex-1 overflow-hidden bg-bg-secondary rounded-lg">
              <iframe
                :src="currentContentUrl"
                class="w-full h-full border-0"
                :title="workspaceStore.currentFile.title || workspaceStore.currentFile.filename"
                sandbox="allow-scripts allow-same-origin"
              />
            </div>
          </div>

          <!-- Code Viewer for source code files -->
          <CodeViewer v-else-if="workspaceStore.currentFile.file_type === 'code'"
            :content="workspaceStore.currentFile.content"
            :filename="workspaceStore.currentFile.filename"
            :show-line-numbers="true"
            class="flex-1">
            <template #toolbar-actions>
              <button @click="startEdit"
                class="notebook-button-secondary px-4 py-2 rounded cursor-pointer text-sm transition">
                Edit
              </button>
              <button @click="toggleProperties"
                class="notebook-button-secondary px-4 py-2 rounded cursor-pointer text-sm transition">
                Properties
              </button>
            </template>
          </CodeViewer>

          <!-- Binary file placeholder -->
          <div v-else-if="workspaceStore.currentFile.file_type === 'binary'" class="flex-1 flex flex-col overflow-hidden">
            <div class="flex justify-between items-center mb-4">
              <h2 class="text-xl font-semibold m-0">{{ workspaceStore.currentFile.title || workspaceStore.currentFile.filename }}</h2>
              <div class="flex gap-2">
                <a :href="currentContentUrl" download
                  class="notebook-button-secondary px-4 py-2 rounded cursor-pointer text-sm transition no-underline">
                  Download
                </a>
                <button @click="toggleProperties"
                  class="notebook-button-secondary px-4 py-2 rounded cursor-pointer text-sm transition">
                  Properties
                </button>
              </div>
            </div>
            <div class="flex-1 flex items-center justify-center bg-bg-secondary rounded-lg">
              <div class="text-center text-text-tertiary">
                <div class="text-6xl mb-4">📦</div>
                <p>This is a binary file.</p>
                <p class="text-sm">Click "Download" to save it to your device.</p>
              </div>
            </div>
          </div>

          <!-- Markdown Viewer for text-based files -->
          <MarkdownViewer v-else :content="workspaceStore.currentFile.content"
            :frontmatter="workspaceStore.currentFile.properties" 
            :workspace-id="workspaceStore.currentWorkspace?.id"
            :notebook-id="workspaceStore.currentNotebook?.id"
            :current-file-path="workspaceStore.currentFile.path"
            :show-frontmatter="false" @edit="startEdit"
            @copy="handleCopy" class="flex-1">
            <template #toolbar-actions>
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
        <!-- Template Selection -->
        <div v-if="createFileNotebook && workspaceStore.currentWorkspace" class="mb-4">
          <TemplateSelector
            :notebook-id="createFileNotebook.id"
            :workspace-id="workspaceStore.currentWorkspace.id"
            v-model="selectedTemplate"
            @select="handleTemplateSelect"
          />
        </div>

        <!-- Filename input -->
        <div class="border-t border-border-light pt-4 mt-4">
          <FormGroup v-if="selectedTemplate" label="Filename" v-slot="{ inputId }">
            <div class="flex items-center gap-2">
              <input
                :id="inputId"
                v-model="customTitle"
                :placeholder="getFilenamePlaceholder()"
                class="flex-1 px-3 py-2 border border-border-medium rounded-md bg-bg-primary text-text-primary"
              />
              <span class="text-text-secondary text-sm">{{ selectedTemplate.file_extension }}</span>
            </div>
            <p class="text-sm text-text-secondary mt-1">
              Will create: <code class="bg-bg-hover px-1 rounded">{{ getPreviewFilename() }}</code>
            </p>
          </FormGroup>

          <FormGroup v-else label="Filename" v-slot="{ inputId }">
            <input :id="inputId" v-model="newFileName" placeholder="example.md" required class="w-full px-3 py-2 border border-border-medium rounded-md bg-bg-primary text-text-primary" />
            <p class="text-sm text-text-secondary mt-1">Enter any filename with extension (e.g., notes.md, data.json, script.py)</p>
          </FormGroup>
        </div>

        <div class="flex gap-2 justify-end mt-6">
          <button type="button" @click="showCreateFile = false"
            class="notebook-button-secondary px-4 py-2 border-none rounded cursor-pointer">Cancel</button>
          <button v-if="!selectedTemplate && newFileName.endsWith('.cdx')" type="button" @click="switchToViewCreator"
            class="notebook-button px-4 py-2 text-white border-none rounded cursor-pointer transition">Configure View →</button>
          <button v-else type="submit"
            class="notebook-button px-4 py-2 text-white border-none rounded cursor-pointer transition">Create</button>
        </div>
      </form>
    </Modal>

    <!-- Create View Modal -->
    <CreateViewModal v-model="showCreateView" @create="handleCreateView" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useWorkspaceStore } from '../stores/workspace'
import type { Workspace, Notebook, FileMetadata, Template } from '../services/codex'
import { templateService } from '../services/codex'
import Modal from '../components/Modal.vue'
import FormGroup from '../components/FormGroup.vue'
import MarkdownViewer from '../components/MarkdownViewer.vue'
import MarkdownEditor from '../components/MarkdownEditor.vue'
import CodeViewer from '../components/CodeViewer.vue'
import ViewRenderer from '../components/views/ViewRenderer.vue'
import FilePropertiesPanel from '../components/FilePropertiesPanel.vue'
import FileTreeItem from '../components/FileTreeItem.vue'
import CreateViewModal from '../components/CreateViewModal.vue'
import TemplateSelector from '../components/TemplateSelector.vue'
import { showToast } from '../utils/toast'
import { buildFileTree, type FileTreeNode } from '../utils/fileTree'

const router = useRouter()
const authStore = useAuthStore()
const workspaceStore = useWorkspaceStore()

// Modal state
const showCreateWorkspace = ref(false)
const showCreateNotebook = ref(false)
const showCreateFile = ref(false)
const showCreateView = ref(false)

// Form state
const newWorkspaceName = ref('')
const newNotebookName = ref('')
const newFileName = ref('')
const createFileNotebook = ref<Notebook | null>(null)
const selectedTemplate = ref<Template | null>(null)
const customTitle = ref('')

// View state
const showPropertiesPanel = ref(false)
const editContent = ref('')

// Folder expansion state - tracks which folder paths are expanded
const expandedFolders = ref<Map<number, Set<string>>>(new Map())

// Drag-drop state
const dragOverNotebook = ref<number | null>(null)
const dragOverFolder = ref<string | null>(null)

// Build file trees for each notebook
const notebookFileTrees = computed(() => {
  const trees = new Map<number, FileTreeNode[]>()
  workspaceStore.notebooks.forEach(notebook => {
    const files = workspaceStore.getFilesForNotebook(notebook.id)
    trees.set(notebook.id, buildFileTree(files))
  })
  return trees
})

// Get content URL for current file (for binary files like images, PDFs, audio, video)
const currentContentUrl = computed(() => {
  if (!workspaceStore.currentFile || !workspaceStore.currentWorkspace) return ''
  return `/api/v1/files/${workspaceStore.currentFile.id}/content?workspace_id=${workspaceStore.currentWorkspace.id}&notebook_id=${workspaceStore.currentFile.notebook_id}`
})

// Open file in a new tab
function openInNewTab() {
  if (currentContentUrl.value) {
    window.open(currentContentUrl.value, '_blank')
  }
}

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

function getFileIcon(file: FileMetadata | undefined): string {
  if (!file) return '📄'

  switch (file.file_type) {
    case 'view':
      return '📊' // Chart/view icon for .cdx files
    case 'markdown':
      return '📝' // Memo for markdown
    case 'json':
      return '📋' // Clipboard for JSON
    case 'xml':
      return '🏷️'  // Tag for XML
    case 'code':
      return '💻' // Computer for code files
    case 'image':
      return '🖼️' // Picture for images
    case 'pdf':
      return '📕' // Book for PDF
    case 'audio':
      return '🎵' // Music note for audio
    case 'video':
      return '🎬' // Film for video
    case 'html':
      return '🌐' // Globe for HTML
    case 'text':
      return '📄' // Document for text
    case 'binary':
      return '📦' // Package for binary
    default:
      return '📄' // Default file icon
  }
}

function selectFile(file: FileMetadata) {
  workspaceStore.selectFile(file)
}

// Drag-drop handlers for files within the sidebar
function handleFileDragStart(event: DragEvent, file: FileMetadata, notebookId: number) {
  if (!event.dataTransfer) return
  event.dataTransfer.effectAllowed = 'move'
  event.dataTransfer.setData('application/x-codex-file', JSON.stringify({
    fileId: file.id,
    notebookId: notebookId,
    filename: file.filename,
    path: file.path
  }))
}

// Folder drag-over handlers
function handleFolderDragOver(event: DragEvent, _notebookId: number, _folderPath: string) {
  if (!event.dataTransfer) return
  const hasFile = event.dataTransfer.types.includes('application/x-codex-file')
  const hasExternalFile = event.dataTransfer.types.includes('Files')
  if (hasFile || hasExternalFile) {
    event.dataTransfer.dropEffect = 'move'
  }
}

function handleFolderDragEnter(notebookId: number, folderPath: string) {
  dragOverFolder.value = `${notebookId}:${folderPath}`
}

function handleFolderDragLeave() {
  dragOverFolder.value = null
}

async function handleFolderDrop(event: DragEvent, notebookId: number, folderPath: string) {
  dragOverFolder.value = null
  if (!event.dataTransfer) return

  // Handle external file drop (upload)
  if (event.dataTransfer.files.length > 0) {
    await handleFileUpload(event.dataTransfer.files, notebookId, folderPath)
    return
  }

  // Handle internal file move
  const data = event.dataTransfer.getData('application/x-codex-file')
  if (!data) return

  try {
    const { fileId, filename } = JSON.parse(data)
    const newPath = folderPath ? `${folderPath}/${filename}` : filename
    await handleMoveFile(fileId, newPath)
  } catch (e) {
    console.error('Failed to parse drag data:', e)
  }
}

// Notebook-level drag handlers (for root-level drops)
function handleNotebookDragOver(event: DragEvent, _notebookId: number) {
  if (!event.dataTransfer) return
  const hasFile = event.dataTransfer.types.includes('application/x-codex-file')
  const hasExternalFile = event.dataTransfer.types.includes('Files')
  if (hasFile || hasExternalFile) {
    event.dataTransfer.dropEffect = 'move'
  }
}

function handleNotebookDragEnter(notebookId: number) {
  dragOverNotebook.value = notebookId
}

function handleNotebookDragLeave() {
  dragOverNotebook.value = null
}

async function handleNotebookDrop(event: DragEvent, notebookId: number) {
  dragOverNotebook.value = null
  if (!event.dataTransfer) return

  // Handle external file drop (upload)
  if (event.dataTransfer.files.length > 0) {
    await handleFileUpload(event.dataTransfer.files, notebookId, '')
    return
  }

  // Handle internal file move to root
  const data = event.dataTransfer.getData('application/x-codex-file')
  if (!data) return

  try {
    const { fileId, filename, path } = JSON.parse(data)
    // Only move if not already at root
    if (path !== filename) {
      await handleMoveFile(fileId, filename)
    }
  } catch (e) {
    console.error('Failed to parse drag data:', e)
  }
}

// Handle file upload from drag-drop
async function handleFileUpload(files: FileList, notebookId: number, folderPath: string) {
  for (const file of Array.from(files)) {
    try {
      const targetPath = folderPath ? `${folderPath}/${file.name}` : file.name
      await workspaceStore.uploadFile(notebookId, file, targetPath)
      showToast({ message: `Uploaded ${file.name}` })
    } catch (e) {
      console.error(`Failed to upload ${file.name}:`, e)
      showToast({ message: `Failed to upload ${file.name}`, type: 'error' })
    }
  }
}

// Handle moving a file to a new path
async function handleMoveFile(fileId: number, newPath: string) {
  const file = findFileById(fileId)
  if (!file) return

  try {
    await workspaceStore.moveFile(fileId, file.notebook_id, newPath)
    showToast({ message: 'File moved successfully' })
  } catch (e) {
    console.error('Failed to move file:', e)
    showToast({ message: 'Failed to move file', type: 'error' })
  }
}

// Helper to find a file by ID across all notebooks
function findFileById(fileId: number): FileMetadata | undefined {
  for (const files of workspaceStore.files.values()) {
    const file = files.find(f => f.id === fileId)
    if (file) return file
  }
  return undefined
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
  if (!createFileNotebook.value || !workspaceStore.currentWorkspace) return

  try {
    // If a template is selected, use the template service
    if (selectedTemplate.value) {
      const filename = customTitle.value
        ? customTitle.value + selectedTemplate.value.file_extension
        : undefined

      const newFile = await templateService.createFromTemplate(
        createFileNotebook.value.id,
        workspaceStore.currentWorkspace.id,
        selectedTemplate.value.id,
        filename
      )

      // Refresh file list and select the new file
      await workspaceStore.fetchFiles(createFileNotebook.value.id)
      await workspaceStore.selectFile(newFile)

      showCreateFile.value = false
      newFileName.value = ''
      customTitle.value = ''
      selectedTemplate.value = null
      createFileNotebook.value = null
      showToast({ message: 'File created from template!' })
      return
    }

    // Otherwise, create a blank file with custom content
    const path = newFileName.value;
    const baseName = path.replace(/\.[^/.]+$/, '') || path;

    // Generate default content based on file extension
    let content: string;
    if (path.endsWith('.cdx')) {
      // Create basic view template
      content = `---
type: view
view_type: kanban
title: ${baseName}
description: Dynamic view
query:
  tags: []
config: {}
---

# ${baseName}

Edit the frontmatter above to configure this view.
`;
    } else if (path.endsWith('.md')) {
      content = `# ${baseName}\n\nStart writing here...`;
    } else if (path.endsWith('.json')) {
      content = '{\n  \n}';
    } else {
      // Default: empty file for other types
      content = '';
    }

    await workspaceStore.createFile(
      createFileNotebook.value.id,
      path,
      content
    )
    showCreateFile.value = false
    newFileName.value = ''
    customTitle.value = ''
    selectedTemplate.value = null
    createFileNotebook.value = null
  } catch {
    // Error handled in store
  }
}

function switchToViewCreator() {
  showCreateFile.value = false
  showCreateView.value = true
}

async function handleCreateView(data: { filename: string; content: string }) {
  if (!createFileNotebook.value) return

  try {
    await workspaceStore.createFile(
      createFileNotebook.value.id,
      data.filename,
      data.content
    )
    showCreateView.value = false
    createFileNotebook.value = null
    showToast({ message: 'View created successfully!' })
  } catch {
    // Error handled in store
  }
}

function startCreateFile(notebook: Notebook) {
  createFileNotebook.value = notebook
  newFileName.value = ''
  selectedTemplate.value = null
  customTitle.value = ''
  showCreateFile.value = true
}

function handleTemplateSelect(template: Template | null) {
  selectedTemplate.value = template
  if (template) {
    // Clear custom filename when a template is selected
    customTitle.value = ''
  }
}

function getFilenamePlaceholder(): string {
  if (!selectedTemplate.value) return 'filename'
  // Extract placeholder from default_name pattern
  const pattern = selectedTemplate.value.default_name
  if (pattern.includes('{title}')) {
    return 'Enter title (optional)'
  }
  // For date-based patterns, show what the filename will be
  return templateService.expandPattern(pattern).replace(selectedTemplate.value.file_extension, '')
}

function getPreviewFilename(): string {
  if (!selectedTemplate.value) return newFileName.value || 'filename.md'

  const pattern = selectedTemplate.value.default_name
  const title = customTitle.value || 'untitled'

  return templateService.expandPattern(pattern, title)
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

/* Main navbar - uses text-inverse to ensure readability on primary background */
.main-navbar {
  background-color: var(--color-primary);
  color: var(--color-text-inverse);
  padding: 1rem 2rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.main-navbar h1,
.main-navbar span,
.main-navbar button {
  color: var(--color-text-inverse);
}

.navbar-button {
  background-color: rgba(255, 255, 255, 0.2);
  color: var(--color-text-inverse);
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 0.25rem;
  cursor: pointer;
  transition: background-color 0.2s;
}

.navbar-button:hover {
  background-color: rgba(255, 255, 255, 0.3);
}
</style>
