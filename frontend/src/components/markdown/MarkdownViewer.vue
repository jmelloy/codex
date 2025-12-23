<script setup lang="ts">
import { computed } from "vue";
import { marked } from "marked";
import DOMPurify from "dompurify";

const props = withDefaults(
  defineProps<{
    content: string;
    class?: string;
  }>(),
  {
    content: "",
    class: "",
  }
);

const sanitizedHtml = computed(() => {
  if (!props.content) return "";
  const rawHtml = marked(props.content) as string;
  return DOMPurify.sanitize(rawHtml);
});
</script>

<template>
  <div
    :class="['markdown-viewer', props.class]"
    v-html="sanitizedHtml"
  ></div>
</template>

<style scoped>
.markdown-viewer {
  line-height: 1.7;
  font-family: var(--font-body);
  color: var(--color-text);
}

.markdown-viewer :deep(h1),
.markdown-viewer :deep(h2),
.markdown-viewer :deep(h3),
.markdown-viewer :deep(h4),
.markdown-viewer :deep(h5),
.markdown-viewer :deep(h6) {
  margin-top: 1.5rem;
  margin-bottom: 0.75rem;
  font-weight: 600;
  line-height: 1.25;
  color: var(--color-primary, #4f46e5);
}

.markdown-viewer :deep(h1:first-child),
.markdown-viewer :deep(h2:first-child),
.markdown-viewer :deep(h3:first-child),
.markdown-viewer :deep(h4:first-child),
.markdown-viewer :deep(h5:first-child),
.markdown-viewer :deep(h6:first-child) {
  margin-top: 0;
}

.markdown-viewer :deep(h1) {
  font-size: 2rem;
}

.markdown-viewer :deep(h2) {
  font-size: 1.5rem;
}

.markdown-viewer :deep(h3) {
  font-size: 1.25rem;
}

.markdown-viewer :deep(h4) {
  font-size: 1.125rem;
}

.markdown-viewer :deep(h5),
.markdown-viewer :deep(h6) {
  font-size: 1rem;
}

.markdown-viewer :deep(p) {
  margin-bottom: 0.75rem;
}

.markdown-viewer :deep(p:last-child) {
  margin-bottom: 0;
}

.markdown-viewer :deep(ul),
.markdown-viewer :deep(ol) {
  margin-left: 1.5rem;
  margin-bottom: 0.75rem;
  padding-left: 0.5rem;
}

.markdown-viewer :deep(li) {
  margin-bottom: 0.25rem;
}

.markdown-viewer :deep(code) {
  background: var(--color-background, #f5f5f5);
  padding: 0.125rem 0.375rem;
  border-radius: var(--radius-sm, 0.25rem);
  font-size: 0.875em;
  font-family: var(--font-mono, monospace);
  color: var(--color-ink-blue, #3b82f6);
}

.markdown-viewer :deep(pre) {
  background: var(--color-background, #f5f5f5);
  padding: 1rem;
  border-radius: var(--radius-md, 0.375rem);
  overflow-x: auto;
  margin-bottom: 0.75rem;
  border-left: 3px solid var(--color-primary, #4f46e5);
}

.markdown-viewer :deep(pre code) {
  background: none;
  padding: 0;
  color: inherit;
}

.markdown-viewer :deep(blockquote) {
  border-left: 3px solid var(--color-primary, #4f46e5);
  padding-left: 1rem;
  margin: 0.75rem 0;
  color: var(--color-text-secondary, #666);
  font-style: italic;
}

.markdown-viewer :deep(a) {
  color: var(--color-primary, #4f46e5);
  text-decoration: none;
}

.markdown-viewer :deep(a:hover) {
  text-decoration: underline;
}

.markdown-viewer :deep(table) {
  border-collapse: collapse;
  width: 100%;
  margin-bottom: 0.75rem;
}

.markdown-viewer :deep(table th),
.markdown-viewer :deep(table td) {
  border: 1px solid var(--color-border, #e5e7eb);
  padding: 0.5rem;
  text-align: left;
}

.markdown-viewer :deep(table th) {
  background: var(--color-background, #f5f5f5);
  font-weight: 600;
}

.markdown-viewer :deep(img) {
  max-width: 100%;
  height: auto;
  border-radius: var(--radius-md, 0.375rem);
  margin: 0.75rem 0;
}

.markdown-viewer :deep(hr) {
  border: none;
  border-top: 1px solid var(--color-border, #e5e7eb);
  margin: 1.5rem 0;
}
</style>
