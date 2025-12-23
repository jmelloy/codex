<script setup lang="ts">
import { ref, computed, watch } from "vue";
import MarkdownViewer from "./MarkdownViewer.vue";

const props = withDefaults(
  defineProps<{
    modelValue: string;
    placeholder?: string;
    editable?: boolean;
    showPreview?: boolean;
    minHeight?: string;
    maxHeight?: string;
  }>(),
  {
    modelValue: "",
    placeholder: "Enter markdown text...",
    editable: true,
    showPreview: true,
    minHeight: "200px",
    maxHeight: "600px",
  }
);

const emit = defineEmits<{
  (e: "update:modelValue", value: string): void;
}>();

const mode = ref<"edit" | "preview" | "split">("split");
const localContent = ref(props.modelValue);
const textareaRef = ref<HTMLTextAreaElement | null>(null);

// Sync local content with prop
watch(() => props.modelValue, (newValue) => {
  localContent.value = newValue;
});

// Emit changes
function handleInput(event: Event) {
  const value = (event.target as HTMLTextAreaElement).value;
  localContent.value = value;
  emit("update:modelValue", value);
}

// Auto-resize textarea
function autoResize() {
  if (textareaRef.value) {
    textareaRef.value.style.height = "auto";
    const newHeight = Math.min(
      Math.max(textareaRef.value.scrollHeight, parseInt(props.minHeight)),
      parseInt(props.maxHeight)
    );
    textareaRef.value.style.height = `${newHeight}px`;
  }
}

// Keyboard shortcuts
function handleKeydown(event: KeyboardEvent) {
  // Tab key inserts 2 spaces
  if (event.key === "Tab") {
    event.preventDefault();
    const textarea = event.target as HTMLTextAreaElement;
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const value = textarea.value;
    
    textarea.value = value.substring(0, start) + "  " + value.substring(end);
    textarea.selectionStart = textarea.selectionEnd = start + 2;
    handleInput(event);
  }
}

const showEdit = computed(() => mode.value === "edit" || mode.value === "split");
const showPreviewPane = computed(() => props.showPreview && (mode.value === "preview" || mode.value === "split"));
</script>

<template>
  <div class="markdown-editor">
    <!-- Toolbar -->
    <div v-if="editable && showPreview" class="editor-toolbar">
      <button
        type="button"
        class="toolbar-btn"
        :class="{ active: mode === 'edit' }"
        @click="mode = 'edit'"
        title="Edit mode"
      >
        ✏️ Edit
      </button>
      <button
        type="button"
        class="toolbar-btn"
        :class="{ active: mode === 'split' }"
        @click="mode = 'split'"
        title="Split mode"
      >
        📄 Split
      </button>
      <button
        type="button"
        class="toolbar-btn"
        :class="{ active: mode === 'preview' }"
        @click="mode = 'preview'"
        title="Preview mode"
      >
        👁️ Preview
      </button>
    </div>

    <!-- Editor panes -->
    <div class="editor-panes" :class="`mode-${mode}`">
      <!-- Edit pane -->
      <div v-if="showEdit" class="editor-pane edit-pane">
        <textarea
          ref="textareaRef"
          v-model="localContent"
          class="editor-textarea"
          :placeholder="placeholder"
          :readonly="!editable"
          @input="handleInput"
          @keydown="handleKeydown"
          @focus="autoResize"
        ></textarea>
      </div>

      <!-- Preview pane -->
      <div v-if="showPreviewPane" class="editor-pane preview-pane">
        <div v-if="localContent" class="preview-content">
          <MarkdownViewer :content="localContent" />
        </div>
        <div v-else class="preview-empty">
          {{ placeholder }}
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.markdown-editor {
  display: flex;
  flex-direction: column;
  border: 1px solid var(--color-border, #e5e7eb);
  border-radius: var(--radius-md, 0.375rem);
  overflow: hidden;
  background: var(--color-surface, #fff);
}

.editor-toolbar {
  display: flex;
  gap: 0.25rem;
  padding: 0.5rem;
  background: var(--color-background, #f5f5f5);
  border-bottom: 1px solid var(--color-border, #e5e7eb);
}

.toolbar-btn {
  padding: 0.375rem 0.75rem;
  background: transparent;
  border: 1px solid transparent;
  border-radius: var(--radius-sm, 0.25rem);
  font-size: 0.875rem;
  cursor: pointer;
  transition: all 0.2s;
  color: var(--color-text, #333);
}

.toolbar-btn:hover {
  background: var(--color-surface, #fff);
  border-color: var(--color-border, #e5e7eb);
}

.toolbar-btn.active {
  background: var(--color-primary, #4f46e5);
  color: white;
  border-color: var(--color-primary, #4f46e5);
}

.editor-panes {
  display: flex;
  min-height: v-bind(minHeight);
  max-height: v-bind(maxHeight);
}

.editor-panes.mode-edit,
.editor-panes.mode-preview {
  display: block;
}

.editor-panes.mode-split {
  display: grid;
  grid-template-columns: 1fr 1fr;
}

.editor-pane {
  flex: 1;
  overflow: auto;
}

.edit-pane {
  border-right: 1px solid var(--color-border, #e5e7eb);
}

.editor-panes.mode-edit .edit-pane,
.editor-panes.mode-preview .preview-pane {
  border-right: none;
}

.editor-textarea {
  width: 100%;
  height: 100%;
  min-height: v-bind(minHeight);
  max-height: v-bind(maxHeight);
  padding: 1rem;
  border: none;
  outline: none;
  resize: vertical;
  font-family: var(--font-mono, monospace);
  font-size: 0.875rem;
  line-height: 1.6;
  background: var(--color-surface, #fff);
  color: var(--color-text, #333);
}

.editor-textarea::placeholder {
  color: var(--color-text-secondary, #999);
  font-style: italic;
}

.preview-pane {
  background: var(--color-surface, #fff);
}

.preview-content {
  padding: 1rem;
}

.preview-empty {
  padding: 1rem;
  color: var(--color-text-secondary, #999);
  font-style: italic;
  text-align: center;
}

/* Responsive */
@media (max-width: 768px) {
  .editor-panes.mode-split {
    grid-template-columns: 1fr;
  }
  
  .edit-pane {
    border-right: none;
    border-bottom: 1px solid var(--color-border, #e5e7eb);
  }
}
</style>
