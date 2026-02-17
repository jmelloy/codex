<template>
  <div class="page-unified-view">
    <!-- Page Header -->
    <div class="page-header">
      <div class="page-icon">
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="48"
          height="48"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="1.5"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
          <polyline points="14 2 14 8 20 8" />
          <line x1="16" y1="13" x2="8" y2="13" />
          <line x1="16" y1="17" x2="8" y2="17" />
          <polyline points="10 9 9 9 8 9" />
        </svg>
      </div>
      <div class="page-info">
        <h1 class="page-title">{{ displayTitle }}</h1>
        <p v-if="pageDescription" class="page-description">
          {{ pageDescription }}
        </p>
        <div class="page-meta">
          <span class="meta-item">
            {{ blockCount }} {{ blockCount === 1 ? "block" : "blocks" }}
          </span>
          <span class="meta-item">
            {{ folder.path }}
          </span>
        </div>
      </div>
      <div class="page-actions">
        <button @click="$emit('toggleProperties')" class="properties-btn">Properties</button>
      </div>
    </div>

    <!-- Loading blocks -->
    <div v-if="loadingBlocks" class="blocks-loading">
      Loading page content...
    </div>

    <!-- Unified block content -->
    <div v-else class="page-blocks">
      <div
        v-for="block in sortedBlocks"
        :key="block.file.id"
        class="page-block"
      >
        <!-- Markdown block: render inline -->
        <div v-if="getBlockDisplayType(block.file) === 'markdown'" class="block-content block-markdown">
          <MarkdownViewer
            v-if="block.content != null"
            :content="block.content"
            :frontmatter="block.file.properties"
            :workspace-id="workspaceId"
            :notebook-id="folder.notebook_id"
            :current-file-path="block.file.path"
            :show-frontmatter="false"
            :show-toolbar="false"
          />
          <div v-else class="block-placeholder" @click="$emit('selectFile', block.file)">
            {{ block.file.filename }}
          </div>
        </div>

        <!-- Image block: render inline -->
        <div v-else-if="getBlockDisplayType(block.file) === 'image'" class="block-content block-image">
          <img
            :src="getContentUrl(block.file)"
            :alt="block.file.title || block.file.filename"
            loading="lazy"
          />
        </div>

        <!-- Code block: render inline -->
        <div v-else-if="getBlockDisplayType(block.file) === 'code'" class="block-content block-code">
          <div class="code-block-header">{{ block.file.filename }}</div>
          <CodeViewer
            v-if="block.content != null"
            :content="block.content"
            :filename="block.file.filename"
            :show-line-numbers="true"
            :show-toolbar="false"
          />
          <div v-else class="block-placeholder" @click="$emit('selectFile', block.file)">
            {{ block.file.filename }}
          </div>
        </div>

        <!-- Video block -->
        <div v-else-if="getBlockDisplayType(block.file) === 'video'" class="block-content block-video">
          <video :src="getContentUrl(block.file)" controls class="block-media">
            Your browser does not support the video element.
          </video>
        </div>

        <!-- Audio block -->
        <div v-else-if="getBlockDisplayType(block.file) === 'audio'" class="block-content block-audio">
          <audio :src="getContentUrl(block.file)" controls class="block-media-audio">
            Your browser does not support the audio element.
          </audio>
        </div>

        <!-- PDF block -->
        <div v-else-if="getBlockDisplayType(block.file) === 'pdf'" class="block-content block-pdf">
          <iframe
            :src="getContentUrl(block.file)"
            class="pdf-frame"
            :title="block.file.title || block.file.filename"
          />
        </div>

        <!-- Other file types: show as clickable card -->
        <div v-else class="block-content block-file" @click="$emit('selectFile', block.file)">
          <div class="file-block-info">
            <span class="file-block-name">{{ block.file.filename }}</span>
            <span class="file-block-type">{{ block.file.content_type }}</span>
          </div>
        </div>
      </div>

      <!-- Empty state -->
      <div v-if="sortedBlocks.length === 0 && !loadingBlocks" class="empty-page">
        <p>This page has no content blocks yet.</p>
        <p class="empty-hint">
          Add numbered files (e.g., 001-intro.md, 002-image.png) to this directory to create blocks.
        </p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from "vue"
import type { FolderWithFiles, FileMetadata } from "../services/codex"
import { fileService } from "../services/codex"
import { getDisplayType, isTextType } from "../utils/contentType"
import MarkdownViewer from "./MarkdownViewer.vue"
import CodeViewer from "./CodeViewer.vue"

interface Props {
  folder: FolderWithFiles
  workspaceId: number
}

const props = defineProps<Props>()

defineEmits<{
  (e: "selectFile", file: FileMetadata): void
  (e: "selectFolder", subfolder: { path: string }): void
  (e: "toggleProperties"): void
}>()

interface BlockWithContent {
  file: FileMetadata
  position: number
  content: string | null
}

const loadingBlocks = ref(false)
const blocks = ref<BlockWithContent[]>([])

// Parse position from numbered filename pattern (e.g., "001-intro.md" -> 1)
function parsePosition(filename: string): number {
  const match = filename.match(/^(\d{3})-/)
  return match && match[1] ? parseInt(match[1], 10) : 999
}

// Check if a file is a numbered block file
function isBlockFile(file: FileMetadata): boolean {
  return /^\d{3}-/.test(file.filename)
}

// Get display type for a block file
function getBlockDisplayType(file: FileMetadata): string {
  return getDisplayType(file.content_type)
}

// Get content URL for binary files
function getContentUrl(file: FileMetadata): string {
  return fileService.getContentUrl(file.id, props.workspaceId, props.folder.notebook_id)
}

// Filter to block files and sort by position
const sortedBlocks = computed(() => {
  return [...blocks.value].sort((a, b) => a.position - b.position)
})

const blockCount = computed(() => sortedBlocks.value.length)

// Page display title - strip .page suffix from folder name
const displayTitle = computed(() => {
  const name = props.folder.title || props.folder.name || props.folder.path
  if (name.endsWith(".page")) {
    return name.slice(0, -5)
  }
  return name
})

const pageDescription = computed(() => {
  return props.folder.description || props.folder.properties?.description
})

// Load text content for blocks that can be rendered inline
async function loadBlockContents() {
  loadingBlocks.value = true

  try {
    // Filter to block files from the folder
    const blockFiles = (props.folder.files || []).filter(isBlockFile)

    // Build block list with positions
    const newBlocks: BlockWithContent[] = blockFiles.map((file) => ({
      file,
      position: parsePosition(file.filename),
      content: null,
    }))

    // Load text content for renderable text files in parallel
    const contentPromises = newBlocks.map(async (block) => {
      if (isTextType(block.file.content_type)) {
        try {
          const textContent = await fileService.getContent(
            block.file.id,
            props.workspaceId,
            props.folder.notebook_id,
          )
          block.content = textContent.content
        } catch (e) {
          // Content couldn't be loaded - leave as null
          console.warn(`Failed to load content for ${block.file.path}:`, e)
        }
      }
    })

    await Promise.all(contentPromises)
    blocks.value = newBlocks
  } finally {
    loadingBlocks.value = false
  }
}

// Also try to read page metadata from .page file in the folder
// (The folder.properties may already have it from the folder metadata endpoint)

// Load blocks when folder changes
watch(
  () => props.folder,
  () => {
    loadBlockContents()
  },
  { immediate: true },
)
</script>

<style scoped>
.page-unified-view {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow-y: auto;
}

.page-header {
  display: flex;
  align-items: flex-start;
  gap: 1rem;
  padding-bottom: 1.5rem;
  margin-bottom: 1.5rem;
  border-bottom: 2px solid var(--page-border, #e5e7eb);
}

.page-icon {
  flex-shrink: 0;
  color: var(--pen-gray, #6b7280);
  opacity: 0.6;
}

.page-info {
  flex: 1;
  min-width: 0;
}

.page-title {
  margin: 0 0 0.25rem 0;
  font-size: 1.75rem;
  font-weight: 700;
  color: var(--notebook-text, #1f2937);
  line-height: 1.2;
}

.page-description {
  margin: 0 0 0.5rem 0;
  font-size: 0.95rem;
  color: var(--pen-gray, #6b7280);
}

.page-meta {
  display: flex;
  gap: 1rem;
  font-size: 0.8rem;
  color: var(--pen-light-gray, #9ca3af);
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.page-actions {
  flex-shrink: 0;
}

.properties-btn {
  padding: 0.5rem 1rem;
  border: 1px solid var(--page-border, #d1d5db);
  border-radius: 0.375rem;
  background: var(--page-bg, #fff);
  color: var(--notebook-text, #374151);
  cursor: pointer;
  font-size: 0.875rem;
  transition: background 0.15s;
}

.properties-btn:hover {
  background: var(--bg-hover, #f3f4f6);
}

.blocks-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 3rem;
  color: var(--pen-gray, #6b7280);
}

.page-blocks {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.page-block {
  /* Blocks flow seamlessly without visible separation */
}

.block-content {
  /* Uniform block rendering */
}

.block-markdown {
  /* Markdown flows naturally */
}

.block-image img {
  max-width: 100%;
  height: auto;
  display: block;
  margin: 1rem 0;
  border-radius: 0.375rem;
}

.block-code {
  margin: 1rem 0;
  border: 1px solid var(--page-border, #e5e7eb);
  border-radius: 0.375rem;
  overflow: hidden;
}

.code-block-header {
  padding: 0.375rem 0.75rem;
  font-size: 0.75rem;
  color: var(--pen-gray, #6b7280);
  background: var(--bg-secondary, #f9fafb);
  border-bottom: 1px solid var(--page-border, #e5e7eb);
  font-family: monospace;
}

.block-video .block-media {
  max-width: 100%;
  max-height: 600px;
  display: block;
  margin: 1rem 0;
  border-radius: 0.375rem;
}

.block-audio .block-media-audio {
  width: 100%;
  margin: 1rem 0;
}

.block-pdf .pdf-frame {
  width: 100%;
  height: 600px;
  border: 1px solid var(--page-border, #e5e7eb);
  border-radius: 0.375rem;
  margin: 1rem 0;
}

.block-file {
  display: flex;
  align-items: center;
  padding: 0.75rem 1rem;
  margin: 0.5rem 0;
  border: 1px solid var(--page-border, #e5e7eb);
  border-radius: 0.375rem;
  cursor: pointer;
  transition: background 0.15s;
}

.block-file:hover {
  background: var(--bg-hover, #f3f4f6);
}

.file-block-info {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.file-block-name {
  font-weight: 500;
  color: var(--notebook-text, #374151);
}

.file-block-type {
  font-size: 0.8rem;
  color: var(--pen-light-gray, #9ca3af);
}

.block-placeholder {
  padding: 0.75rem 1rem;
  color: var(--pen-gray, #6b7280);
  cursor: pointer;
  border: 1px dashed var(--page-border, #e5e7eb);
  border-radius: 0.375rem;
  margin: 0.5rem 0;
  transition: background 0.15s;
}

.block-placeholder:hover {
  background: var(--bg-hover, #f3f4f6);
}

.empty-page {
  text-align: center;
  padding: 3rem;
  color: var(--pen-gray, #6b7280);
}

.empty-hint {
  font-size: 0.875rem;
  color: var(--pen-light-gray, #9ca3af);
}
</style>
