<template>
  <div class="min-h-screen flex flex-col notebook-texture w-full">
    <nav class="bg-primary text-white px-8 py-4 flex justify-between items-center shadow-md">
      <h1 class="m-0 text-2xl">Markdown Editor</h1>
      <div>
        <router-link
          to="/"
          class="text-white no-underline px-4 py-2 bg-bg-primary/20 rounded transition hover:bg-bg-primary/30"
          >← Back to Home</router-link
        >
      </div>
    </nav>

    <div class="flex flex-1 overflow-hidden">
      <aside class="w-[280px] notebook-sidebar flex flex-col">
        <div class="flex justify-between items-center px-4 py-4 border-b border-border-light">
          <h2 class="m-0 text-base text-text-primary">Documents</h2>
          <button
            @click="createNew"
            class="bg-primary text-white border-none w-7 h-7 rounded-full cursor-pointer text-lg flex items-center justify-center transition hover:bg-primary-hover"
          >
            +
          </button>
        </div>
        <div class="flex-1 overflow-y-auto">
          <div
            v-for="doc in documents"
            :key="doc.id"
            :class="[
              'py-3 px-4 cursor-pointer border-b border-bg-hover transition hover:bg-bg-hover',
              {
                'bg-bg-tertiary border-l-4 border-l-primary': currentDocument?.id === doc.id,
              },
            ]"
            @click="selectDocument(doc)"
          >
            <div
              class="font-medium text-text-primary mb-1 whitespace-nowrap overflow-hidden text-ellipsis"
            >
              {{ doc.title || "Untitled" }}
            </div>
            <div class="text-xs text-text-tertiary">
              {{ formatDate(doc.updatedAt) }}
            </div>
          </div>
          <div
            v-if="documents.length === 0"
            class="py-8 px-4 text-center text-text-tertiary text-sm"
          >
            No documents yet. Create one to get started!
          </div>
        </div>
      </aside>

      <main class="flex-1 flex flex-col overflow-hidden">
        <div v-if="isEditing && currentDocument" class="flex-1 p-8 flex overflow-hidden">
          <MarkdownEditor
            v-model="currentDocument.content"
            :frontmatter="currentDocument.frontmatter"
            :autosave="true"
            :autosave-delay="2000"
            :extensions="markdownExtensions"
            @save="saveDocument"
            @cancel="cancelEdit"
            class="flex-1"
          >
            <template #toolbar-actions>
              <div class="flex gap-2">
                <button
                  @click="toggleFrontmatterEditor"
                  class="px-4 py-2 border border-border-medium bg-bg-primary rounded cursor-pointer text-sm transition hover:bg-bg-hover"
                >
                  📋 Metadata
                </button>
              </div>
            </template>
          </MarkdownEditor>
        </div>

        <div
          v-else-if="currentDocument"
          class="flex-1 p-8 flex overflow-hidden max-w-5xl mx-auto w-full"
        >
          <MarkdownViewer
            :content="currentDocument.content"
            :frontmatter="currentDocument.frontmatter"
            :show-frontmatter="showFrontmatter"
            :extensions="markdownExtensions"
            @edit="startEdit"
            @copy="handleCopy"
            class="flex-1"
          >
            <template #toolbar-actions>
              <button
                @click="toggleFrontmatter"
                class="px-4 py-2 border border-border-medium bg-bg-primary rounded cursor-pointer text-sm transition hover:bg-bg-hover"
              >
                {{ showFrontmatter ? "Hide" : "Show" }} Metadata
              </button>
              <button
                @click="deleteDocument"
                class="px-4 py-2 text-red-600 border border-red-600 bg-bg-primary rounded cursor-pointer text-sm transition hover:bg-red-600 hover:text-white"
              >
                Delete
              </button>
            </template>
          </MarkdownViewer>
        </div>

        <div v-else class="flex flex-col items-center justify-center h-full py-8 text-center">
          <h2 class="text-text-primary mb-2">Welcome to Markdown Editor</h2>
          <p class="text-text-secondary mb-8">
            Select a document from the sidebar or create a new one to get started.
          </p>
          <button
            @click="createNew"
            class="px-6 py-3 bg-primary text-white border-none rounded-md text-base cursor-pointer transition hover:bg-primary-hover"
          >
            Create New Document
          </button>
        </div>
      </main>
    </div>

    <!-- Frontmatter Editor Modal -->
    <Modal v-model="showFrontmatterEditor" title="Edit Metadata" confirm-text="Save" hide-actions>
      <FormGroup label="Title" v-slot="{ inputId }">
        <input :id="inputId" v-model="frontmatterEdit.title" />
      </FormGroup>
      <FormGroup label="Tags (comma-separated)" v-slot="{ inputId }">
        <input :id="inputId" v-model="frontmatterEdit.tags" />
      </FormGroup>
      <FormGroup label="Author" v-slot="{ inputId }">
        <input :id="inputId" v-model="frontmatterEdit.author" />
      </FormGroup>
      <div class="flex gap-2 justify-end mt-6">
        <button
          type="button"
          @click="showFrontmatterEditor = false"
          class="px-4 py-2 bg-bg-disabled text-text-primary border-none rounded cursor-pointer text-sm transition hover:bg-border-medium"
        >
          Cancel
        </button>
        <button
          type="button"
          @click="saveFrontmatter"
          class="px-4 py-2 bg-primary text-white border-none rounded cursor-pointer text-sm transition hover:bg-primary-hover"
        >
          Save
        </button>
      </div>
    </Modal>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue"
import MarkdownEditor from "../components/MarkdownEditor.vue"
import MarkdownViewer, { type MarkdownExtension } from "../components/MarkdownViewer.vue"
import { formatRelativeDate } from "../utils/date"
import { showToast } from "../utils/toast"
import Modal from "../components/Modal.vue"
import FormGroup from "../components/FormGroup.vue"

// Types
interface Document {
  id: string
  title: string
  content: string
  frontmatter?: Record<string, any>
  createdAt: Date
  updatedAt: Date
}

// State
const documents = ref<Document[]>([])
const currentDocument = ref<Document | null>(null)
const isEditing = ref(false)
const showFrontmatter = ref(false)
const showFrontmatterEditor = ref(false)
const frontmatterEdit = ref<Record<string, any>>({})

// Example custom extension for demonstration
const markdownExtensions = ref<MarkdownExtension[]>([
  // Add custom extensions here
  // Example: Custom syntax for callouts, diagrams, etc.
])

// Methods
const loadDocuments = () => {
  // Load from localStorage for demo purposes
  const stored = localStorage.getItem("markdown-documents")
  if (stored) {
    try {
      const parsed = JSON.parse(stored)
      documents.value = parsed.map((doc: any) => ({
        ...doc,
        createdAt: new Date(doc.createdAt),
        updatedAt: new Date(doc.updatedAt),
      }))
    } catch (e) {
      console.error("Failed to load documents:", e)
    }
  }
}

const saveDocuments = () => {
  localStorage.setItem("markdown-documents", JSON.stringify(documents.value))
}

const createNew = () => {
  const newDoc: Document = {
    id: Date.now().toString(),
    title: "Untitled Document",
    content: "# New Document\n\nStart writing your markdown here...",
    frontmatter: {
      title: "Untitled Document",
      created: new Date().toISOString(),
      tags: [],
    },
    createdAt: new Date(),
    updatedAt: new Date(),
  }
  documents.value.unshift(newDoc)
  currentDocument.value = newDoc
  isEditing.value = true
  saveDocuments()
}

const selectDocument = (doc: Document) => {
  currentDocument.value = doc
  isEditing.value = false
}

const startEdit = () => {
  isEditing.value = true
}

const cancelEdit = () => {
  isEditing.value = false
}

const saveDocument = () => {
  if (!currentDocument.value) return

  currentDocument.value.updatedAt = new Date()

  // Extract title from content if not in frontmatter
  if (!currentDocument.value.frontmatter?.title) {
    const lines = currentDocument.value.content.split("\n")
    if (lines.length > 0 && lines[0]) {
      const firstLine = lines[0]
      const titleMatch = firstLine.match(/^#+ (.+)/)
      if (titleMatch && titleMatch[1]) {
        currentDocument.value.title = titleMatch[1]
      }
    }
  } else {
    currentDocument.value.title = currentDocument.value.frontmatter.title
  }

  saveDocuments()
}

const deleteDocument = () => {
  if (!currentDocument.value) return

  if (confirm(`Are you sure you want to delete "${currentDocument.value.title}"?`)) {
    documents.value = documents.value.filter((d) => d.id !== currentDocument.value!.id)
    currentDocument.value = null
    saveDocuments()
  }
}

const toggleFrontmatter = () => {
  showFrontmatter.value = !showFrontmatter.value
}

const toggleFrontmatterEditor = () => {
  if (currentDocument.value) {
    frontmatterEdit.value = {
      title: currentDocument.value.frontmatter?.title || currentDocument.value.title,
      tags: currentDocument.value.frontmatter?.tags?.join(", ") || "",
      author: currentDocument.value.frontmatter?.author || "",
    }
    showFrontmatterEditor.value = true
  }
}

const saveFrontmatter = () => {
  if (currentDocument.value) {
    currentDocument.value.frontmatter = {
      ...currentDocument.value.frontmatter,
      title: frontmatterEdit.value.title,
      tags: frontmatterEdit.value.tags
        .split(",")
        .map((t: string) => t.trim())
        .filter(Boolean),
      author: frontmatterEdit.value.author,
    }
    currentDocument.value.title = frontmatterEdit.value.title
    saveDocuments()
    showFrontmatterEditor.value = false
  }
}

const handleCopy = () => {
  // Content is already copied by the viewer component
  showToast({ message: "Content copied to clipboard!" })
}

const formatDate = formatRelativeDate

// Lifecycle
onMounted(() => {
  loadDocuments()
})
</script>

<style scoped>
/* Tailwind classes used, minimal custom styles needed */
</style>
