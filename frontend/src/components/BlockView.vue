<template>
  <div
    class="block-editor"
    :class="{ 'drop-active': dropActive }"
    @click="handleEditorClick"
    @dragover.prevent="onFileDragOver"
    @dragenter.prevent="onFileDragEnter"
    @dragleave="onFileDragLeave"
    @drop.prevent="onFileDrop"
  >
    <div class="page-header" v-if="pageTitle">
      <div class="page-header-row">
        <h1 class="page-title">{{ pageTitle }}</h1>
        <button class="new-page-btn" @click.stop="$emit('createSubpage')" title="New subpage">
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.5">
            <line x1="7" y1="2" x2="7" y2="12" /><line x1="2" y1="7" x2="12" y2="7" />
          </svg>
          New page
        </button>
      </div>
      <p class="page-description" v-if="pageDescription">{{ pageDescription }}</p>
    </div>

    <div class="blocks-container">
      <div
        v-for="(block, index) in blocks"
        :key="block.block_id"
        class="block-wrapper"
        :class="{
          'is-dragging': dragIndex === index,
          'drag-over-top': dragOverIndex === index && dragPosition === 'top',
          'drag-over-bottom': dragOverIndex === index && dragPosition === 'bottom',
        }"
        @mouseenter="hoveredIndex = index"
        @mouseleave="handleBlockMouseLeave(index)"
      >
        <!-- Left gutter -->
        <div class="block-gutter" :class="{ visible: hoveredIndex === index || typeMenuIndex === index }">
          <button
            class="gutter-btn gutter-add"
            title="Add block"
            @click.stop="insertBlockAt(index)"
          >
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="6" y1="1" x2="6" y2="11" /><line x1="1" y1="6" x2="11" y2="6" />
            </svg>
          </button>
          <button
            class="gutter-btn gutter-drag"
            title="Drag to reorder / Change type"
            draggable="true"
            @click.stop="toggleTypeMenu(index)"
            @dragstart="onDragStart($event, index)"
            @dragend="onDragEnd"
          >
            <svg width="10" height="14" viewBox="0 0 10 14" fill="currentColor">
              <circle cx="3" cy="2" r="1.2" /><circle cx="7" cy="2" r="1.2" />
              <circle cx="3" cy="7" r="1.2" /><circle cx="7" cy="7" r="1.2" />
              <circle cx="3" cy="12" r="1.2" /><circle cx="7" cy="12" r="1.2" />
            </svg>
          </button>
        </div>

        <!-- Type menu popover -->
        <div
          v-if="typeMenuIndex === index"
          class="type-menu"
          @mouseleave="typeMenuIndex = null"
        >
          <button
            v-for="bt in blockTypes"
            :key="bt.type"
            class="type-menu-item"
            :class="{ active: block.block_type === bt.type }"
            @click.stop="changeBlockType(block, bt.type, bt.defaultContent)"
          >
            <span class="type-icon">{{ bt.icon }}</span>
            <span class="type-label">{{ bt.label }}</span>
          </button>
          <template v-if="dynamicBlockTypes.length > 0">
            <div class="type-menu-divider"></div>
            <div class="type-menu-section-label">Dynamic</div>
            <button
              v-for="bt in dynamicBlockTypes"
              :key="bt.type"
              class="type-menu-item"
              :class="{ active: block.block_type === bt.type }"
              @click.stop="changeBlockType(block, bt.type, bt.defaultContent)"
            >
              <span class="type-icon">{{ bt.icon }}</span>
              <span class="type-label">{{ bt.label }}</span>
            </button>
          </template>
          <div class="type-menu-divider"></div>
          <button class="type-menu-item type-menu-delete" @click.stop="$emit('deleteBlock', block.block_id)">
            <span class="type-icon">&#x2715;</span>
            <span class="type-label">Delete</span>
          </button>
        </div>

        <!-- Drop zone -->
        <div
          class="block-drop-zone"
          @dragover.prevent="onDragOver($event, index)"
          @drop="onDrop($event, index)"
        >
          <!-- Block content area -->
          <div class="block-content" :class="`block-type-${block.block_type}`">
            <!-- Divider block -->
            <template v-if="block.block_type === 'divider'">
              <hr class="block-divider" />
            </template>

            <!-- Page link -->
            <template v-else-if="block.block_type === 'page'">
              <div class="block-page-link" @click.stop="$emit('navigatePage', block)">
                <span class="page-icon">&#x1F4C4;</span>
                <span class="page-name">{{ block.title || block.path }}</span>
              </div>
            </template>

            <!-- Image block -->
            <template v-else-if="block.block_type === 'image' && block.block_id">
              <div class="block-image">
                <img
                  :src="getBlockFileUrl(block)"
                  :alt="getBlockFileName(block)"
                  loading="lazy"
                />
                <div class="block-image-caption">{{ getBlockFileName(block) }}</div>
              </div>
            </template>

            <!-- File block -->
            <template v-else-if="block.block_type === 'file' && block.block_id">
              <a class="block-file-link" :href="getBlockFileUrl(block)" target="_blank" download>
                <span class="file-icon">&#x1F4CE;</span>
                <span class="file-name">{{ getBlockFileName(block) }}</span>
              </a>
            </template>

            <!-- Database block -->
            <template v-else-if="block.block_type === 'database'">
              <DatabaseBlock
                :config="parseDatabaseConfig(block)"
                :workspace-id="workspaceId ? Number(workspaceId) : undefined"
                :notebook-id="notebookId ? Number(notebookId) : undefined"
                :parent-block-id="blocks[0]?.parent_block_id || undefined"
                @navigate-page="(b: any) => $emit('navigatePage', b)"
              />
            </template>

            <!-- Editable blocks -->
            <template v-else>
              <!-- Editing mode -->
              <textarea
                v-if="editingBlockId === block.block_id"
                ref="textareaRefs"
                v-model="editContent"
                class="block-textarea"
                :class="[`textarea-${block.block_type}`, { 'is-empty': !editContent }]"
                :placeholder="getPlaceholder(block.block_type)"
                :data-block-index="index"
                @blur="finishEditing(block)"
                @keydown="handleKeydown($event, block, index)"
                @input="autoResize($event)"
                @paste="handleBlockPaste($event, block, index)"
              ></textarea>

              <!-- View mode -->
              <div
                v-else
                class="block-rendered"
                :class="{ 'is-empty': !block.content }"
                @click.stop="handleRenderedBlockClick($event, block, index)"
              >
                <div v-if="block.content" v-html="renderBlock(block)"></div>
                <span v-else class="block-placeholder-text">{{ getPlaceholder(block.block_type) }}</span>
              </div>
            </template>
          </div>
        </div>
      </div>
    </div>

    <!-- Trailing click area to add a new block -->
    <div class="block-trailing-area" @click="addBlockAtEnd">
      <span class="trailing-hint">&nbsp;</span>
    </div>

    <!-- Hidden file input for file uploads -->
    <input
      ref="fileInputRef"
      type="file"
      style="display: none"
      @change="handleFileSelected"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, watch, onMounted } from "vue"
import { Marked } from "marked"
import type { Block } from "../services/codex"
import { blockService } from "../services/codex"
import { getAvailableBlockTypes } from "../services/pluginLoader"
import { isLocalFileReference, resolveFileUrl } from "../utils/markdownHelpers"
import DatabaseBlock from "./blocks/DatabaseBlock.vue"

interface Props {
  blocks: Block[]
  pageTitle?: string
  pageDescription?: string
  workspaceId?: number | string
  notebookId?: number | string
}

const props = withDefaults(defineProps<Props>(), {
  blocks: () => [],
  pageTitle: undefined,
  pageDescription: undefined,
})

const emit = defineEmits<{
  navigatePage: [block: Block]
  deleteBlock: [blockId: string]
  addBlock: [blockType: string, content: string, position?: number]
  reorder: [blockIds: string[]]
  updateBlock: [block: { block_id: string; content: string; block_type?: string }]
  createSubpage: []
  uploadFile: [file: File, parentBlockId: string | undefined, position?: number]
}>()

// File input ref for file uploads
const fileInputRef = ref<HTMLInputElement | null>(null)
const pendingFilePosition = ref<number | undefined>(undefined)

// Editing state
const editingBlockId = ref<string | null>(null)
const editContent = ref("")
const textareaRefs = ref<HTMLTextAreaElement[]>([])

// Hover state
const hoveredIndex = ref<number | null>(null)

// Type menu
const typeMenuIndex = ref<number | null>(null)

// Drag state
const dragIndex = ref<number | null>(null)
const dragOverIndex = ref<number | null>(null)
const dragPosition = ref<"top" | "bottom">("bottom")

// Focus tracking - when a new block is created, focus it
const pendingFocusIndex = ref<number | null>(null)

const blockTypes = [
  { type: "text", label: "Text", icon: "T", defaultContent: "" },
  { type: "heading", label: "Heading", icon: "H", defaultContent: "## " },
  { type: "image-upload", label: "Image", icon: "Img", defaultContent: "" },
  { type: "file-upload", label: "File", icon: "📎", defaultContent: "" },
  { type: "code", label: "Code", icon: "<>", defaultContent: "```\n\n```" },
  { type: "list", label: "List", icon: "=", defaultContent: "- " },
  { type: "quote", label: "Quote", icon: ">", defaultContent: "> " },
  { type: "divider", label: "Divider", icon: "--", defaultContent: "---" },
]

// Default YAML templates for dynamic block types
const dynamicBlockTemplates: Record<string, string> = {
  database: "source: children\ndisplay: table",
  api: "url: https://api.example.com/data\nmethod: GET\ndisplay: json",
}

// Dynamic block types loaded from plugins
const dynamicBlockTypes = ref<Array<{ type: string; label: string; icon: string; defaultContent: string }>>([])

onMounted(async () => {
  try {
    const available = await getAvailableBlockTypes()
    dynamicBlockTypes.value = available.map((bt) => ({
      type: bt.blockType,
      label: bt.pluginName,
      icon: bt.icon || "{}",
      defaultContent: "```" + bt.blockType + "\n" + (dynamicBlockTemplates[bt.blockType] || "") + "\n```",
    }))
  } catch {
    // Plugin manifest unavailable — dynamic types won't appear
  }
})

// Watch blocks for pending focus
watch(
  () => props.blocks,
  () => {
    if (pendingFocusIndex.value !== null) {
      const idx = pendingFocusIndex.value
      pendingFocusIndex.value = null
      nextTick(() => {
        const block = props.blocks[idx]
        if (block && block.block_type !== "divider" && block.block_type !== "page") {
          startEditing(block, idx)
        }
      })
    }
  },
)

// Auto-focus first empty block on mount
onMounted(() => {
  if (props.blocks.length === 1 && !props.blocks[0]!.content) {
    nextTick(() => startEditing(props.blocks[0]!, 0))
  }
})

/** Parse YAML-like config from a database block's code fence content */
function parseDatabaseConfig(block: Block): Record<string, any> {
  const content = block.content || ""
  // Strip code fence markers: ```database\n...\n```
  const match = content.match(/^```\w*\n([\s\S]*?)\n```$/)
  const body = match ? match[1] : content
  const config: Record<string, any> = {}
  let currentParent: string | null = null
  body.split("\n").forEach((line) => {
    const indented = line.match(/^[ \t]+([\w-]+):\s*(.+)$/)
    if (indented && indented[1] && indented[2] && currentParent) {
      if (typeof config[currentParent] !== "object" || config[currentParent] === null) {
        config[currentParent] = {}
      }
      config[currentParent][indented[1]] = indented[2].trim()
      return
    }
    const kv = line.match(/^([\w-]+):\s*(.+)$/)
    if (kv && kv[1] && kv[2]) {
      config[kv[1]] = kv[2].trim()
      currentParent = null
      return
    }
    const parent = line.match(/^([\w-]+):\s*$/)
    if (parent && parent[1]) {
      currentParent = parent[1]
      config[currentParent] = {}
    }
  })
  return config
}

function getBlockFileUrl(block: Block): string {
  if (!props.workspaceId || !props.notebookId || !block.block_id) return ""
  return `/api/v1/workspaces/${props.workspaceId}/notebooks/${props.notebookId}/blocks/${block.block_id}/content`
}

function getBlockFileName(block: Block): string {
  if (!block.path) return ""
  return block.path.split("/").pop() || block.path
}

// Create a local Marked instance with custom renderer for resolving links/images
function createMarkedInstance(): Marked {
  const instance = new Marked()
  instance.use({
    renderer: {
      image({ href, title, text }: { href: string; title?: string | null; text: string }): string {
        const resolvedHref = resolveFileUrl(href, props.workspaceId, props.notebookId)
        const titleAttr = title ? ` title="${title}"` : ""
        const alt = text || ""
        return `<img src="${resolvedHref}" alt="${alt}"${titleAttr}>`
      },
      link({ href, title, text }: { href: string; title?: string | null; text: string }): string {
        const titleAttr = title ? ` title="${title}"` : ""
        const displayText = text || ""
        if (href && !isLocalFileReference(href)) {
          // External link: open in new tab
          return `<a href="${href}"${titleAttr} target="_blank" rel="noopener">${displayText}</a>`
        }
        // Internal/local link: resolve URL, add data attribute for navigation
        const resolvedHref = resolveFileUrl(href, props.workspaceId, props.notebookId)
        return `<a href="${resolvedHref}"${titleAttr} data-internal-link="${href}">${displayText}</a>`
      },
    },
  })
  instance.setOptions({ breaks: true, gfm: true })
  return instance
}

const markedInstance = createMarkedInstance()

function renderBlock(block: Block): string {
  try {
    return markedInstance.parse(block.content || "", { async: false }) as string
  } catch {
    return block.content || ""
  }
}

function getPlaceholder(_blockType: string): string {
  return ""
}

function startEditing(block: Block, _index: number) {
  if (block.block_type === "page" || block.block_type === "divider") return
  editingBlockId.value = block.block_id
  editContent.value = block.content || ""
  nextTick(() => {
    const textareas = textareaRefs.value
    if (textareas && textareas.length > 0) {
      const ta = textareas[0]!
      ta.focus()
      // Place cursor at end
      ta.selectionStart = ta.selectionEnd = ta.value.length
      autoResizeElement(ta)
    }
  })
}

function finishEditing(block: Block) {
  if (editingBlockId.value !== block.block_id) return
  const newContent = editContent.value
  if (newContent !== (block.content || "")) {
    // Update local content before clearing edit state so the rendered view shows new text immediately
    ;(block as any).content = newContent
    editingBlockId.value = null
    emit("updateBlock", { block_id: block.block_id, content: newContent })
  } else {
    editingBlockId.value = null
  }
}

function saveAndNavigate(block: Block, _fromIndex: number, toIndex: number) {
  const newContent = editContent.value
  if (newContent !== (block.content || "")) {
    ;(block as any).content = newContent
    emit("updateBlock", { block_id: block.block_id, content: newContent })
  }
  editingBlockId.value = null
  const target = props.blocks[toIndex]
  if (target && target.block_type !== "divider" && target.block_type !== "page") {
    nextTick(() => startEditing(target, toIndex))
  }
}

function autoResize(event: Event) {
  const el = event.target as HTMLTextAreaElement
  autoResizeElement(el)
}

function autoResizeElement(el: HTMLTextAreaElement) {
  el.style.height = "auto"
  el.style.height = el.scrollHeight + "px"
}

function handleKeydown(event: KeyboardEvent, block: Block, index: number) {
  const ta = event.target as HTMLTextAreaElement

  if (event.key === "Enter" && !event.shiftKey) {
    // Create new block below
    event.preventDefault()

    // If cursor is at the end, create empty block below
    // If cursor is in the middle, split the block
    const cursorPos = ta.selectionStart
    const content = editContent.value
    const beforeCursor = content.substring(0, cursorPos)
    const afterCursor = content.substring(cursorPos)

    if (afterCursor.trim()) {
      // Split: update current block with content before cursor
      editContent.value = beforeCursor
      finishEditing(block)
      // Create new block with content after cursor
      pendingFocusIndex.value = index + 1
      emit("addBlock", "text", afterCursor.trimStart(), index + 1)
    } else {
      // Just create a new empty block below
      finishEditing(block)
      pendingFocusIndex.value = index + 1
      emit("addBlock", "text", "", index + 1)
    }
  } else if (event.key === "Backspace" && ta.selectionStart === 0 && ta.selectionEnd === 0) {
    // Backspace at start of empty block: delete block and focus previous
    if (!editContent.value) {
      event.preventDefault()
      editingBlockId.value = null
      emit("deleteBlock", block.block_id)
      // Focus previous block
      if (index > 0) {
        const prevBlock = props.blocks[index - 1]
        if (prevBlock && prevBlock.block_type !== "divider" && prevBlock.block_type !== "page") {
          nextTick(() => startEditing(prevBlock, index - 1))
        }
      }
    }
  } else if (event.key === "ArrowUp" && ta.selectionStart === 0) {
    // Save current block and move to previous
    event.preventDefault()
    saveAndNavigate(block, index, index - 1)
  } else if (event.key === "ArrowDown" && ta.selectionStart === ta.value.length) {
    // Save current block and move to next
    event.preventDefault()
    saveAndNavigate(block, index, index + 1)
  } else if (event.key === "Escape") {
    editingBlockId.value = null
    editContent.value = ""
  }
}

function handleEditorClick(event: Event) {
  // Close type menu when clicking outside
  const target = event.target as HTMLElement
  if (!target.closest(".type-menu") && !target.closest(".gutter-drag")) {
    typeMenuIndex.value = null
  }
}

function handleBlockMouseLeave(index: number) {
  if (typeMenuIndex.value !== index) {
    hoveredIndex.value = null
  }
}

function toggleTypeMenu(index: number) {
  typeMenuIndex.value = typeMenuIndex.value === index ? null : index
}

function changeBlockType(block: Block, newType: string, defaultContent: string) {
  typeMenuIndex.value = null

  // Image/file upload triggers file picker instead of changing type
  if (newType === "image-upload" || newType === "file-upload") {
    const idx = props.blocks.indexOf(block)
    triggerFileUpload(idx >= 0 ? idx + 1 : undefined)
    return
  }

  if (block.block_type === newType) return

  // For divider, just update with divider content
  const content = newType === "divider" ? "---" : (block.content || defaultContent)
  emit("updateBlock", { block_id: block.block_id, content, block_type: newType })
}

function insertBlockAt(index: number) {
  pendingFocusIndex.value = index
  emit("addBlock", "text", "", index)
}

function addBlockAtEnd() {
  pendingFocusIndex.value = props.blocks.length
  emit("addBlock", "text", "")
}

// Link click handling in rendered blocks
async function handleRenderedBlockClick(event: MouseEvent, block: Block, index: number) {
  const target = event.target as HTMLElement
  const anchor = target.closest("a")
  if (anchor) {
    event.preventDefault()
    const internalLink = anchor.getAttribute("data-internal-link")
    if (internalLink && props.workspaceId && props.notebookId) {
      // Internal link: resolve and navigate
      try {
        const resolved = await blockService.resolveLink(
          internalLink,
          props.notebookId,
          props.workspaceId,
        )
        if (resolved) {
          emit("navigatePage", resolved as unknown as Block)
        }
      } catch {
        // If resolution fails, open the resolved href as fallback
        const href = anchor.getAttribute("href")
        if (href) window.open(href, "_blank")
      }
    } else {
      // External link: open in new tab
      const href = anchor.getAttribute("href")
      if (href) window.open(href, "_blank")
    }
    return
  }
  // No link clicked: enter edit mode
  startEditing(block, index)
}

// File upload (images and other binary files)
function triggerFileUpload(position?: number) {
  pendingFilePosition.value = position
  fileInputRef.value?.click()
}

function handleFileSelected(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (file) {
    const parentBlockId = props.blocks[0]?.parent_block_id || undefined
    emit("uploadFile", file, parentBlockId, pendingFilePosition.value)
  }
  // Reset input so the same file can be selected again
  input.value = ""
  pendingFilePosition.value = undefined
}

function handleBlockPaste(event: ClipboardEvent, _block: Block, index: number) {
  const items = event.clipboardData?.items
  if (!items) return
  for (const item of items) {
    if (item.kind === "file") {
      event.preventDefault()
      const file = item.getAsFile()
      if (file) {
        const parentBlockId = props.blocks[0]?.parent_block_id || undefined
        emit("uploadFile", file, parentBlockId, index + 1)
      }
      return
    }
  }
}

// Drag and drop
function onDragStart(event: DragEvent, index: number) {
  dragIndex.value = index
  if (event.dataTransfer) {
    event.dataTransfer.effectAllowed = "move"
    event.dataTransfer.setData("text/plain", String(index))
  }
}

function onDragOver(event: DragEvent, index: number) {
  if (dragIndex.value === null || dragIndex.value === index) return
  event.preventDefault()
  const rect = (event.currentTarget as HTMLElement).getBoundingClientRect()
  const midY = rect.top + rect.height / 2
  dragPosition.value = event.clientY < midY ? "top" : "bottom"
  dragOverIndex.value = index
}

function onDrop(_event: DragEvent, targetIndex: number) {
  const sourceIndex = dragIndex.value
  if (sourceIndex === null || sourceIndex === targetIndex) return

  const newOrder = [...props.blocks]
  const [moved] = newOrder.splice(sourceIndex, 1)
  if (moved) {
    const insertAt = dragPosition.value === "top" ? targetIndex : targetIndex
    newOrder.splice(insertAt, 0, moved)
    emit("reorder", newOrder.map((b) => b.block_id))
  }
  dragIndex.value = null
  dragOverIndex.value = null
}

function onDragEnd() {
  dragIndex.value = null
  dragOverIndex.value = null
}

// File drop upload
const dropActive = ref(false)
let dragEnterCount = 0

function hasFiles(event: DragEvent): boolean {
  return event.dataTransfer?.types?.includes("Files") ?? false
}

function onFileDragOver(event: DragEvent) {
  if (!hasFiles(event)) return
  if (event.dataTransfer) event.dataTransfer.dropEffect = "copy"
}

function onFileDragEnter(event: DragEvent) {
  if (!hasFiles(event)) return
  dragEnterCount++
  dropActive.value = true
}

function onFileDragLeave() {
  dragEnterCount--
  if (dragEnterCount <= 0) {
    dropActive.value = false
    dragEnterCount = 0
  }
}

function onFileDrop(event: DragEvent) {
  dropActive.value = false
  dragEnterCount = 0
  const files = event.dataTransfer?.files
  if (!files || files.length === 0) return
  const parentBlockId = props.blocks[0]?.parent_block_id || undefined
  for (const file of Array.from(files)) {
    emit("uploadFile", file, parentBlockId)
  }
}
</script>

<style scoped>
.block-editor {
  width: 100%;
  max-width: 900px;
  margin: 0 auto;
  padding: 1.5rem 2rem;
  min-height: 100%;
  transition: outline 0.15s ease;
}

.block-editor.drop-active {
  outline: 2px dashed var(--pen-blue, #3b82f6);
  outline-offset: -4px;
  background: color-mix(in srgb, var(--pen-blue, #3b82f6) 5%, transparent);
}

.page-header {
  margin-bottom: 1.5rem;
  padding-bottom: 1rem;
}

.page-header-row {
  display: flex;
  align-items: baseline;
  gap: 1rem;
}

.page-title {
  font-size: 2.25rem;
  font-weight: 700;
  margin: 0 0 0.25rem;
  color: var(--text-primary, #1a1a1a);
  line-height: 1.2;
}

.new-page-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  border: 1px solid var(--border-color, #e0e0e0);
  border-radius: 5px;
  background: transparent;
  color: var(--text-secondary, #666);
  font-size: 0.8125rem;
  cursor: pointer;
  white-space: nowrap;
  transition: background-color 0.15s, color 0.15s;
}

.new-page-btn:hover {
  background: var(--hover-bg, #f5f5f5);
  color: var(--text-primary, #333);
}

.page-description {
  color: var(--text-secondary, #666);
  margin: 0;
  font-size: 1rem;
}

/* Block wrapper */
.block-wrapper {
  position: relative;
  display: flex;
  align-items: flex-start;
  width: 100%;
  min-height: 1.5rem;
  border-radius: 4px;
  transition: background-color 0.1s;
}

.block-wrapper:hover {
  background-color: transparent;
}

.block-wrapper.drag-over-top {
  border-top: 2px solid var(--accent-color, #2563eb);
}

.block-wrapper.drag-over-bottom {
  border-bottom: 2px solid var(--accent-color, #2563eb);
}

.block-wrapper.is-dragging {
  opacity: 0.4;
}

/* Gutter */
.block-gutter {
  position: absolute;
  left: -52px;
  top: 0;
  display: flex;
  gap: 2px;
  opacity: 0;
  transition: opacity 0.15s;
  padding-top: 2px;
}

.block-gutter.visible {
  opacity: 1;
}

.gutter-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border: none;
  background: transparent;
  color: var(--text-tertiary, #999);
  cursor: pointer;
  border-radius: 3px;
  padding: 0;
}

.gutter-btn:hover {
  background: var(--hover-bg, #f0f0f0);
  color: var(--text-secondary, #666);
}

.gutter-drag {
  cursor: grab;
}

.gutter-drag:active {
  cursor: grabbing;
}

/* Type menu */
.type-menu {
  position: absolute;
  left: -52px;
  top: 26px;
  z-index: 50;
  background: var(--bg-primary, #fff);
  border: 1px solid var(--border-color, #e0e0e0);
  border-radius: 8px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
  padding: 4px;
  min-width: 140px;
}

.type-menu-item {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 6px 10px;
  border: none;
  background: transparent;
  color: var(--text-primary, #333);
  cursor: pointer;
  border-radius: 4px;
  font-size: 0.8125rem;
  text-align: left;
}

.type-menu-item:hover {
  background: var(--hover-bg, #f5f5f5);
}

.type-menu-item.active {
  background: var(--accent-color, #2563eb);
  color: white;
}

.type-menu-delete {
  color: var(--danger-color, #e74c3c);
}

.type-menu-delete:hover {
  background: rgba(231, 76, 60, 0.1);
}

.type-menu-divider {
  height: 1px;
  background: var(--border-color, #e0e0e0);
  margin: 4px 0;
}

.type-menu-section-label {
  padding: 4px 10px 2px;
  font-size: 0.6875rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--text-tertiary, #999);
}

.type-icon {
  font-weight: 600;
  font-size: 0.75rem;
  width: 18px;
  text-align: center;
  flex-shrink: 0;
}

/* Drop zone */
.block-drop-zone {
  flex: 1;
  min-width: 0;
}

/* Block content */
.block-content {
  width: 100%;
}

/* Textarea - seamless editing */
.block-textarea {
  width: 100%;
  min-height: 1.5em;
  padding: 3px 2px;
  border: none;
  border-radius: 3px;
  background: transparent;
  color: var(--text-primary, #333);
  font-family: inherit;
  font-size: 1rem;
  line-height: 1.6;
  resize: none;
  outline: none;
  overflow: hidden;
  display: block;
}

.block-textarea:focus {
  background: var(--bg-secondary, #fafafa);
  box-shadow: inset 0 0 0 1px var(--border-color, #e0e0e0);
}

.block-textarea.is-empty::placeholder {
  color: var(--text-tertiary, #bbb);
}

/* Type-specific textarea styles */
.textarea-heading {
  font-size: 1.5rem;
  font-weight: 600;
  line-height: 1.3;
}

.textarea-code {
  font-family: "SF Mono", "Fira Code", "Cascadia Code", monospace;
  font-size: 0.875rem;
  background: var(--bg-secondary, #f5f5f5);
  padding: 8px 12px;
  border-radius: 6px;
  line-height: 1.5;
}

/* Rendered block */
.block-rendered {
  padding: 3px 2px;
  cursor: text;
  min-height: 1.5em;
  border-radius: 3px;
  transition: background-color 0.1s;
}

.block-rendered:hover {
  background: var(--hover-bg, rgba(0, 0, 0, 0.03));
}

.block-rendered.is-empty {
  color: var(--text-tertiary, #bbb);
}

.block-placeholder-text {
  font-style: normal;
  user-select: none;
}

/* Block type styling */
.block-content :deep(h1),
.block-content :deep(h2),
.block-content :deep(h3),
.block-content :deep(h4),
.block-content :deep(h5),
.block-content :deep(h6) {
  margin: 0;
  line-height: 1.3;
}

.block-content :deep(h1) { font-size: 2rem; }
.block-content :deep(h2) { font-size: 1.5rem; }
.block-content :deep(h3) { font-size: 1.25rem; }

.block-content :deep(p) {
  margin: 0;
  line-height: 1.6;
}

.block-content :deep(pre) {
  margin: 0;
  border-radius: 6px;
  background: var(--bg-secondary, #f5f5f5);
  padding: 12px 16px;
  font-size: 0.875rem;
  overflow-x: auto;
}

.block-content :deep(code) {
  font-family: "SF Mono", "Fira Code", "Cascadia Code", monospace;
}

.block-content :deep(blockquote) {
  margin: 0;
  padding-left: 1rem;
  border-left: 3px solid var(--accent-color, #2563eb);
  color: var(--text-secondary, #555);
}

.block-content :deep(ul),
.block-content :deep(ol) {
  margin: 0;
  padding-left: 1.5rem;
}

.block-content :deep(li) {
  line-height: 1.6;
}

.block-content :deep(img) {
  max-width: 100%;
  border-radius: 6px;
}

/* Image block */
.block-image {
  border-radius: 6px;
  overflow: hidden;
}

.block-image img {
  max-width: 100%;
  display: block;
  border-radius: 6px;
}

.block-image-caption {
  font-size: 0.75rem;
  color: var(--text-tertiary, #999);
  margin-top: 4px;
}

/* File block */
.block-file-link {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  border: 1px solid var(--border-color, #e0e0e0);
  border-radius: 6px;
  color: var(--text-primary, #333);
  text-decoration: none;
  transition: background-color 0.1s;
}

.block-file-link:hover {
  background: var(--hover-bg, #f5f5f5);
}

.file-icon {
  font-size: 1.2rem;
}

.file-name {
  font-weight: 500;
  font-size: 0.875rem;
}

/* Divider */
.block-divider {
  border: none;
  border-top: 1px solid var(--border-color, #e0e0e0);
  margin: 8px 0;
}

/* Page link */
.block-page-link {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: 6px;
  cursor: pointer;
  color: var(--text-primary, #333);
  transition: background-color 0.1s;
}

.block-page-link:hover {
  background: var(--hover-bg, #f5f5f5);
}

.page-icon {
  font-size: 1.1rem;
}

.page-name {
  font-weight: 500;
}

/* Trailing area */
.block-trailing-area {
  min-height: 200px;
  cursor: text;
  padding: 8px 2px;
}

.trailing-hint {
  color: var(--text-tertiary, #ccc);
  font-size: 1rem;
  user-select: none;
}

.block-trailing-area:hover .trailing-hint {
  color: var(--text-secondary, #999);
}
</style>
