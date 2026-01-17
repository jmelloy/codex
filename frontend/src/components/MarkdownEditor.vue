<template>
  <div class="markdown-editor notebook-page ruled-paper" :class="themeStore.theme.className">
    <div class="editor-toolbar">
      <div class="toolbar-group">
        <button @click="insertBold" title="Bold">
          <strong>B</strong>
        </button>
        <button @click="insertItalic" title="Italic">
          <em>I</em>
        </button>
        <button @click="insertCode" title="Code">
          &lt;/&gt;
        </button>
        <button @click="insertLink" title="Link">
          🔗
        </button>
        <button @click="insertImage" title="Image">
          🖼️
        </button>
      </div>
      <div class="toolbar-group">
        <button @click="insertHeading(1)" title="Heading 1">
          H1
        </button>
        <button @click="insertHeading(2)" title="Heading 2">
          H2
        </button>
        <button @click="insertHeading(3)" title="Heading 3">
          H3
        </button>
      </div>
      <div class="toolbar-group">
        <button @click="insertList('ul')" title="Bullet List">
          • List
        </button>
        <button @click="insertList('ol')" title="Numbered List">
          1. List
        </button>
        <button @click="insertQuote" title="Quote">
          "
        </button>
      </div>
      <div class="toolbar-group">
        <button @click="togglePreview" :class="{ active: showPreview }">
          {{ showPreview ? 'Edit' : 'Preview' }}
        </button>
      </div>
      <slot name="toolbar-actions"></slot>
    </div>

    <div class="editor-content" :class="{ 'split-view': showPreview && showEditor }">
      <div class="editor-pane" v-show="showEditor">
        <textarea
          ref="editorTextarea"
          v-model="localContent"
          @input="handleInput"
          @keydown="handleKeydown"
          :placeholder="placeholder"
          class="markdown-textarea"
          spellcheck="true"
        ></textarea>
      </div>
      <div class="preview-pane" v-show="showPreview">
        <MarkdownViewer
          :content="localContent"
          :frontmatter="frontmatter"
          :show-toolbar="false"
          :extensions="extensions"
        />
      </div>
    </div>

    <div class="editor-footer">
      <div class="editor-stats">
        <span>{{ characterCount }} characters</span>
        <span>{{ wordCount }} words</span>
        <span>{{ lineCount }} lines</span>
      </div>
      <div class="editor-actions">
        <button @click="handleCancel" class="btn-cancel">
          Cancel
        </button>
        <button @click="handleSave" class="btn-save">
          Save
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'
import MarkdownViewer, { type MarkdownExtension } from './MarkdownViewer.vue'
import { useThemeStore } from '../stores/theme'

const themeStore = useThemeStore()

// Props
interface Props {
  modelValue: string
  frontmatter?: Record<string, any>
  placeholder?: string
  autosave?: boolean
  autosaveDelay?: number
  extensions?: MarkdownExtension[]
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: '',
  placeholder: 'Start writing your markdown...',
  autosave: false,
  autosaveDelay: 1000,
  extensions: () => []
})

// Emits
const emit = defineEmits<{
  'update:modelValue': [value: string]
  save: [content: string]
  cancel: []
  change: [content: string]
}>()

// State
const localContent = ref(props.modelValue)
const editorTextarea = ref<HTMLTextAreaElement | null>(null)
const showPreview = ref(false)
const showEditor = ref(true)
const autosaveTimer = ref<number | null>(null)

// Computed
const characterCount = computed(() => localContent.value.length)
const wordCount = computed(() => {
  const text = localContent.value.trim()
  return text ? text.split(/\s+/).length : 0
})
const lineCount = computed(() => localContent.value.split('\n').length)

// Watch for external changes
watch(() => props.modelValue, (newValue) => {
  if (newValue !== localContent.value) {
    localContent.value = newValue
  }
})

// Watch for local changes
watch(localContent, (newValue) => {
  emit('update:modelValue', newValue)
  emit('change', newValue)
  
  // Handle autosave
  if (props.autosave) {
    if (autosaveTimer.value) {
      clearTimeout(autosaveTimer.value)
    }
    autosaveTimer.value = window.setTimeout(() => {
      emit('save', newValue)
    }, props.autosaveDelay)
  }
})

// Methods
const handleInput = () => {
  // Input is handled by v-model
}

const handleKeydown = (e: KeyboardEvent) => {
  // Tab key - insert spaces
  if (e.key === 'Tab') {
    e.preventDefault()
    insertAtCursor('  ')
  }
}

const insertAtCursor = (text: string, selectText: boolean = false) => {
  const textarea = editorTextarea.value
  if (!textarea) return

  const start = textarea.selectionStart
  const end = textarea.selectionEnd
  const before = localContent.value.substring(0, start)
  const after = localContent.value.substring(end)

  localContent.value = before + text + after

  nextTick(() => {
    if (selectText) {
      textarea.selectionStart = start
      textarea.selectionEnd = start + text.length
    } else {
      textarea.selectionStart = textarea.selectionEnd = start + text.length
    }
    textarea.focus()
  })
}

const wrapSelection = (before: string, after: string) => {
  const textarea = editorTextarea.value
  if (!textarea) return

  const start = textarea.selectionStart
  const end = textarea.selectionEnd
  const selectedText = localContent.value.substring(start, end)
  const replacement = before + (selectedText || 'text') + after

  const beforeText = localContent.value.substring(0, start)
  const afterText = localContent.value.substring(end)

  localContent.value = beforeText + replacement + afterText

  nextTick(() => {
    if (selectedText) {
      textarea.selectionStart = start + before.length
      textarea.selectionEnd = start + before.length + selectedText.length
    } else {
      textarea.selectionStart = textarea.selectionEnd = start + before.length
    }
    textarea.focus()
  })
}

const insertBold = () => wrapSelection('**', '**')
const insertItalic = () => wrapSelection('*', '*')
const insertCode = () => wrapSelection('`', '`')
const insertLink = () => wrapSelection('[', '](url)')
const insertImage = () => wrapSelection('![', '](url)')

const insertHeading = (level: number) => {
  const prefix = '#'.repeat(level) + ' '
  insertAtCursor(prefix)
}

const insertList = (type: 'ul' | 'ol') => {
  const prefix = type === 'ul' ? '- ' : '1. '
  insertAtCursor(prefix)
}

const insertQuote = () => {
  insertAtCursor('> ')
}

const togglePreview = () => {
  if (showPreview.value && showEditor.value) {
    // Currently split view, show preview only
    showEditor.value = false
  } else if (showPreview.value && !showEditor.value) {
    // Currently preview only, back to edit only
    showPreview.value = false
    showEditor.value = true
  } else {
    // Currently edit only, show split view
    showPreview.value = true
    showEditor.value = true
  }
}

const handleSave = () => {
  emit('save', localContent.value)
}

const handleCancel = () => {
  emit('cancel')
}

// Expose methods for parent components
defineExpose({
  insertAtCursor,
  wrapSelection,
  getContent: () => localContent.value
})
</script>

<style scoped>
.markdown-editor {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: white;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid #e2e8f0;
}

.editor-toolbar {
  display: flex;
  gap: 0.5rem;
  padding: 0.75rem;
  background: rgba(255, 255, 255, 0.5);
  border-bottom: 1px solid rgba(0, 0, 0, 0.1);
  flex-wrap: wrap;
  backdrop-filter: blur(10px);
}

.toolbar-group {
  display: flex;
  gap: 0.25rem;
  padding-right: 0.5rem;
  border-right: 1px solid #cbd5e0;
}

.toolbar-group:last-child {
  border-right: none;
  margin-left: auto;
}

.editor-toolbar button {
  padding: 0.375rem 0.75rem;
  border: 1px solid #cbd5e0;
  background: white;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.875rem;
  transition: all 0.2s;
  min-width: 32px;
}

.editor-toolbar button:hover {
  background: #edf2f7;
  border-color: #a0aec0;
}

.editor-toolbar button.active {
  background: #667eea;
  color: white;
  border-color: #667eea;
}

.editor-content {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.editor-content.split-view .editor-pane,
.editor-content.split-view .preview-pane {
  width: 50%;
  border-right: 1px solid #e2e8f0;
}

.editor-content.split-view .preview-pane {
  border-right: none;
}

.editor-pane,
.preview-pane {
  width: 100%;
  height: 100%;
  overflow: auto;
}

.markdown-textarea {
  width: 100%;
  height: 100%;
  padding: 1.5rem 1.5rem 1.5rem 80px;
  border: none;
  outline: none;
  font-family: Georgia, Palatino, 'Times New Roman', serif;
  font-size: 1rem;
  line-height: 24px;
  resize: none;
  background: transparent;
  color: var(--notebook-text);
}

.markdown-textarea::placeholder {
  color: #a0aec0;
}

.editor-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem;
  background: rgba(255, 255, 255, 0.5);
  border-top: 1px solid rgba(0, 0, 0, 0.1);
  backdrop-filter: blur(10px);
}

.editor-stats {
  display: flex;
  gap: 1rem;
  font-size: 0.75rem;
  color: #718096;
}

.editor-actions {
  display: flex;
  gap: 0.5rem;
}

.editor-actions button {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.875rem;
  font-weight: 500;
  transition: all 0.2s;
}

.btn-cancel {
  background: #e2e8f0;
  color: #2d3748;
}

.btn-cancel:hover {
  background: #cbd5e0;
}

.btn-save {
  background: #667eea;
  color: white;
}

.btn-save:hover {
  background: #5a67d8;
}
</style>
