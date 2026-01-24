<template>
  <li v-if="node.type === 'folder'">
    <!-- Folder -->
    <div
      :class="['flex items-center py-2 cursor-pointer text-[13px] text-text-secondary transition hover:bg-bg-hover']"
      :style="{ paddingLeft: `${(depth + 1) * 16 + 32}px` }"
      @click="emit('toggleFolder', notebookId, node.path)"
    >
      <span class="text-[10px] mr-2 text-text-tertiary w-3">{{ isFolderExpanded ? '▼' : '▶' }}</span>
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
        @toggle-folder="(nid: number, path: string) => emit('toggleFolder', nid, path)"
        @select-file="(file: FileMetadata) => emit('selectFile', file)"
      />
    </ul>
  </li>

  <!-- File -->
  <li v-else>
    <div
      :class="['flex items-center py-2 cursor-pointer text-[13px] text-text-secondary transition hover:bg-bg-hover', { 'bg-bg-active text-primary font-medium': currentFileId === node.file?.id }]"
      :style="{ paddingLeft: `${(depth + 1) * 16 + 32}px` }"
      @click="node.file && emit('selectFile', node.file)"
    >
      <span class="mr-2 text-sm">{{ getFileIcon(node.file) }}</span>
      <span class="overflow-hidden text-ellipsis whitespace-nowrap">{{ node.file?.title || node.name }}</span>
    </div>
  </li>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { FileTreeNode } from '../utils/fileTree'
import type { FileMetadata } from '../services/codex'

interface Props {
  node: FileTreeNode
  notebookId: number
  depth: number
  expandedFolders: Map<number, Set<string>>
  currentFileId?: number
}

const props = defineProps<Props>()

const emit = defineEmits<{
  toggleFolder: [notebookId: number, path: string]
  selectFile: [file: FileMetadata]
}>()

const isFolderExpanded = computed(() => {
  if (props.node.type !== 'folder') return false
  return props.expandedFolders.get(props.notebookId)?.has(props.node.path) || false
})

const getFileIcon = (file: FileMetadata | undefined): string => {
  if (!file) return '📄'

  switch (file.file_type) {
    case 'view':
      return '📊' // Chart/view icon for .cdx files
    case 'markdown':
      return '📝' // Memo for markdown
    case 'json':
      return '📋' // Clipboard for JSON
    case 'xml':
      return '🏷️'  // Tag for XML
    case 'image':
      return '🖼️' // Picture for images
    case 'pdf':
      return '📕' // Book for PDF
    case 'audio':
      return '🎵' // Music note for audio
    case 'video':
      return '🎬' // Film for video
    case 'html':
      return '🌐' // Globe for HTML
    case 'text':
      return '📄' // Document for text
    case 'binary':
      return '📦' // Package for binary
    default:
      return '📄' // Default file icon
  }
}
</script>
