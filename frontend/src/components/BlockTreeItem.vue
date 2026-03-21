<template>
  <li v-if="node.type === 'page'">
    <!-- Page -->
    <div
      :class="[
        'flex items-center py-2 cursor-pointer text-[13px] text-text-secondary transition hover:bg-bg-hover',
        { 'bg-primary/20 border-t-2 border-primary': isDragOver },
        { 'bg-bg-active text-primary font-medium': isSelectedPage },
      ]"
      :style="{ paddingLeft: `${(depth + 1) * 16 + 32}px` }"
      @click="handlePageClick"
      @dragover.prevent="handleDragOver"
      @dragenter.prevent="handleDragEnter"
      @dragleave="handleDragLeave"
      @drop.prevent="handleDrop"
    >
      <span
        v-if="!node.isPage || hasSubpages"
        class="text-[10px] mr-2 text-text-tertiary w-3"
      >{{
        isPageExpanded ? "▼" : "▶"
      }}</span>
      <span v-else class="mr-2 w-3"></span>
      <span class="mr-2 text-sm">{{ node.isPage ? '📄' : '📁' }}</span>
      <span class="overflow-hidden text-ellipsis whitespace-nowrap">{{ node.pageMeta?.title || node.name }}</span>
    </div>

    <!-- Page contents -->
    <ul v-if="isPageExpanded && node.children" class="list-none p-0 m-0">
      <BlockTreeItem
        v-for="child in node.children"
        :key="child.path"
        :node="child"
        :notebook-id="notebookId"
        :depth="depth + 1"
        :expanded-pages="expandedPages"
        :current-block-id="currentBlockId"
        :current-page-path="currentPagePath"
        :current-page-notebook-id="currentPageNotebookId"
        @toggle-page="(nid: number, path: string) => emit('togglePage', nid, path)"
        @select-page="(nid: number, path: string) => emit('selectPage', nid, path)"
        @select-block="(block: Block) => emit('selectBlock', block)"
        @move-block="(blockId: string, targetPath: string) => emit('moveBlock', blockId, targetPath)"
      />
    </ul>
  </li>

  <!-- Leaf block -->
  <li v-else>
    <div
      :class="[
        'flex items-center py-2 cursor-grab text-[13px] text-text-secondary transition hover:bg-bg-hover',
        { 'bg-bg-active text-primary font-medium': currentBlockId === node.leafBlock?.id },
        { 'opacity-50': isDragging },
      ]"
      :style="{ paddingLeft: `${(depth + 1) * 16 + 32}px` }"
      draggable="true"
      @click="node.leafBlock && emit('selectBlock', node.leafBlock)"
      @dragstart="handleDragStart"
      @dragend="handleDragEnd"
    >
      <span class="mr-2 text-sm">{{ getBlockIcon(node.leafBlock) }}</span>
      <span class="overflow-hidden text-ellipsis whitespace-nowrap">{{
        node.leafBlock?.title || node.name
      }}</span>
    </div>
  </li>
</template>

<script setup lang="ts">
import { computed, ref } from "vue"
import type { BlockTreeNode } from "../utils/blockTree"
import type { Block } from "../services/codex"
import { getDisplayType } from "../utils/contentType"

interface Props {
  node: BlockTreeNode
  notebookId: number
  depth: number
  expandedPages: Map<number, Set<string>>
  currentBlockId?: number
  currentPagePath?: string
  currentPageNotebookId?: number
}

const props = defineProps<Props>()

const emit = defineEmits<{
  togglePage: [notebookId: number, path: string]
  selectPage: [notebookId: number, path: string]
  selectBlock: [block: Block]
  moveBlock: [blockId: string, targetPath: string]
}>()

const isDragging = ref(false)
const isDragOver = ref(false)

const isPageExpanded = computed(() => {
  if (props.node.type !== "page") return false
  return props.expandedPages.get(props.notebookId)?.has(props.node.path) || false
})

const hasSubpages = computed(() => {
  if (props.node.type !== "page") return false
  // Use API-provided flag, fall back to checking children
  if (props.node.hasSubpages !== undefined) return props.node.hasSubpages
  if (!props.node.children) return false
  return props.node.children.some((c) => c.type === "page" && c.isPage)
})

const isSelectedPage = computed(() => {
  if (props.node.type !== "page") return false
  return (
    props.currentPagePath === props.node.path &&
    props.currentPageNotebookId === props.notebookId
  )
})

const handlePageClick = async () => {
  // Pages without subpages: just select, don't toggle disclosure
  if (props.node.isPage && !hasSubpages.value) {
    emit("selectPage", props.notebookId, props.node.path)
    return
  }

  const wasExpanded = isPageExpanded.value

  if (wasExpanded) {
    // Just collapse
    emit("togglePage", props.notebookId, props.node.path)
  } else {
    // First select the page to load contents
    emit("selectPage", props.notebookId, props.node.path)
  }
}

// Drag handlers for leaf blocks
const handleDragStart = (event: DragEvent) => {
  if (!props.node.leafBlock || !event.dataTransfer) return
  isDragging.value = true
  event.dataTransfer.effectAllowed = "move"
  event.dataTransfer.setData(
    "application/x-codex-block",
    JSON.stringify({
      blockId: props.node.leafBlock.block_id,
      notebookId: props.notebookId,
      filename: props.node.leafBlock.filename || props.node.leafBlock.path.split("/").pop() || props.node.leafBlock.path,
      path: props.node.leafBlock.path,
    })
  )
}

const handleDragEnd = () => {
  isDragging.value = false
}

// Drag handlers for pages (drop targets)
const handleDragOver = (event: DragEvent) => {
  if (!event.dataTransfer) return
  if (event.dataTransfer.types.includes("application/x-codex-block")) {
    event.dataTransfer.dropEffect = "move"
  }
}

const handleDragEnter = (event: DragEvent) => {
  if (!event.dataTransfer) return
  if (event.dataTransfer.types.includes("application/x-codex-block")) {
    isDragOver.value = true
  }
}

const handleDragLeave = () => {
  isDragOver.value = false
}

const handleDrop = (event: DragEvent) => {
  isDragOver.value = false
  if (!event.dataTransfer) return

  const data = event.dataTransfer.getData("application/x-codex-block")
  if (!data) return

  try {
    const { blockId, filename } = JSON.parse(data)
    const newPath = props.node.path ? `${props.node.path}/${filename}` : filename
    emit("moveBlock", blockId, newPath)
  } catch (e) {
    console.error("Failed to parse drag data:", e)
  }
}

const getBlockIcon = (block: Block | undefined): string => {
  if (!block) return "📄"

  const displayType = getDisplayType(block.content_type || "")

  switch (displayType) {
    case "markdown":
      return "📝"
    case "json":
      return "📋"
    case "xml":
      return "🏷️"
    case "image":
      return "🖼️"
    case "pdf":
      return "📕"
    case "audio":
      return "🎵"
    case "video":
      return "🎬"
    case "html":
      return "🌐"
    case "text":
    case "code":
      return "📄"
    case "binary":
      return "📦"
    default:
      return "📄"
  }
}
</script>
