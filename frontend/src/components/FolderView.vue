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
            {{ totalItemCount }} items
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
        <button
          @click="viewMode = 'rendered'"
          :class="['view-mode-btn', { active: viewMode === 'rendered' }]"
          title="Rendered view"
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
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <polyline points="14 2 14 8 20 8" />
            <line x1="16" y1="13" x2="8" y2="13" />
            <line x1="16" y1="17" x2="8" y2="17" />
            <polyline points="10 9 9 9 8 9" />
          </svg>
        </button>
      </div>
      <div v-if="viewMode !== 'rendered'" class="sort-controls">
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

    <!-- Rendered View Mode -->
    <div v-if="viewMode === 'rendered'" class="rendered-container">
      <div v-if="loadingContent" class="rendered-loading">
        Loading content...
      </div>
      <template v-else>
        <div
          v-for="file in sortedFiles"
          :key="file.id"
          class="rendered-block"
        >
          <!-- Markdown -->
          <div v-if="getBlockDisplayType(file) === 'markdown'" class="rendered-content rendered-markdown">
            <MarkdownViewer
              v-if="renderedContents.get(file.id) != null"
              :content="renderedContents.get(file.id)!"
              :frontmatter="file.properties"
              :workspace-id="workspaceStore.currentWorkspace?.id ?? 0"
              :notebook-id="folder.notebook_id"
              :current-file-path="file.path"
              :show-frontmatter="false"
              :show-toolbar="false"
            />
            <div v-else class="rendered-placeholder" @click="$emit('selectFile', file)">
              {{ file.filename }}
            </div>
          </div>

          <!-- Image -->
          <div v-else-if="getBlockDisplayType(file) === 'image'" class="rendered-content rendered-image">
            <img
              :src="getContentUrl(file)"
              :alt="file.title || file.filename"
              loading="lazy"
            />
          </div>

          <!-- Code -->
          <div v-else-if="getBlockDisplayType(file) === 'code' || getBlockDisplayType(file) === 'json'" class="rendered-content rendered-code">
            <div class="code-header">{{ file.filename }}</div>
            <CodeViewer
              v-if="renderedContents.get(file.id) != null"
              :content="renderedContents.get(file.id)!"
              :filename="file.filename"
              :show-line-numbers="true"
              :show-toolbar="false"
            />
            <div v-else class="rendered-placeholder" @click="$emit('selectFile', file)">
              {{ file.filename }}
            </div>
          </div>

          <!-- Video -->
          <div v-else-if="getBlockDisplayType(file) === 'video'" class="rendered-content rendered-video">
            <video :src="getContentUrl(file)" controls class="rendered-media">
              Your browser does not support the video element.
            </video>
          </div>

          <!-- Audio -->
          <div v-else-if="getBlockDisplayType(file) === 'audio'" class="rendered-content rendered-audio">
            <audio :src="getContentUrl(file)" controls class="rendered-media-audio">
              Your browser does not support the audio element.
            </audio>
          </div>

          <!-- PDF -->
          <div v-else-if="getBlockDisplayType(file) === 'pdf'" class="rendered-content rendered-pdf">
            <iframe
              :src="getContentUrl(file)"
              class="pdf-frame"
              :title="file.title || file.filename"
            />
          </div>

          <!-- Other file types: clickable card -->
          <div v-else class="rendered-content rendered-file" @click="$emit('selectFile', file)">
            <div class="rendered-file-info">
              <span class="rendered-file-name">{{ file.filename }}</span>
              <span class="rendered-file-type">{{ file.content_type }}</span>
            </div>
          </div>
        </div>

        <div v-if="sortedFiles.length === 0" class="rendered-empty">
          <p>No files in this folder.</p>
        </div>
      </template>
    </div>

    <!-- Files Grid/List/Compact -->
    <template v-else>
      <div v-if="hasContent" :class="['files-container', viewMode]">
        <!-- Grid View -->
        <template v-if="viewMode === 'grid'">
          <!-- Subfolders -->
          <div
            v-for="subfolder in subfolders"
            :key="'folder-' + subfolder.path"
            class="file-card folder-card"
            @click="$emit('selectFolder', subfolder)"
          >
            <div class="file-card-icon folder-icon-color">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="24"
                height="24"
                viewBox="0 0 24 24"
                fill="currentColor"
              >
                <path
                  d="M10 4H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2h-8l-2-2z"
                />
              </svg>
            </div>
            <div class="file-card-info">
              <span class="file-card-name">{{
                subfolder.properties?.title || subfolder.title || subfolder.name
              }}</span>
              <span class="file-card-meta">Folder</span>
            </div>
          </div>
          <!-- Files -->
          <div
            v-for="file in sortedFiles"
            :key="file.id"
            class="file-card"
            :class="{ 'has-thumbnail': isImageFile(file) }"
            @click="$emit('selectFile', file)"
          >
            <div v-if="isImageFile(file)" class="file-card-thumbnail">
              <img
                :src="getThumbnailUrl(file)"
                :alt="file.properties?.title || file.title || file.filename"
                loading="lazy"
              />
            </div>
            <div v-else class="file-card-icon">
              <component :is="getFileIcon(file.content_type)" />
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
          <!-- Subfolders -->
          <div
            v-for="subfolder in subfolders"
            :key="'folder-' + subfolder.path"
            class="file-row folder-row"
            @click="$emit('selectFolder', subfolder)"
          >
            <div class="file-row-icon folder-icon-color">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="24"
                height="24"
                viewBox="0 0 24 24"
                fill="currentColor"
              >
                <path
                  d="M10 4H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2h-8l-2-2z"
                />
              </svg>
            </div>
            <div class="file-row-name">
              {{ subfolder.properties?.title || subfolder.title || subfolder.name }}
            </div>
            <div class="file-row-type">Folder</div>
            <div class="file-row-size">-</div>
            <div class="file-row-date">{{ formatDate(subfolder.updated_at || "") }}</div>
          </div>
          <!-- Files -->
          <div
            v-for="file in sortedFiles"
            :key="file.id"
            class="file-row"
            @click="$emit('selectFile', file)"
          >
            <div class="file-row-icon">
              <img
                v-if="isImageFile(file)"
                :src="getThumbnailUrl(file)"
                :alt="file.properties?.title || file.title || file.filename"
                class="file-row-thumbnail"
                loading="lazy"
              />
              <component v-else :is="getFileIcon(file.content_type)" />
            </div>
            <div class="file-row-name">
              {{ file.properties?.title || file.title || file.filename }}
            </div>
            <div class="file-row-type">{{ file.content_type }}</div>
            <div class="file-row-size">{{ formatSize(file.size) }}</div>
            <div class="file-row-date">{{ formatDate(file.updated_at) }}</div>
          </div>
        </template>

        <!-- Compact View -->
        <template v-else>
          <!-- Subfolders -->
          <div
            v-for="subfolder in subfolders"
            :key="'folder-' + subfolder.path"
            class="file-compact folder-compact"
            @click="$emit('selectFolder', subfolder)"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="currentColor"
              class="file-compact-icon folder-icon-color"
            >
              <path
                d="M10 4H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2h-8l-2-2z"
              />
            </svg>
            <span class="file-compact-name">{{
              subfolder.properties?.title || subfolder.title || subfolder.name
            }}</span>
          </div>
          <!-- Files -->
          <div
            v-for="file in sortedFiles"
            :key="file.id"
            class="file-compact"
            @click="$emit('selectFile', file)"
          >
            <img
              v-if="isImageFile(file)"
              :src="getThumbnailUrl(file)"
              :alt="file.properties?.title || file.title || file.filename"
              class="file-compact-thumbnail"
              loading="lazy"
            />
            <component v-else :is="getFileIcon(file.content_type)" class="file-compact-icon" />
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
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, h, watch } from "vue"
import type { FolderWithFiles, FileMetadata, SubfolderMetadata } from "../services/codex"
import { fileService } from "../services/codex"
import { getDisplayType, isTextType } from "../utils/contentType"
import { useWorkspaceStore } from "../stores/workspace"
import MarkdownViewer from "./MarkdownViewer.vue"
import CodeViewer from "./CodeViewer.vue"

type ViewMode = "grid" | "list" | "compact" | "rendered"
type SortField = "name" | "date" | "type" | "size"

interface Props {
  folder: FolderWithFiles
}

const props = defineProps<Props>()
const workspaceStore = useWorkspaceStore()

defineEmits<{
  selectFile: [file: FileMetadata]
  selectFolder: [folder: SubfolderMetadata]
  toggleProperties: []
}>()

// Initialize view/sort from folder properties, falling back to defaults
const viewMode = ref<ViewMode>(
  (props.folder.properties?.view_mode as ViewMode) || "grid"
)
const sortBy = ref<SortField>(
  (props.folder.properties?.sort_by as SortField) || "name"
)
const sortAsc = ref(
  (props.folder.properties?.sort_direction || "asc") === "asc"
)

// Sync settings when folder changes (user navigated to a different folder)
watch(
  () => props.folder.path,
  () => {
    viewMode.value = (props.folder.properties?.view_mode as ViewMode) || "grid"
    sortBy.value = (props.folder.properties?.sort_by as SortField) || "name"
    sortAsc.value = (props.folder.properties?.sort_direction || "asc") === "asc"
  },
)

// Also sync when folder properties are updated externally (e.g. from FolderPropertiesPanel)
watch(
  () => props.folder.properties,
  (newProps) => {
    if (newProps?.view_mode && newProps.view_mode !== viewMode.value) {
      viewMode.value = newProps.view_mode as ViewMode
    }
    if (newProps?.sort_by && newProps.sort_by !== sortBy.value) {
      sortBy.value = newProps.sort_by as SortField
    }
    if (newProps?.sort_direction) {
      const newAsc = newProps.sort_direction === "asc"
      if (newAsc !== sortAsc.value) {
        sortAsc.value = newAsc
      }
    }
  },
)

// --- Rendered view content loading ---
const loadingContent = ref(false)
const renderedContents = ref<Map<number, string>>(new Map())

function getBlockDisplayType(file: FileMetadata): string {
  return getDisplayType(file.content_type)
}

function getContentUrl(file: FileMetadata): string {
  return fileService.getContentUrl(file.id, workspaceStore.currentWorkspace?.id ?? 0, props.folder.notebook_id)
}

async function loadRenderedContents() {
  loadingContent.value = true
  const contents = new Map<number, string>()

  try {
    const textFiles = sortedFiles.value.filter((f) => isTextType(f.content_type))
    const promises = textFiles.map(async (file) => {
      try {
        const result = await fileService.getContent(
          file.id,
          workspaceStore.currentWorkspace?.id ?? 0,
          props.folder.notebook_id,
        )
        contents.set(file.id, result.content)
      } catch (e) {
        console.warn(`Failed to load content for ${file.path}:`, e)
      }
    })

    await Promise.all(promises)
    renderedContents.value = contents
  } finally {
    loadingContent.value = false
  }
}

// Load content when switching to rendered mode or when folder changes
watch(
  [() => viewMode.value, () => props.folder],
  ([mode]) => {
    if (mode === "rendered") {
      loadRenderedContents()
    } else {
      renderedContents.value = new Map()
    }
  },
  { immediate: true },
)

// --- Existing logic ---

function isImageFile(file: FileMetadata): boolean {
  return (
    file.content_type.startsWith("image/") ||
    /\.(jpg|jpeg|png|gif|bmp|webp|svg)$/i.test(file.filename)
  )
}

function getThumbnailUrl(file: FileMetadata): string {
  const workspaceId = workspaceStore.currentWorkspace?.id
  return `/api/v1/workspaces/${workspaceId}/notebooks/${props.folder.notebook_id}/files/${file.id}/content`
}

const displayTitle = computed(() => {
  return props.folder.properties?.title || props.folder.title || props.folder.name
})

const subfolders = computed(() => props.folder.subfolders || [])

const visibleFiles = computed(() => {
  return props.folder.files
})

const hasContent = computed(() => {
  return visibleFiles.value.length > 0 || subfolders.value.length > 0
})

const totalItemCount = computed(() => {
  return visibleFiles.value.length + subfolders.value.length
})

const sortedFiles = computed(() => {
  const files = [...visibleFiles.value]

  files.sort((a, b) => {
    let comparison = 0

    switch (sortBy.value) {
      case "name": {
        const nameA = a.properties?.title || a.title || a.filename
        const nameB = b.properties?.title || b.title || b.filename
        comparison = nameA.localeCompare(nameB)
        break
      }
      case "date":
        comparison = new Date(a.updated_at).getTime() - new Date(b.updated_at).getTime()
        break
      case "type":
        comparison = a.content_type.localeCompare(b.content_type)
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

function getFileIcon(contentType: string) {
  const displayType = getDisplayType(contentType)
  const iconProps = {
    width: 24,
    height: 24,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    "stroke-width": 2,
  }

  switch (displayType) {
    case "markdown":
    case "text":
      return () =>
        h("svg", iconProps, [
          h("path", { d: "M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" }),
          h("polyline", { points: "14 2 14 8 20 8" }),
          h("line", { x1: "16", y1: "13", x2: "8", y2: "13" }),
          h("line", { x1: "16", y1: "17", x2: "8", y2: "17" }),
          h("polyline", { points: "10 9 9 9 8 9" }),
        ])
    case "image":
      return () =>
        h("svg", iconProps, [
          h("rect", { x: "3", y: "3", width: "18", height: "18", rx: "2", ry: "2" }),
          h("circle", { cx: "8.5", cy: "8.5", r: "1.5" }),
          h("polyline", { points: "21 15 16 10 5 21" }),
        ])
    case "pdf":
      return () =>
        h("svg", iconProps, [
          h("path", { d: "M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" }),
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
          h("rect", { x: "1", y: "5", width: "15", height: "14", rx: "2", ry: "2" }),
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
          h("path", { d: "M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" }),
          h("polyline", { points: "14 2 14 8 20 8" }),
          h("path", { d: "M8 13h2" }),
          h("path", { d: "M8 17h2" }),
          h("path", { d: "M14 13h2" }),
          h("path", { d: "M14 17h2" }),
        ])
    default:
      return () =>
        h("svg", iconProps, [
          h("path", { d: "M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" }),
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

/* --- Rendered View --- */
.rendered-container {
  flex: 1 1 0;
  min-height: 0;
  overflow-y: auto;
  padding: var(--spacing-xl);
}

.rendered-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 3rem;
  color: var(--color-text-tertiary);
}

.rendered-block {
  /* Blocks flow seamlessly */
}

.rendered-content {
  /* Uniform block rendering */
}

.rendered-markdown {
  /* Markdown flows naturally */
}

.rendered-image img {
  max-width: 100%;
  height: auto;
  display: block;
  margin: 1rem 0;
  border-radius: var(--radius-sm);
}

.rendered-code {
  margin: 1rem 0;
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-sm);
  overflow: hidden;
}

.code-header {
  padding: 0.375rem 0.75rem;
  font-size: 0.75rem;
  color: var(--color-text-tertiary);
  background: var(--color-bg-secondary);
  border-bottom: 1px solid var(--color-border-light);
  font-family: monospace;
}

.rendered-video .rendered-media {
  max-width: 100%;
  max-height: 600px;
  display: block;
  margin: 1rem 0;
  border-radius: var(--radius-sm);
}

.rendered-audio .rendered-media-audio {
  width: 100%;
  margin: 1rem 0;
}

.rendered-pdf .pdf-frame {
  width: 100%;
  height: 600px;
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-sm);
  margin: 1rem 0;
}

.rendered-file {
  display: flex;
  align-items: center;
  padding: 0.75rem 1rem;
  margin: 0.5rem 0;
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: background 0.15s;
}

.rendered-file:hover {
  background: var(--color-bg-secondary);
}

.rendered-file-info {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.rendered-file-name {
  font-weight: 500;
  color: var(--color-text-primary);
}

.rendered-file-type {
  font-size: 0.8rem;
  color: var(--color-text-tertiary);
}

.rendered-placeholder {
  padding: 0.75rem 1rem;
  color: var(--color-text-tertiary);
  cursor: pointer;
  border: 1px dashed var(--color-border-light);
  border-radius: var(--radius-sm);
  margin: 0.5rem 0;
  transition: background 0.15s;
}

.rendered-placeholder:hover {
  background: var(--color-bg-secondary);
}

.rendered-empty {
  text-align: center;
  padding: 3rem;
  color: var(--color-text-tertiary);
}

/* --- Grid/List/Compact Views --- */
.files-container {
  flex: 1 1 0;
  min-height: 0;
  overflow-y: auto;
  padding: var(--spacing-xl);
}

/* Grid View */
.files-container.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
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

/* Folder Items */
.folder-icon-color {
  color: var(--color-primary);
}

.folder-card:hover,
.folder-row:hover,
.folder-compact:hover {
  border-color: var(--color-primary);
}

/* Thumbnail styles */
.file-card.has-thumbnail {
  padding: 0;
  overflow: hidden;
  min-height: fit-content;
}

.file-card.has-thumbnail .file-card-info {
  padding: var(--spacing-sm) var(--spacing-md);
}

.file-card-thumbnail {
  width: 100%;
  height: 140px;
  min-height: 140px;
  flex-shrink: 0;
  overflow: hidden;
  background: var(--color-bg-tertiary);
}

.file-card-thumbnail img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.2s;
}

.file-card:hover .file-card-thumbnail img {
  transform: scale(1.05);
}

.file-row-thumbnail {
  width: 24px;
  height: 24px;
  object-fit: cover;
  border-radius: var(--radius-xs);
}

.file-compact-thumbnail {
  width: 16px;
  height: 16px;
  object-fit: cover;
  border-radius: 2px;
  flex-shrink: 0;
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
