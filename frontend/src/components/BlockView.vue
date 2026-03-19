<template>
  <div class="block-view">
    <div class="page-header" v-if="pageTitle">
      <h1 class="page-title">{{ pageTitle }}</h1>
      <p class="page-description" v-if="pageDescription">{{ pageDescription }}</p>
    </div>

    <div class="blocks-container" v-if="blocks.length > 0">
      <div
        v-for="(block, index) in blocks"
        :key="block.block_id"
        class="block-item"
        :class="[`block-type-${block.block_type}`, { 'is-dragging': dragIndex === index }]"
        :draggable="editingBlockId !== block.block_id"
        @dragstart="onDragStart($event, index)"
        @dragover.prevent="onDragOver($event, index)"
        @drop="onDrop($event, index)"
        @dragend="onDragEnd"
      >
        <div class="block-handle" title="Drag to reorder">
          <span class="handle-icon">&#x2630;</span>
        </div>

        <div class="block-content" @click="startEditing(block)">
          <!-- Editing mode -->
          <template v-if="editingBlockId === block.block_id">
            <textarea
              ref="editTextarea"
              v-model="editContent"
              class="block-editor-textarea"
              :class="`edit-${block.block_type}`"
              @blur="finishEditing(block)"
              @keydown.escape="cancelEditing"
              @keydown.enter.ctrl="finishEditing(block)"
              @keydown.enter.meta="finishEditing(block)"
              :placeholder="getPlaceholder(block.block_type)"
              autofocus
            ></textarea>
          </template>

          <!-- View mode -->
          <template v-else>
            <!-- Heading -->
            <template v-if="block.block_type === 'heading'">
              <div class="block-heading" v-html="renderMarkdown(block.content || '')"></div>
            </template>

            <!-- Text -->
            <template v-else-if="block.block_type === 'text'">
              <div class="block-text" v-html="renderMarkdown(block.content || '')"></div>
            </template>

            <!-- Code -->
            <template v-else-if="block.block_type === 'code'">
              <div class="block-code" v-html="renderMarkdown(block.content || '')"></div>
            </template>

            <!-- Image -->
            <template v-else-if="block.block_type === 'image'">
              <div class="block-image" v-html="renderMarkdown(block.content || '')"></div>
            </template>

            <!-- List -->
            <template v-else-if="block.block_type === 'list'">
              <div class="block-list" v-html="renderMarkdown(block.content || '')"></div>
            </template>

            <!-- Quote -->
            <template v-else-if="block.block_type === 'quote'">
              <div class="block-quote" v-html="renderMarkdown(block.content || '')"></div>
            </template>

            <!-- Divider -->
            <template v-else-if="block.block_type === 'divider'">
              <hr class="block-divider" />
            </template>

            <!-- Nested Page -->
            <template v-else-if="block.block_type === 'page'">
              <div class="block-page-link" @click.stop="$emit('navigatePage', block)">
                <span class="page-icon">&#x1F4C4;</span>
                <span class="page-name">{{ block.title || block.path }}</span>
              </div>
            </template>

            <!-- File / Other -->
            <template v-else>
              <div class="block-file">
                <span class="file-icon">&#x1F4CE;</span>
                <span class="file-name">{{ block.path?.split('/').pop() }}</span>
              </div>
            </template>
          </template>
        </div>

        <div class="block-actions">
          <button
            class="btn-block-action"
            title="Delete block"
            @click="$emit('deleteBlock', block.block_id)"
          >
            &times;
          </button>
        </div>
      </div>
    </div>

    <div class="blocks-empty" v-else>
      <p>This page has no blocks yet.</p>
      <button class="btn-add-block" @click="showAddMenu = !showAddMenu">Add a block</button>
    </div>

    <!-- Add block area at bottom -->
    <div class="add-block-footer" v-if="blocks.length > 0">
      <div class="add-block-row">
        <button class="btn-add-block" @click="showAddMenu = !showAddMenu">+ Add block</button>
      </div>
      <div v-if="showAddMenu" class="add-block-menu">
        <button
          v-for="bt in blockTypes"
          :key="bt.type"
          class="add-block-option"
          @click="addBlockOfType(bt.type, bt.defaultContent)"
        >
          <span class="add-block-icon">{{ bt.icon }}</span>
          <span>{{ bt.label }}</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, watch } from "vue"
import { marked } from "marked"
import type { Block } from "../services/codex"

interface Props {
  blocks: Block[]
  pageTitle?: string
  pageDescription?: string
}

const props = withDefaults(defineProps<Props>(), {
  blocks: () => [],
  pageTitle: undefined,
  pageDescription: undefined,
})

const emit = defineEmits<{
  navigatePage: [block: Block]
  deleteBlock: [blockId: string]
  addBlock: [blockType: string, content: string]
  reorder: [blockIds: string[]]
  editBlock: [block: Block]
  updateBlock: [block: { block_id: string; content: string }]
}>()

// Drag state
const dragIndex = ref<number | null>(null)
const dragOverIndex = ref<number | null>(null)

// Inline editing state
const editingBlockId = ref<string | null>(null)
const editContent = ref("")
const editTextarea = ref<HTMLTextAreaElement[] | null>(null)

// Add block menu
const showAddMenu = ref(false)

const blockTypes = [
  { type: "text", label: "Text", icon: "T", defaultContent: "" },
  { type: "heading", label: "Heading", icon: "H", defaultContent: "## " },
  { type: "code", label: "Code", icon: "<>", defaultContent: "```\n\n```" },
  { type: "list", label: "List", icon: "-", defaultContent: "- " },
  { type: "quote", label: "Quote", icon: ">", defaultContent: "> " },
  { type: "divider", label: "Divider", icon: "--", defaultContent: "---" },
]

function renderMarkdown(content: string): string {
  try {
    return marked.parse(content, { async: false }) as string
  } catch {
    return content
  }
}

function getPlaceholder(blockType: string): string {
  switch (blockType) {
    case "heading": return "Heading text..."
    case "code": return "Code..."
    case "list": return "- List item..."
    case "quote": return "> Quote..."
    default: return "Type something..."
  }
}

function startEditing(block: Block) {
  if (block.block_type === "page" || block.block_type === "divider") return
  editingBlockId.value = block.block_id
  editContent.value = block.content || ""
  nextTick(() => {
    if (editTextarea.value && editTextarea.value.length > 0) {
      const ta = editTextarea.value[0]
      if (ta) {
        ta.focus()
        autoResizeTextarea(ta)
      }
    }
  })
}

function finishEditing(block: Block) {
  if (editingBlockId.value !== block.block_id) return
  const newContent = editContent.value
  editingBlockId.value = null
  if (newContent !== (block.content || "")) {
    emit("updateBlock", { block_id: block.block_id, content: newContent })
  }
}

function cancelEditing() {
  editingBlockId.value = null
  editContent.value = ""
}

function autoResizeTextarea(el: HTMLTextAreaElement) {
  el.style.height = "auto"
  el.style.height = el.scrollHeight + "px"
}

// Watch editContent for auto-resize
watch(editContent, () => {
  nextTick(() => {
    if (editTextarea.value && editTextarea.value.length > 0) {
      const ta = editTextarea.value[0]
      if (ta) autoResizeTextarea(ta)
    }
  })
})

function addBlockOfType(blockType: string, defaultContent: string) {
  showAddMenu.value = false
  emit("addBlock", blockType, defaultContent)
}

function onDragStart(event: DragEvent, index: number) {
  dragIndex.value = index
  if (event.dataTransfer) {
    event.dataTransfer.effectAllowed = "move"
    event.dataTransfer.setData("text/plain", String(index))
  }
}

function onDragOver(_event: DragEvent, index: number) {
  dragOverIndex.value = index
}

function onDrop(_event: DragEvent, targetIndex: number) {
  const sourceIndex = dragIndex.value
  if (sourceIndex === null || sourceIndex === targetIndex) return

  const newOrder = [...props.blocks]
  const [moved] = newOrder.splice(sourceIndex, 1)
  if (moved) {
    newOrder.splice(targetIndex, 0, moved)
    emit("reorder", newOrder.map((b) => b.block_id))
  }
  dragIndex.value = null
  dragOverIndex.value = null
}

function onDragEnd() {
  dragIndex.value = null
  dragOverIndex.value = null
}
</script>

<style scoped>
.block-view {
  max-width: 900px;
  margin: 0 auto;
  padding: 1.5rem;
  overflow-y: auto;
}

.page-header {
  margin-bottom: 1.5rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid var(--border-color, #e0e0e0);
}

.page-title {
  font-size: 2rem;
  font-weight: 700;
  margin: 0 0 0.5rem;
}

.page-description {
  color: var(--text-secondary, #666);
  margin: 0;
}

.block-item {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  padding: 0.25rem 0;
  border-radius: 4px;
  transition: background-color 0.15s;
}

.block-item:hover {
  background-color: var(--hover-bg, #f5f5f5);
}

.block-item:hover .block-handle,
.block-item:hover .block-actions {
  opacity: 1;
}

.block-handle {
  opacity: 0;
  cursor: grab;
  padding: 0.25rem;
  color: var(--text-tertiary, #999);
  user-select: none;
  flex-shrink: 0;
  margin-top: 0.125rem;
}

.block-handle:active {
  cursor: grabbing;
}

.handle-icon {
  font-size: 0.75rem;
}

.block-content {
  flex: 1;
  min-width: 0;
  cursor: text;
}

.block-editor-textarea {
  width: 100%;
  min-height: 2rem;
  padding: 0.25rem 0.5rem;
  border: 1px solid var(--border-color, #d0d0d0);
  border-radius: 4px;
  background: var(--bg-primary, #fff);
  color: var(--text-primary, #333);
  font-family: inherit;
  font-size: inherit;
  line-height: 1.5;
  resize: vertical;
  outline: none;
}

.block-editor-textarea:focus {
  border-color: var(--accent-color, #2563eb);
  box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.15);
}

.edit-code {
  font-family: monospace;
  font-size: 0.9em;
}

.block-actions {
  opacity: 0;
  flex-shrink: 0;
}

.btn-block-action {
  background: none;
  border: none;
  cursor: pointer;
  color: var(--text-tertiary, #999);
  font-size: 1.2rem;
  padding: 0 0.25rem;
}

.btn-block-action:hover {
  color: var(--danger-color, #e74c3c);
}

.block-type-divider {
  padding: 0.5rem 0;
}

.block-divider {
  border: none;
  border-top: 1px solid var(--border-color, #e0e0e0);
  margin: 0;
}

.block-page-link {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem;
  border-radius: 4px;
  cursor: pointer;
  color: var(--link-color, #2563eb);
}

.block-page-link:hover {
  background-color: var(--hover-bg, #f0f0f0);
}

.page-icon {
  font-size: 1.2rem;
}

.block-file {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem;
  color: var(--text-secondary, #666);
}

.blocks-empty {
  text-align: center;
  padding: 3rem;
  color: var(--text-secondary, #666);
}

.btn-add-block {
  background: none;
  border: 1px dashed var(--border-color, #ccc);
  border-radius: 4px;
  padding: 0.5rem 1rem;
  cursor: pointer;
  color: var(--text-secondary, #666);
  width: 100%;
  text-align: center;
  margin-top: 0.5rem;
}

.btn-add-block:hover {
  background-color: var(--hover-bg, #f5f5f5);
  border-color: var(--text-secondary, #999);
}

.add-block-footer {
  margin-top: 0.5rem;
}

.add-block-menu {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  padding: 0.75rem;
  margin-top: 0.5rem;
  border: 1px solid var(--border-color, #e0e0e0);
  border-radius: 6px;
  background: var(--bg-primary, #fff);
}

.add-block-option {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--border-color, #e0e0e0);
  border-radius: 4px;
  background: var(--bg-secondary, #f9f9f9);
  cursor: pointer;
  color: var(--text-primary, #333);
  font-size: 0.875rem;
}

.add-block-option:hover {
  background: var(--hover-bg, #f0f0f0);
  border-color: var(--accent-color, #2563eb);
}

.add-block-icon {
  font-weight: 700;
  font-size: 0.8rem;
  width: 1.5rem;
  height: 1.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 3px;
  background: var(--bg-tertiary, #eee);
}

.is-dragging {
  opacity: 0.5;
}

/* Markdown content styling */
.block-content :deep(h1),
.block-content :deep(h2),
.block-content :deep(h3),
.block-content :deep(h4),
.block-content :deep(h5),
.block-content :deep(h6) {
  margin: 0;
}

.block-content :deep(p) {
  margin: 0.25rem 0;
}

.block-content :deep(pre) {
  margin: 0;
  border-radius: 4px;
}

.block-content :deep(blockquote) {
  margin: 0;
  padding-left: 1rem;
  border-left: 3px solid var(--border-color, #e0e0e0);
}

.block-content :deep(ul),
.block-content :deep(ol) {
  margin: 0;
  padding-left: 1.5rem;
}

.block-content :deep(img) {
  max-width: 100%;
  border-radius: 4px;
}
</style>
