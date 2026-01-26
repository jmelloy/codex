<template>
  <div class="folder-view">
    <!-- Folder Header -->
    <div class="folder-header">
      <div class="folder-icon">
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="48"
          height="48"
          viewBox="0 0 24 24"
          fill="currentColor"
        >
          <path
            d="M10 4H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2h-8l-2-2z"
          />
        </svg>
      </div>
      <div class="folder-info">
        <h1 class="folder-title">{{ displayTitle }}</h1>
        <p v-if="folder.description || folder.properties?.description" class="folder-description">
          {{ folder.description || folder.properties?.description }}
        </p>
        <div class="folder-meta">
          <span class="meta-item">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
            >
              <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z" />
              <polyline points="13 2 13 9 20 9" />
            </svg>
            {{ folder.file_count }} items
          </span>
          <span class="meta-item">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
            >
              <path
                d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"
              />
            </svg>
            {{ folder.path }}
          </span>
        </div>
      </div>
      <div class="folder-actions">
        <button @click="$emit('toggleProperties')" class="properties-btn">Properties</button>
      </div>
    </div>

    <!-- View Mode Selector -->
    <div class="view-controls">
      <div class="view-mode-selector">
        <button
          @click="viewMode = 'grid'"
          :class="['view-mode-btn', { active: viewMode === 'grid' }]"
          title="Grid view"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
          >
            <rect x="3" y="3" width="7" height="7" />
            <rect x="14" y="3" width="7" height="7" />
            <rect x="14" y="14" width="7" height="7" />
            <rect x="3" y="14" width="7" height="7" />
          </svg>
        </button>
        <button
          @click="viewMode = 'list'"
          :class="['view-mode-btn', { active: viewMode === 'list' }]"
          title="List view"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
          >
            <line x1="8" y1="6" x2="21" y2="6" />
            <line x1="8" y1="12" x2="21" y2="12" />
            <line x1="8" y1="18" x2="21" y2="18" />
            <line x1="3" y1="6" x2="3.01" y2="6" />
            <line x1="3" y1="12" x2="3.01" y2="12" />
            <line x1="3" y1="18" x2="3.01" y2="18" />
          </svg>
        </button>
        <button
          @click="viewMode = 'compact'"
          :class="['view-mode-btn', { active: viewMode === 'compact' }]"
          title="Compact view"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
          >
            <line x1="3" y1="12" x2="21" y2="12" />
            <line x1="3" y1="6" x2="21" y2="6" />
            <line x1="3" y1="18" x2="21" y2="18" />
          </svg>
        </button>
      </div>
      <div class="sort-controls">
        <select v-model="sortBy" class="sort-select">
          <option value="name">Name</option>
          <option value="date">Date Modified</option>
          <option value="type">Type</option>
          <option value="size">Size</option>
        </select>
        <button
          @click="sortAsc = !sortAsc"
          class="sort-direction-btn"
          :title="sortAsc ? 'Ascending' : 'Descending'"
        >
          <svg
            v-if="sortAsc"
            xmlns="http://www.w3.org/2000/svg"
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
          >
            <polyline points="18 15 12 9 6 15" />
          </svg>
          <svg
            v-else
            xmlns="http://www.w3.org/2000/svg"
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
          >
            <polyline points="6 9 12 15 18 9" />
          </svg>
        </button>
      </div>
    </div>

    <!-- Files Grid/List -->
    <div v-if="sortedFiles.length > 0" :class="['files-container', viewMode]">
      <!-- Grid View -->
      <template v-if="viewMode === 'grid'">
        <div
          v-for="file in sortedFiles"
          :key="file.id"
          class="file-card"
          @click="$emit('selectFile', file)"
        >
          <div class="file-card-icon">
            <component :is="getFileIcon(file.file_type)" />
          </div>
          <div class="file-card-info">
            <span class="file-card-name">{{
              file.properties?.title || file.title || file.filename
            }}</span>
            <span class="file-card-meta">{{ formatSize(file.size) }}</span>
          </div>
        </div>
      </template>

      <!-- List View -->
      <template v-else-if="viewMode === 'list'">
        <div
          v-for="file in sortedFiles"
          :key="file.id"
          class="file-row"
          @click="$emit('selectFile', file)"
        >
          <div class="file-row-icon">
            <component :is="getFileIcon(file.file_type)" />
          </div>
          <div class="file-row-name">
            {{ file.properties?.title || file.title || file.filename }}
          </div>
          <div class="file-row-type">{{ file.file_type }}</div>
          <div class="file-row-size">{{ formatSize(file.size) }}</div>
          <div class="file-row-date">{{ formatDate(file.updated_at) }}</div>
        </div>
      </template>

      <!-- Compact View -->
      <template v-else>
        <div
          v-for="file in sortedFiles"
          :key="file.id"
          class="file-compact"
          @click="$emit('selectFile', file)"
        >
          <component :is="getFileIcon(file.file_type)" class="file-compact-icon" />
          <span class="file-compact-name">{{
            file.properties?.title || file.title || file.filename
          }}</span>
        </div>
      </template>
    </div>

    <!-- Empty State -->
    <div v-else class="empty-state">
      <svg
        xmlns="http://www.w3.org/2000/svg"
        width="64"
        height="64"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="1"
      >
        <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
      </svg>
      <p>This folder is empty</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, h } from "vue"
import type { FolderWithFiles, FileMetadata } from "../services/codex"

interface Props {
  folder: FolderWithFiles
}

const props = defineProps<Props>()

defineEmits<{
  selectFile: [file: FileMetadata]
  toggleProperties: []
}>()

const viewMode = ref<"grid" | "list" | "compact">("grid")
const sortBy = ref<"name" | "date" | "type" | "size">("name")
const sortAsc = ref(true)

const displayTitle = computed(() => {
  return props.folder.properties?.title || props.folder.title || props.folder.name
})

const sortedFiles = computed(() => {
  const files = [...props.folder.files]

  files.sort((a, b) => {
    let comparison = 0

    switch (sortBy.value) {
      case "name":
        const nameA = a.properties?.title || a.title || a.filename
        const nameB = b.properties?.title || b.title || b.filename
        comparison = nameA.localeCompare(nameB)
        break
      case "date":
        comparison = new Date(a.updated_at).getTime() - new Date(b.updated_at).getTime()
        break
      case "type":
        comparison = a.file_type.localeCompare(b.file_type)
        break
      case "size":
        comparison = a.size - b.size
        break
    }

    return sortAsc.value ? comparison : -comparison
  })

  return files
})

function formatSize(bytes: number): string {
  if (bytes === 0) return "0 B"
  const k = 1024
  const sizes = ["B", "KB", "MB", "GB"]
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i]
}

function formatDate(dateStr: string): string {
  try {
    const date = new Date(dateStr)
    return date.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    })
  } catch {
    return dateStr
  }
}

function getFileIcon(fileType: string) {
  const iconProps = {
    width: 24,
    height: 24,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    "stroke-width": 2,
  }

  switch (fileType) {
    case "markdown":
    case "text":
      return () =>
        h("svg", iconProps, [
          h("path", {
            d: "M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z",
          }),
          h("polyline", { points: "14 2 14 8 20 8" }),
          h("line", { x1: "16", y1: "13", x2: "8", y2: "13" }),
          h("line", { x1: "16", y1: "17", x2: "8", y2: "17" }),
          h("polyline", { points: "10 9 9 9 8 9" }),
        ])
    case "image":
      return () =>
        h("svg", iconProps, [
          h("rect", {
            x: "3",
            y: "3",
            width: "18",
            height: "18",
            rx: "2",
            ry: "2",
          }),
          h("circle", { cx: "8.5", cy: "8.5", r: "1.5" }),
          h("polyline", { points: "21 15 16 10 5 21" }),
        ])
    case "pdf":
      return () =>
        h("svg", iconProps, [
          h("path", {
            d: "M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z",
          }),
          h("polyline", { points: "14 2 14 8 20 8" }),
          h("path", { d: "M10 12h4" }),
          h("path", { d: "M10 16h4" }),
        ])
    case "audio":
      return () =>
        h("svg", iconProps, [
          h("path", { d: "M9 18V5l12-2v13" }),
          h("circle", { cx: "6", cy: "18", r: "3" }),
          h("circle", { cx: "18", cy: "16", r: "3" }),
        ])
    case "video":
      return () =>
        h("svg", iconProps, [
          h("polygon", { points: "23 7 16 12 23 17 23 7" }),
          h("rect", {
            x: "1",
            y: "5",
            width: "15",
            height: "14",
            rx: "2",
            ry: "2",
          }),
        ])
    case "code":
      return () =>
        h("svg", iconProps, [
          h("polyline", { points: "16 18 22 12 16 6" }),
          h("polyline", { points: "8 6 2 12 8 18" }),
        ])
    case "json":
      return () =>
        h("svg", iconProps, [
          h("path", {
            d: "M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z",
          }),
          h("polyline", { points: "14 2 14 8 20 8" }),
          h("path", { d: "M8 13h2" }),
          h("path", { d: "M8 17h2" }),
          h("path", { d: "M14 13h2" }),
          h("path", { d: "M14 17h2" }),
        ])
    default:
      return () =>
        h("svg", iconProps, [
          h("path", {
            d: "M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z",
          }),
          h("polyline", { points: "14 2 14 8 20 8" }),
        ])
  }
}
</script>

<style scoped>
.folder-view {
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: var(--color-bg-primary);
}

.folder-header {
  display: flex;
  align-items: flex-start;
  gap: var(--spacing-xl);
  padding: var(--spacing-xl);
  border-bottom: 1px solid var(--color-border-light);
  background: var(--color-bg-secondary);
}

.folder-icon {
  color: var(--color-primary);
  flex-shrink: 0;
}

.folder-info {
  flex: 1;
  min-width: 0;
}

.folder-actions {
  flex-shrink: 0;
}

.properties-btn {
  padding: var(--spacing-sm) var(--spacing-lg);
  background: var(--color-bg-secondary);
  color: var(--color-text-primary);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-sm);
  font-size: var(--text-sm);
  cursor: pointer;
  transition: all 0.2s;
}

.properties-btn:hover {
  background: var(--color-bg-tertiary);
  border-color: var(--color-border);
}

.folder-title {
  margin: 0 0 var(--spacing-sm);
  font-size: var(--text-2xl);
  font-weight: var(--font-semibold);
  color: var(--color-text-primary);
}

.folder-description {
  margin: 0 0 var(--spacing-md);
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
  line-height: 1.5;
}

.folder-meta {
  display: flex;
  gap: var(--spacing-lg);
  flex-wrap: wrap;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
}

.view-controls {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-md) var(--spacing-xl);
  border-bottom: 1px solid var(--color-border-light);
  background: var(--color-bg-primary);
}

.view-mode-selector {
  display: flex;
  gap: var(--spacing-xs);
}

.view-mode-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  background: none;
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-sm);
  color: var(--color-text-tertiary);
  cursor: pointer;
  transition: all 0.2s;
}

.view-mode-btn:hover {
  color: var(--color-text-primary);
  border-color: var(--color-border);
}

.view-mode-btn.active {
  color: var(--color-primary);
  border-color: var(--color-primary);
  background: color-mix(in srgb, var(--color-primary) 10%, transparent);
}

.sort-controls {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.sort-select {
  padding: var(--spacing-sm) var(--spacing-md);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-sm);
  background: var(--color-bg-primary);
  color: var(--color-text-primary);
  font-size: var(--text-sm);
  cursor: pointer;
}

.sort-select:focus {
  outline: none;
  border-color: var(--color-border-focus);
}

.sort-direction-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  background: none;
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-sm);
  color: var(--color-text-tertiary);
  cursor: pointer;
  transition: all 0.2s;
}

.sort-direction-btn:hover {
  color: var(--color-text-primary);
  border-color: var(--color-border);
}

.files-container {
  flex: 1;
  overflow-y: auto;
  padding: var(--spacing-xl);
}

/* Grid View */
.files-container.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: var(--spacing-lg);
  align-content: start;
}

.file-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: var(--spacing-lg);
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all 0.2s;
}

.file-card:hover {
  border-color: var(--color-primary);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.file-card-icon {
  color: var(--color-text-tertiary);
  margin-bottom: var(--spacing-md);
}

.file-card-info {
  text-align: center;
  width: 100%;
}

.file-card-name {
  display: block;
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--color-text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-card-meta {
  display: block;
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
  margin-top: var(--spacing-xs);
}

/* List View */
.files-container.list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.file-row {
  display: grid;
  grid-template-columns: 32px 1fr 100px 80px 120px;
  align-items: center;
  gap: var(--spacing-md);
  padding: var(--spacing-sm) var(--spacing-md);
  background: var(--color-bg-primary);
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all 0.2s;
}

.file-row:hover {
  background: var(--color-bg-secondary);
  border-color: var(--color-border-light);
}

.file-row-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-text-tertiary);
}

.file-row-name {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--color-text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-row-type,
.file-row-size,
.file-row-date {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
}

.file-row-type {
  text-transform: uppercase;
}

/* Compact View */
.files-container.compact {
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-sm);
  align-content: start;
}

.file-compact {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-xs) var(--spacing-md);
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all 0.2s;
}

.file-compact:hover {
  border-color: var(--color-primary);
}

.file-compact-icon {
  width: 16px;
  height: 16px;
  color: var(--color-text-tertiary);
}

.file-compact-name {
  font-size: var(--text-sm);
  color: var(--color-text-primary);
  white-space: nowrap;
}

/* Empty State */
.empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: var(--color-text-placeholder);
  gap: var(--spacing-md);
}

.empty-state p {
  font-size: var(--text-sm);
}
</style>
