<template>
  <div class="mdx-viewer notebook-page" :class="themeStore.theme.className">
    <div class="mdx-toolbar" v-if="showToolbar">
      <button @click="$emit('edit')" v-if="editable" class="btn-edit">Edit</button>
      <button @click="copyContent" class="btn-copy">Copy</button>
      <slot name="toolbar-actions"></slot>
    </div>
    <div class="mdx-content notebook-content">
      <component :is="renderRoot" />
    </div>
    <div v-if="showFrontmatter && frontmatter" class="frontmatter-section">
      <h4>Metadata</h4>
      <pre>{{ JSON.stringify(frontmatter, null, 2) }}</pre>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, h, type Component, type VNode } from "vue"
import { useThemeStore } from "../stores/theme"
import { compileMdx, MdxCompileError } from "../services/mdxRenderer"
import { resolveLegacyBackedMdxComponent } from "../services/mdxLegacyBlockAdapter"
import Calendar from "./blocks/Calendar.vue"
import CodeBlock from "./blocks/CodeBlock.vue"

const themeStore = useThemeStore()

interface Props {
  content: string
  frontmatter?: Record<string, any>
  editable?: boolean
  showToolbar?: boolean
  showFrontmatter?: boolean
  workspaceId?: string
  notebookId?: string
  parentBlockId?: string
}

const props = withDefaults(defineProps<Props>(), {
  content: "",
  editable: true,
  showToolbar: true,
  showFrontmatter: false,
  workspaceId: undefined,
  notebookId: undefined,
  parentBlockId: undefined,
})

defineEmits<{
  edit: []
  copy: []
}>()

// Components with a dedicated MDX-native implementation, resolved before
// falling back to legacy code-fence block components (Weather, GitHub*, etc).
const DEDICATED_COMPONENTS: Record<string, Component> = {
  Calendar,
  CodeBlock,
}

function resolveComponent(name: string): Component | undefined {
  return (
    DEDICATED_COMPONENTS[name] ??
    resolveLegacyBackedMdxComponent(name, {
      workspaceId: props.workspaceId,
      notebookId: props.notebookId,
      parentBlockId: props.parentBlockId,
    })
  )
}

const renderedVNode = computed<{ vnode: VNode | null; error: string | null }>(() => {
  if (!props.content.trim()) {
    return { vnode: null, error: null }
  }
  try {
    return { vnode: compileMdx(props.content, resolveComponent), error: null }
  } catch (e) {
    const message = e instanceof MdxCompileError ? e.message : String(e)
    console.error("MDX compile error:", e)
    return { vnode: null, error: message }
  }
})

// A parameterless functional component so <component :is="renderRoot" /> can
// render an already-built VNode tree from renderedVNode without re-invoking
// MDXContent on every Vue re-render.
const renderRoot = () => {
  const { vnode, error } = renderedVNode.value
  if (error) {
    return h("p", { class: "error-content" }, `Error rendering MDX: ${error}`)
  }
  if (!vnode) {
    return h("p", { class: "empty-content" }, "No content to display")
  }
  return vnode
}

const copyContent = async () => {
  try {
    await navigator.clipboard.writeText(props.content)
  } catch (e) {
    console.error("Copy failed:", e)
  }
}
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

.mdx-toolbar {
  display: flex;
  gap: var(--spacing-sm);
  padding: var(--spacing-md);
  background: color-mix(in srgb, var(--color-bg-primary) 50%, transparent);
  border-bottom: 1px solid var(--color-border-light);
  align-items: center;
  backdrop-filter: blur(10px);
}

.mdx-toolbar button {
  padding: var(--spacing-sm) var(--spacing-lg);
  border: 1px solid var(--color-border-medium);
  background: var(--color-bg-primary);
  color: var(--color-text-primary);
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  transition: all 0.2s;
}

.mdx-toolbar button:hover {
  background: var(--color-bg-hover);
  border-color: var(--color-border-dark);
}

.btn-edit {
  color: var(--color-primary);
  border-color: var(--color-primary) !important;
}

.btn-edit:hover {
  background: var(--color-primary) !important;
  color: var(--color-text-inverse) !important;
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

.mdx-content :deep(pre) {
  background: var(--color-text-primary);
  color: var(--color-bg-primary);
  padding: var(--spacing-lg);
  border-radius: var(--radius-md);
  overflow-x: auto;
  margin-bottom: var(--spacing-lg);
}

.mdx-content :deep(pre code) {
  background: transparent;
  padding: 0;
  color: inherit;
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

.frontmatter-section {
  padding: var(--spacing-lg);
  background: var(--color-bg-secondary);
  border-top: 1px solid var(--color-border-light);
}

.frontmatter-section h4 {
  margin: 0 0 var(--spacing-sm);
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
  font-weight: var(--font-semibold);
  text-transform: uppercase;
  letter-spacing: var(--tracking-wide);
}

.frontmatter-section pre {
  background: var(--color-bg-primary);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-sm);
  padding: var(--spacing-md);
  font-size: var(--text-xs);
  overflow-x: auto;
  margin: 0;
  color: var(--color-text-primary);
}
</style>
