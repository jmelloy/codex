<template>
  <div class="markdown-page">
    <nav class="navbar">
      <h1>Markdown Editor</h1>
      <div class="nav-actions">
        <router-link to="/" class="btn-back">← Back to Home</router-link>
      </div>
    </nav>

    <div class="main-content">
      <aside class="sidebar">
        <div class="sidebar-header">
          <h2>Documents</h2>
          <button @click="createNew" class="btn-new">+</button>
        </div>
        <div class="document-list">
          <div
            v-for="doc in documents"
            :key="doc.id"
            :class="['document-item', { active: currentDocument?.id === doc.id }]"
            @click="selectDocument(doc)"
          >
            <div class="doc-title">{{ doc.title || 'Untitled' }}</div>
            <div class="doc-meta">{{ formatDate(doc.updatedAt) }}</div>
          </div>
          <div v-if="documents.length === 0" class="empty-state">
            No documents yet. Create one to get started!
          </div>
        </div>
      </aside>

      <main class="content">
        <div v-if="isEditing && currentDocument" class="editor-container">
          <MarkdownEditor
            v-model="currentDocument.content"
            :frontmatter="currentDocument.frontmatter"
            :autosave="true"
            :autosave-delay="2000"
            :extensions="markdownExtensions"
            @save="saveDocument"
            @cancel="cancelEdit"
          >
            <template #toolbar-actions>
              <div class="custom-toolbar-actions">
                <button @click="toggleFrontmatterEditor" class="btn-metadata">
                  📋 Metadata
                </button>
              </div>
            </template>
          </MarkdownEditor>
        </div>

        <div v-else-if="currentDocument" class="viewer-container">
          <MarkdownViewer
            :content="currentDocument.content"
            :frontmatter="currentDocument.frontmatter"
            :show-frontmatter="showFrontmatter"
            :extensions="markdownExtensions"
            @edit="startEdit"
            @copy="handleCopy"
          >
            <template #toolbar-actions>
              <button @click="toggleFrontmatter" class="btn-metadata">
                {{ showFrontmatter ? 'Hide' : 'Show' }} Metadata
              </button>
              <button @click="deleteDocument" class="btn-delete">
                Delete
              </button>
            </template>
          </MarkdownViewer>
        </div>

        <div v-else class="welcome">
          <h2>Welcome to Markdown Editor</h2>
          <p>Select a document from the sidebar or create a new one to get started.</p>
          <button @click="createNew" class="btn-create-large">
            Create New Document
          </button>
        </div>
      </main>
    </div>

    <!-- Frontmatter Editor Modal -->
    <Modal
      v-model="showFrontmatterEditor"
      title="Edit Metadata"
      confirm-text="Save"
      hide-actions
    >
      <FormGroup label="Title">
        <input v-model="frontmatterEdit.title" />
      </FormGroup>
      <FormGroup label="Tags (comma-separated)">
        <input v-model="frontmatterEdit.tags" />
      </FormGroup>
      <FormGroup label="Author">
        <input v-model="frontmatterEdit.author" />
      </FormGroup>
      <div class="modal-actions">
        <button type="button" @click="showFrontmatterEditor = false">Cancel</button>
        <button type="button" @click="saveFrontmatter" class="btn-primary">Save</button>
      </div>
    </Modal>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import MarkdownEditor from '../components/MarkdownEditor.vue'
import MarkdownViewer, { type MarkdownExtension } from '../components/MarkdownViewer.vue'
import { formatRelativeDate } from '../utils/date'
import { showToast } from '../utils/toast'
import Modal from '../components/Modal.vue'
import FormGroup from '../components/FormGroup.vue'

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
  const stored = localStorage.getItem('markdown-documents')
  if (stored) {
    try {
      const parsed = JSON.parse(stored)
      documents.value = parsed.map((doc: any) => ({
        ...doc,
        createdAt: new Date(doc.createdAt),
        updatedAt: new Date(doc.updatedAt)
      }))
    } catch (e) {
      console.error('Failed to load documents:', e)
    }
  }
}

const saveDocuments = () => {
  localStorage.setItem('markdown-documents', JSON.stringify(documents.value))
}

const createNew = () => {
  const newDoc: Document = {
    id: Date.now().toString(),
    title: 'Untitled Document',
    content: '# New Document\n\nStart writing your markdown here...',
    frontmatter: {
      title: 'Untitled Document',
      created: new Date().toISOString(),
      tags: []
    },
    createdAt: new Date(),
    updatedAt: new Date()
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
    const lines = currentDocument.value.content.split('\n')
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
    documents.value = documents.value.filter(d => d.id !== currentDocument.value!.id)
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
      tags: currentDocument.value.frontmatter?.tags?.join(', ') || '',
      author: currentDocument.value.frontmatter?.author || ''
    }
    showFrontmatterEditor.value = true
  }
}

const saveFrontmatter = () => {
  if (currentDocument.value) {
    currentDocument.value.frontmatter = {
      ...currentDocument.value.frontmatter,
      title: frontmatterEdit.value.title,
      tags: frontmatterEdit.value.tags.split(',').map((t: string) => t.trim()).filter(Boolean),
      author: frontmatterEdit.value.author
    }
    currentDocument.value.title = frontmatterEdit.value.title
    saveDocuments()
    showFrontmatterEditor.value = false
  }
}

const handleCopy = () => {
  // Content is already copied by the viewer component
  showToast({ message: 'Content copied to clipboard!' })
}

const formatDate = formatRelativeDate

// Lifecycle
onMounted(() => {
  loadDocuments()
})
</script>

<style scoped>
.markdown-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: #f7fafc;
}

.navbar {
  background: #667eea;
  color: white;
  padding: 1rem 2rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.navbar h1 {
  margin: 0;
  font-size: 1.5rem;
}

.btn-back {
  color: white;
  text-decoration: none;
  padding: 0.5rem 1rem;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 4px;
  transition: background 0.2s;
}

.btn-back:hover {
  background: rgba(255, 255, 255, 0.3);
}

.main-content {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.sidebar {
  width: 280px;
  background: white;
  border-right: 1px solid #e2e8f0;
  display: flex;
  flex-direction: column;
}

.sidebar-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  border-bottom: 1px solid #e2e8f0;
}

.sidebar-header h2 {
  margin: 0;
  font-size: 1rem;
  color: #2d3748;
}

.btn-new {
  background: #667eea;
  color: white;
  border: none;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  cursor: pointer;
  font-size: 1.2rem;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.2s;
}

.btn-new:hover {
  background: #5a67d8;
}

.document-list {
  flex: 1;
  overflow-y: auto;
}

.document-item {
  padding: 0.75rem 1rem;
  cursor: pointer;
  border-bottom: 1px solid #f7fafc;
  transition: background 0.2s;
}

.document-item:hover {
  background: #f7fafc;
}

.document-item.active {
  background: #edf2f7;
  border-left: 3px solid #667eea;
}

.doc-title {
  font-weight: 500;
  color: #2d3748;
  margin-bottom: 0.25rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.doc-meta {
  font-size: 0.75rem;
  color: #a0aec0;
}

.empty-state {
  padding: 2rem 1rem;
  text-align: center;
  color: #a0aec0;
  font-size: 0.875rem;
}

.content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.editor-container,
.viewer-container {
  flex: 1;
  padding: 1rem;
  display: flex;
  overflow: hidden;
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
  padding: 2rem;
  text-align: center;
}

.welcome h2 {
  color: #2d3748;
  margin-bottom: 0.5rem;
}

.welcome p {
  color: #718096;
  margin-bottom: 2rem;
}

.btn-create-large {
  padding: 0.75rem 1.5rem;
  background: #667eea;
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 1rem;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-create-large:hover {
  background: #5a67d8;
}

.custom-toolbar-actions {
  display: flex;
  gap: 0.5rem;
}

.btn-metadata,
.btn-delete {
  padding: 0.5rem 1rem;
  border: 1px solid #cbd5e0;
  background: white;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.875rem;
  transition: all 0.2s;
}

.btn-metadata:hover {
  background: #edf2f7;
}

.btn-delete {
  color: #f56565;
  border-color: #f56565;
}

.btn-delete:hover {
  background: #f56565;
  color: white;
}

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
  font-size: 0.875rem;
  transition: all 0.2s;
}

.modal-actions button[type='button'] {
  background: #e2e8f0;
  color: #2d3748;
}

.modal-actions button[type='button']:hover {
  background: #cbd5e0;
}

.modal-actions .btn-primary {
  background: #667eea;
  color: white;
}

.modal-actions .btn-primary:hover {
  background: #5a67d8;
}
</style>
