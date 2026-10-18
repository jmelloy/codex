<!-- Full-page viewer for a single prose block (MDX or legacy Markdown). -->
<template>
  <div class="mdx-viewer notebook-page" :class="themeStore.theme.className">
    <div class="mdx-content notebook-content">
      <MdxBlockRenderer
        :content="content"
        :format="format"
        :workspace-id="workspaceId"
        :notebook-id="notebookId"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { useThemeStore } from "../stores/theme"
import MdxBlockRenderer from "./blocks/MdxBlockRenderer.vue"
import type { MdxFormat } from "../services/mdxRenderer"

const themeStore = useThemeStore()

withDefaults(
  defineProps<{
    content: string
    format?: MdxFormat
    workspaceId?: string
    notebookId?: string
  }>(),
  {
    content: "",
    format: "mdx",
    workspaceId: undefined,
    notebookId: undefined,
  },
)
</script>

<style scoped>
.mdx-viewer {
  display: flex;
  flex-direction: column;
  height: 100%;
  border-radius: var(--radius-lg);
  overflow: hidden;
  box-shadow: var(--shadow-md);
}

.mdx-content {
  flex: 1;
  padding: var(--spacing-3xl) 4rem;
  overflow-y: auto;
  line-height: var(--leading-loose);
}

.mdx-content :deep(h1) {
  font-size: var(--text-2xl);
  margin-top: var(--spacing-xl);
  margin-bottom: var(--spacing-lg);
  font-weight: var(--font-semibold);
  border-bottom: 2px solid var(--color-border-light);
  padding-bottom: var(--spacing-sm);
  color: var(--color-text-primary);
}

.mdx-content :deep(h2) {
  font-size: var(--text-xl);
  margin-top: var(--spacing-xl);
  margin-bottom: var(--spacing-md);
  font-weight: var(--font-semibold);
  color: var(--color-text-primary);
}

.mdx-content :deep(h3) {
  font-size: var(--text-lg);
  margin-top: var(--spacing-lg);
  margin-bottom: var(--spacing-sm);
  font-weight: var(--font-semibold);
  color: var(--color-text-primary);
}

.mdx-content :deep(p) {
  margin-bottom: var(--spacing-lg);
  color: var(--color-text-primary);
}

.mdx-content :deep(code) {
  background: var(--color-bg-secondary);
  padding: 0.2rem 0.4rem;
  border-radius: var(--radius-sm);
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  color: var(--color-text-primary);
}

.mdx-content :deep(blockquote) {
  border-left: 4px solid var(--color-primary);
  padding-left: var(--spacing-lg);
  margin-left: 0;
  color: var(--color-text-secondary);
  font-style: italic;
}

.mdx-content :deep(ul),
.mdx-content :deep(ol) {
  margin-bottom: var(--spacing-lg);
  padding-left: var(--spacing-2xl);
}

.mdx-content :deep(li) {
  margin-bottom: var(--spacing-xs);
}

.mdx-content :deep(a) {
  color: var(--color-primary);
  text-decoration: none;
}

.mdx-content :deep(a:hover) {
  text-decoration: underline;
}

.mdx-content :deep(table) {
  border-collapse: collapse;
  margin-bottom: var(--spacing-lg);
}

.mdx-content :deep(th),
.mdx-content :deep(td) {
  border: 1px solid var(--color-border-light);
  padding: var(--spacing-xs) var(--spacing-sm);
  text-align: left;
}

.mdx-content :deep(img) {
  max-width: 100%;
}

.mdx-content :deep(.mdx-unauthorized-component) {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-xs);
  border: 2px dashed var(--color-error);
  border-radius: var(--radius-sm);
  padding: var(--spacing-xs) var(--spacing-sm);
  color: var(--color-error);
  font-size: var(--text-sm);
}

.empty-content,
.error-content {
  color: var(--color-text-placeholder);
  text-align: center;
  padding: var(--spacing-2xl);
}

.error-content {
  color: var(--color-error);
}
</style>
