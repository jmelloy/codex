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
        :draggable="true"
        @dragstart="onDragStart($event, index)"
        @dragover.prevent="onDragOver($event, index)"
        @drop="onDrop($event, index)"
        @dragend="onDragEnd"
      >
        <div class="block-handle" title="Drag to reorder">
          <span class="handle-icon">&#x2630;</span>
        </div>

        <div class="block-content" @dblclick="startEditing(block)">
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
            <div class="block-page-link" @click="$emit('navigatePage', block)">
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
      <button class="btn-add-block" @click="$emit('addBlock')">Add a block</button>
    </div>

    <!-- Add block button at bottom -->
    <div class="add-block-footer" v-if="blocks.length > 0">
      <button class="btn-add-block" @click="$emit('addBlock')">+ Add block</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue"
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
  addBlock: []
  reorder: [blockIds: string[]]
  editBlock: [block: Block]
}>()

// Drag state
const dragIndex = ref<number | null>(null)
const dragOverIndex = ref<number | null>(null)

function renderMarkdown(content: string): string {
  try {
    return marked.parse(content, { async: false }) as string
  } catch {
    return content
  }
}

function startEditing(block: Block) {
  emit("editBlock", block)
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

  // Reorder blocks
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
