<template>
  <div class="markdown-editor notebook-page ruled-paper" :class="themeStore.theme.className">
    <div class="editor-toolbar">
      <div class="toolbar-group mode-toggle">
        <button
          @click="setEditMode('live')"
          :class="{ active: editMode === 'live' }"
          title="Live Edit - Format as you type"
        >
          Live
        </button>
        <button
          @click="setEditMode('raw')"
          :class="{ active: editMode === 'raw' }"
          title="Raw - Plain text editing"
        >
          Raw
        </button>
      </div>
      <div class="toolbar-group" v-show="editMode === 'raw'">
        <button @click="insertBold" title="Bold">
          <strong>B</strong>
        </button>
        <button @click="insertItalic" title="Italic">
          <em>I</em>
        </button>
        <button @click="insertCode" title="Code">&lt;/&gt;</button>
        <button @click="insertLink" title="Link">🔗</button>
        <button @click="insertImage" title="Image">🖼️</button>
      </div>
      <div class="toolbar-group" v-show="editMode === 'raw'">
        <button @click="insertHeading(1)" title="Heading 1">H1</button>
        <button @click="insertHeading(2)" title="Heading 2">H2</button>
        <button @click="insertHeading(3)" title="Heading 3">H3</button>
      </div>
      <div class="toolbar-group" v-show="editMode === 'raw'">
        <button @click="insertList('ul')" title="Bullet List">• List</button>
        <button @click="insertList('ol')" title="Numbered List">1. List</button>
        <button @click="insertQuote" title="Quote">"</button>
      </div>
      <div class="toolbar-group" v-show="editMode === 'raw'">
        <button @click="togglePreview" :class="{ active: showPreview }">
          {{ showPreview ? "Edit" : "Preview" }}
        </button>
      </div>
      <div class="toolbar-group live-mode-hint" v-show="editMode === 'live'">
        <span class="hint-text">Type # for headings, - for lists, > for quotes, ``` for code</span>
      </div>
      <slot name="toolbar-actions"></slot>
    </div>

    <!-- Live Edit Mode -->
    <div class="editor-content live-mode" v-if="editMode === 'live'">
      <MarkdownLiveEditor
        ref="liveEditorRef"
        v-model="localContent"
        :placeholder="placeholder"
        @change="handleLiveChange"
      />
    </div>

    <!-- Raw Edit Mode -->
    <div class="editor-content" :class="{ 'split-view': showPreview && showEditor }" v-else>
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
        <span v-if="autosave" class="autosave-indicator">{{ autosaveStatus }}</span>
      </div>
      <div class="editor-actions" v-if="!autosave">
        <button @click="handleCancel" class="btn-cancel">Cancel</button>
        <button @click="handleSave" class="btn-save">Save</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick } from "vue"
import MarkdownViewer, { type MarkdownExtension } from "./MarkdownViewer.vue"
import MarkdownLiveEditor from "./MarkdownLiveEditor.vue"
import { useThemeStore } from "../stores/theme"

const themeStore = useThemeStore()

// Types
type EditMode = "live" | "raw"

// Props
interface Props {
  modelValue: string
  frontmatter?: Record<string, any>
  placeholder?: string
  autosave?: boolean
  autosaveDelay?: number
  extensions?: MarkdownExtension[]
  defaultMode?: EditMode
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: "",
  placeholder: "Start writing your markdown...",
  autosave: false,
  autosaveDelay: 1000,
  extensions: () => [],
  defaultMode: "live",
})

// Emits
const emit = defineEmits<{
  "update:modelValue": [value: string]
  save: [content: string]
  cancel: []
  change: [content: string]
}>()

// State
const localContent = ref(props.modelValue)
const editorTextarea = ref<HTMLTextAreaElement | null>(null)
const liveEditorRef = ref<InstanceType<typeof MarkdownLiveEditor> | null>(null)
const showPreview = ref(false)
const showEditor = ref(true)
const autosaveTimer = ref<number | null>(null)
const autosaveStatusTimer = ref<number | null>(null)
const autosaveStatus = ref("")
const editMode = ref<EditMode>(props.defaultMode)

// Computed
const characterCount = computed(() => localContent.value.length)
const wordCount = computed(() => {
  const text = localContent.value.trim()
  return text ? text.split(/\s+/).length : 0
})
const lineCount = computed(() => localContent.value.split("\n").length)

// Watch for external changes
watch(
  () => props.modelValue,
  (newValue) => {
    if (newValue !== localContent.value) {
      localContent.value = newValue
    }
  }
)

// Watch for local changes
watch(localContent, (newValue) => {
  emit("update:modelValue", newValue)
  emit("change", newValue)

  // Handle autosave
  if (props.autosave) {
    autosaveStatus.value = "Unsaved changes"
    if (autosaveTimer.value) {
      clearTimeout(autosaveTimer.value)
    }
    autosaveTimer.value = window.setTimeout(() => {
      emit("save", newValue)
      autosaveStatus.value = "Saved"
      if (autosaveStatusTimer.value) {
        clearTimeout(autosaveStatusTimer.value)
      }
      autosaveStatusTimer.value = window.setTimeout(() => {
        autosaveStatus.value = ""
      }, 2000)
    }, props.autosaveDelay)
  }
})

// Methods
const setEditMode = (mode: EditMode) => {
  editMode.value = mode
  // When switching modes, ensure content is synced
  nextTick(() => {
    if (mode === "raw" && editorTextarea.value) {
      editorTextarea.value.focus()
    } else if (mode === "live" && liveEditorRef.value) {
      liveEditorRef.value.focus()
    }
  })
}

const handleLiveChange = (content: string) => {
  // Content is already updated via v-model, just trigger autosave if enabled
  if (props.autosave) {
    if (autosaveTimer.value) {
      clearTimeout(autosaveTimer.value)
    }
    autosaveTimer.value = window.setTimeout(() => {
      emit("save", content)
    }, props.autosaveDelay)
  }
}

const handleInput = () => {
  // Input is handled by v-model
}

const handleKeydown = (e: KeyboardEvent) => {
  // Tab key - insert spaces
  if (e.key === "Tab") {
    e.preventDefault()
    insertAtCursor("  ")
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
  const replacement = before + (selectedText || "text") + after

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

const insertBold = () => wrapSelection("**", "**")
const insertItalic = () => wrapSelection("*", "*")
const insertCode = () => wrapSelection("`", "`")
const insertLink = () => wrapSelection("[", "](url)")
const insertImage = () => wrapSelection("![", "](url)")

const insertHeading = (level: number) => {
  const prefix = "#".repeat(level) + " "
  insertAtCursor(prefix)
}

const insertList = (type: "ul" | "ol") => {
  const prefix = type === "ul" ? "- " : "1. "
  insertAtCursor(prefix)
}

const insertQuote = () => {
  insertAtCursor("> ")
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
  emit("save", localContent.value)
}

const handleCancel = () => {
  emit("cancel")
}

// Expose methods for parent components
defineExpose({
  insertAtCursor,
  wrapSelection,
  getContent: () => localContent.value,
})
</script>

<style scoped>
.markdown-editor {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--color-bg-primary);
  border-radius: var(--radius-lg);
  overflow: hidden;
  border: 1px solid var(--color-border-light);
}

.editor-toolbar {
  display: flex;
  gap: var(--spacing-sm);
  padding: var(--spacing-md);
  background: color-mix(in srgb, var(--color-bg-primary) 50%, transparent);
  border-bottom: 1px solid var(--color-border-light);
  flex-wrap: wrap;
  backdrop-filter: blur(10px);
}

.toolbar-group {
  display: flex;
  gap: var(--spacing-xs);
  padding-right: var(--spacing-sm);
  border-right: 1px solid var(--color-border-medium);
}

.toolbar-group:last-child {
  border-right: none;
  margin-left: auto;
}

.toolbar-group.mode-toggle {
  background: var(--color-bg-secondary);
  border-radius: var(--radius-md);
  padding: 2px;
  gap: 2px;
}

.toolbar-group.mode-toggle button {
  border: none;
  background: transparent;
  padding: var(--spacing-xs) var(--spacing-md);
  min-width: auto;
}

.toolbar-group.mode-toggle button.active {
  background: var(--color-bg-tertiary);
  box-shadow: var(--shadow-sm);
  color: var(--color-text-primary);
}

.toolbar-group.live-mode-hint {
  border-right: none;
  flex: 1;
  justify-content: center;
}

.toolbar-group.live-mode-hint .hint-text {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
  font-style: italic;
}

.editor-toolbar button {
  padding: var(--spacing-sm) var(--spacing-md);
  border: 1px solid var(--color-border-medium);
  background: var(--color-bg-primary);
  color: var(--color-text-primary);
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  transition: all 0.2s;
  min-width: 32px;
}

.editor-toolbar button:hover {
  background: var(--color-bg-hover);
  border-color: var(--color-border-dark);
}

.editor-toolbar button.active {
  background: var(--color-primary);
  color: var(--color-text-inverse);
  border-color: var(--color-primary);
}

.editor-content {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.editor-content.live-mode {
  flex-direction: column;
}

.editor-content.split-view .editor-pane,
.editor-content.split-view .preview-pane {
  width: 50%;
  border-right: 1px solid var(--color-border-light);
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
  padding: var(--spacing-xl) var(--spacing-xl) var(--spacing-xl) 80px;
  border: none;
  outline: none;
  font-family: var(--font-serif);
  font-size: var(--text-base);
  line-height: var(--grid-size);
  resize: none;
  background: transparent;
  color: var(--notebook-text);
}

.markdown-textarea::placeholder {
  color: var(--color-text-placeholder);
  font-style: italic;
}

.editor-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-md);
  background: color-mix(in srgb, var(--color-bg-primary) 50%, transparent);
  border-top: 1px solid var(--color-border-light);
  backdrop-filter: blur(10px);
}

.editor-stats {
  display: flex;
  gap: var(--spacing-lg);
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
}

.editor-actions {
  display: flex;
  gap: var(--spacing-sm);
}

.editor-actions button {
  padding: var(--spacing-sm) var(--spacing-lg);
  border: none;
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  transition: all 0.2s;
}

.btn-cancel {
  background: var(--color-bg-disabled);
  color: var(--color-text-primary);
}

.btn-cancel:hover {
  background: var(--color-border-medium);
}

.btn-save {
  background: var(--color-primary);
  color: var(--color-text-inverse);
}

.btn-save:hover {
  background: var(--color-primary-hover);
}

.autosave-indicator {
  font-style: italic;
  color: var(--color-text-tertiary);
}
</style>
