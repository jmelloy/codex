<template>
  <li v-if="node.type === 'folder'">
    <!-- Folder -->
    <div
      :class="[
        'flex items-center py-2 cursor-pointer text-[13px] text-text-secondary transition hover:bg-bg-hover',
        { 'bg-primary/20 border-t-2 border-primary': isDragOver },
        { 'bg-bg-active text-primary font-medium': isSelectedFolder },
      ]"
      :style="{ paddingLeft: `${(depth + 1) * 16 + 32}px` }"
      @click="handleFolderClick"
      @dragover.prevent="handleDragOver"
      @dragenter.prevent="handleDragEnter"
      @dragleave="handleDragLeave"
      @drop.prevent="handleDrop"
    >
      <span class="text-[10px] mr-2 text-text-tertiary w-3">{{
        isFolderExpanded ? "▼" : "▶"
      }}</span>
      <span class="mr-2 text-sm">📁</span>
      <span class="overflow-hidden text-ellipsis whitespace-nowrap">{{ node.name }}</span>
    </div>

    <!-- Folder contents -->
    <ul v-if="isFolderExpanded && node.children" class="list-none p-0 m-0">
      <FileTreeItem
        v-for="child in node.children"
        :key="child.path"
        :node="child"
        :notebook-id="notebookId"
        :depth="depth + 1"
        :expanded-folders="expandedFolders"
        :current-file-id="currentFileId"
        :current-folder-path="currentFolderPath"
        :current-folder-notebook-id="currentFolderNotebookId"
        @toggle-folder="(nid: number, path: string) => emit('toggleFolder', nid, path)"
        @select-folder="(nid: number, path: string) => emit('selectFolder', nid, path)"
        @select-file="(file: FileMetadata) => emit('selectFile', file)"
        @move-file="(fileId: number, targetPath: string) => emit('moveFile', fileId, targetPath)"
      />
    </ul>
  </li>

  <!-- File -->
  <li v-else>
    <div
      :class="[
        'flex items-center py-2 cursor-grab text-[13px] text-text-secondary transition hover:bg-bg-hover',
        {
          'bg-bg-active text-primary font-medium': currentFileId === node.file?.id,
        },
        { 'opacity-50': isDragging },
      ]"
      :style="{ paddingLeft: `${(depth + 1) * 16 + 32}px` }"
      draggable="true"
      @click="node.file && emit('selectFile', node.file)"
      @dragstart="handleDragStart"
      @dragend="handleDragEnd"
    >
      <span class="mr-2 text-sm">{{ getFileIcon(node.file) }}</span>
      <span class="overflow-hidden text-ellipsis whitespace-nowrap">{{
        node.file?.title || node.name
      }}</span>
    </div>
  </li>
</template>

<script setup lang="ts">
import { computed, ref } from "vue"
import type { FileTreeNode } from "../utils/fileTree"
import type { FileMetadata } from "../services/codex"

interface Props {
  node: FileTreeNode
  notebookId: number
  depth: number
  expandedFolders: Map<number, Set<string>>
  currentFileId?: number
  currentFolderPath?: string
  currentFolderNotebookId?: number
}

const props = defineProps<Props>()

const emit = defineEmits<{
  toggleFolder: [notebookId: number, path: string]
  selectFolder: [notebookId: number, path: string]
  selectFile: [file: FileMetadata]
  moveFile: [fileId: number, targetPath: string]
}>()

const isDragging = ref(false)
const isDragOver = ref(false)

const isFolderExpanded = computed(() => {
  if (props.node.type !== "folder") return false
  return props.expandedFolders.get(props.notebookId)?.has(props.node.path) || false
})

const isSelectedFolder = computed(() => {
  if (props.node.type !== "folder") return false
  return (
    props.currentFolderPath === props.node.path &&
    props.currentFolderNotebookId === props.notebookId
  )
})

const handleFolderClick = () => {
  // Toggle folder expansion
  emit("toggleFolder", props.notebookId, props.node.path)
  // Also select the folder to show folder view
  emit("selectFolder", props.notebookId, props.node.path)
}

// Drag handlers for files
const handleDragStart = (event: DragEvent) => {
  if (!props.node.file || !event.dataTransfer) return
  isDragging.value = true
  event.dataTransfer.effectAllowed = "move"
  event.dataTransfer.setData(
    "application/x-codex-file",
    JSON.stringify({
      fileId: props.node.file.id,
      notebookId: props.notebookId,
      filename: props.node.file.filename,
      path: props.node.file.path,
    })
  )
}

const handleDragEnd = () => {
  isDragging.value = false
}

// Drag handlers for folders (drop targets)
const handleDragOver = (event: DragEvent) => {
  if (!event.dataTransfer) return
  // Check if this is a file drag
  if (event.dataTransfer.types.includes("application/x-codex-file")) {
    event.dataTransfer.dropEffect = "move"
  }
}

const handleDragEnter = (event: DragEvent) => {
  if (!event.dataTransfer) return
  if (event.dataTransfer.types.includes("application/x-codex-file")) {
    isDragOver.value = true
  }
}

const handleDragLeave = () => {
  isDragOver.value = false
}

const handleDrop = (event: DragEvent) => {
  isDragOver.value = false
  if (!event.dataTransfer) return

  const data = event.dataTransfer.getData("application/x-codex-file")
  if (!data) return

  try {
    const { fileId, filename } = JSON.parse(data)
    // Calculate new path: folder path + filename
    const newPath = props.node.path ? `${props.node.path}/${filename}` : filename
    emit("moveFile", fileId, newPath)
  } catch (e) {
    console.error("Failed to parse drag data:", e)
  }
}

const getFileIcon = (file: FileMetadata | undefined): string => {
  if (!file) return "📄"

  switch (file.file_type) {
    case "view":
      return "📊" // Chart/view icon for .cdx files
    case "markdown":
      return "📝" // Memo for markdown
    case "json":
      return "📋" // Clipboard for JSON
    case "xml":
      return "🏷️" // Tag for XML
    case "image":
      return "🖼️" // Picture for images
    case "pdf":
      return "📕" // Book for PDF
    case "audio":
      return "🎵" // Music note for audio
    case "video":
      return "🎬" // Film for video
    case "html":
      return "🌐" // Globe for HTML
    case "text":
      return "📄" // Document for text
    case "binary":
      return "📦" // Package for binary
    default:
      return "📄" // Default file icon
  }
}
</script>
