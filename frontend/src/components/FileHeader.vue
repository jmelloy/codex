<template>
  <div class="file-header">
    <div class="file-icon">
      <component :is="fileIcon" />
    </div>
    <div class="file-info">
      <h1 class="file-title">{{ displayTitle }}</h1>
      <p v-if="file.properties?.description" class="file-description">
        {{ file.properties.description }}
      </p>
      <div class="file-meta">
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
          {{ file.content_type }}
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
              d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"
            />
          </svg>
          {{ formatSize(file.size) }}
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
            <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
            <line x1="16" y1="2" x2="16" y2="6" />
            <line x1="8" y1="2" x2="8" y2="6" />
            <line x1="3" y1="10" x2="21" y2="10" />
          </svg>
          {{ formatDate(file.updated_at) }}
        </span>
      </div>
    </div>
    <div class="file-actions">
      <slot name="actions">
        <button @click="$emit('toggleProperties')" class="properties-btn">Properties</button>
      </slot>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, h } from "vue"
import type { FileMetadata } from "../services/codex"
import { getDisplayType } from "../utils/contentType"

interface Props {
  file: FileMetadata
}

const props = defineProps<Props>()

defineEmits<{
  toggleProperties: []
}>()

const displayTitle = computed(() => {
  return props.file.properties?.title || props.file.title || props.file.filename
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

const fileIcon = computed(() => {
  const displayType = getDisplayType(props.file.content_type)
  const iconProps = {
    width: 48,
    height: 48,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    "stroke-width": 1.5,
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
    case "html":
      return () =>
        h("svg", iconProps, [
          h("polyline", { points: "16 18 22 12 16 6" }),
          h("polyline", { points: "8 6 2 12 8 18" }),
          h("line", { x1: "12", y1: "2", x2: "12", y2: "22" }),
        ])
    case "view":
      return () =>
        h("svg", iconProps, [
          h("rect", { x: "3", y: "3", width: "18", height: "18", rx: "2", ry: "2" }),
          h("line", { x1: "3", y1: "9", x2: "21", y2: "9" }),
          h("line", { x1: "9", y1: "21", x2: "9", y2: "9" }),
        ])
    case "binary":
      return () =>
        h("svg", iconProps, [
          h("path", {
            d: "M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z",
          }),
          h("polyline", { points: "3.27 6.96 12 12.01 20.73 6.96" }),
          h("line", { x1: "12", y1: "22.08", x2: "12", y2: "12" }),
        ])
    default:
      return () =>
        h("svg", iconProps, [
          h("path", { d: "M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" }),
          h("polyline", { points: "14 2 14 8 20 8" }),
        ])
  }
})
</script>

<style scoped>
.file-header {
  display: flex;
  align-items: flex-start;
  gap: var(--spacing-xl);
  padding: var(--spacing-xl);
  border-bottom: 1px solid var(--color-border-light);
  background: var(--color-bg-secondary);
  overflow-x: auto;
}

.file-icon {
  color: var(--color-primary);
  flex-shrink: 0;
}

.file-info {
  flex: 1;
  min-width: 0;
}

.file-actions {
  flex-shrink: 0;
  display: flex;
  gap: var(--spacing-sm);
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

.file-title {
  margin: 0 0 var(--spacing-sm);
  font-size: var(--text-2xl);
  font-weight: var(--font-semibold);
  color: var(--color-text-primary);
  /* Enable wrapping for long file names */
  overflow-wrap: break-word;
  word-break: break-word;
  /* Limit to 2 lines with ellipsis */
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  line-height: 1.4;
}

.file-description {
  margin: 0 0 var(--spacing-md);
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
  line-height: 1.5;
}

.file-meta {
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
  text-transform: capitalize;
}
</style>
