<template>
  <div class="markdown-viewer notebook-page" :class="themeStore.theme.className">
    <div class="markdown-toolbar" v-if="showToolbar">
      <button @click="$emit('edit')" v-if="editable" class="btn-edit">
        Edit
      </button>
      <button @click="copyContent" class="btn-copy">
        Copy
      </button>
      <slot name="toolbar-actions"></slot>
    </div>
    <div
      class="markdown-content notebook-content"
      v-html="renderedHtml"
      :class="{ 'loading': isLoading }"
    ></div>
    <div v-if="showFrontmatter && frontmatter" class="frontmatter-section">
      <h4>Metadata</h4>
      <pre>{{ JSON.stringify(frontmatter, null, 2) }}</pre>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { marked } from 'marked'
import hljs from 'highlight.js'
import 'highlight.js/styles/github.css'
import { useThemeStore } from '../stores/theme'

const themeStore = useThemeStore()

// Props
interface Props {
  content: string
  frontmatter?: Record<string, any>
  editable?: boolean
  showToolbar?: boolean
  showFrontmatter?: boolean
  extensions?: MarkdownExtension[]
}

const props = withDefaults(defineProps<Props>(), {
  content: '',
  editable: true,
  showToolbar: true,
  showFrontmatter: false,
  extensions: () => []
})

// Emits
const emit = defineEmits<{
  edit: []
  copy: []
}>()

// State
const isLoading = ref(false)

// Extension system for custom rendering
export interface MarkdownExtension {
  name: string
  renderer?: any
}

// Configure marked with extensions
const configureMarked = () => {
  marked.setOptions({
    breaks: true,
    gfm: true
  })

  // Apply custom extensions
  if (props.extensions && props.extensions.length > 0) {
    props.extensions.forEach(ext => {
      if (ext.renderer) {
        marked.use({
          renderer: ext.renderer
        })
      }
    })
  }
}

// Computed
const renderedHtml = computed(() => {
  if (!props.content) {
    return '<p class="empty-content">No content to display</p>'
  }
  
  try {
    const html = marked(props.content) as string
    // Apply syntax highlighting to code blocks safely
    const parser = new DOMParser()
    const doc = parser.parseFromString(html, 'text/html')
    const codeBlocks = doc.querySelectorAll('pre code')
    codeBlocks.forEach((block) => {
      const code = block.textContent || ''
      const highlighted = hljs.highlightAuto(code)
      // Create a new element to safely set the highlighted HTML
      const highlightedElement = document.createElement('code')
      highlightedElement.innerHTML = highlighted.value
      // Copy classes
      highlightedElement.className = block.className
      // Replace the code block
      block.parentNode?.replaceChild(highlightedElement, block)
    })
    return doc.body.innerHTML
  } catch (e) {
    console.error('Markdown parsing error:', e)
    return '<p class="error-content">Error rendering markdown</p>'
  }
})

// Methods
const copyContent = async () => {
  try {
    await navigator.clipboard.writeText(props.content)
    emit('copy')
  } catch (e) {
    console.error('Copy failed:', e)
  }
}

// Lifecycle
onMounted(() => {
  configureMarked()
})

// Watch for extension changes
watch(() => props.extensions, () => {
  configureMarked()
}, { deep: true })
</script>

<style scoped>
.markdown-viewer {
  display: flex;
  flex-direction: column;
  height: 100%;
  border-radius: var(--radius-lg);
  overflow: hidden;
  box-shadow: var(--shadow-md);
}

.markdown-toolbar {
  display: flex;
  gap: var(--spacing-sm);
  padding: var(--spacing-md);
  background: color-mix(in srgb, var(--color-bg-primary) 50%, transparent);
  border-bottom: 1px solid var(--color-border-light);
  align-items: center;
  backdrop-filter: blur(10px);
}

.markdown-toolbar button {
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

.markdown-toolbar button:hover {
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

.markdown-content {
  flex: 1;
  padding: var(--spacing-3xl) 4rem;
  overflow-y: auto;
  line-height: var(--leading-loose);
}

.markdown-content.loading {
  opacity: 0.5;
}

.markdown-content :deep(h1) {
  font-size: var(--text-2xl);
  margin-top: var(--spacing-xl);
  margin-bottom: var(--spacing-lg);
  font-weight: var(--font-semibold);
  border-bottom: 2px solid var(--color-border-light);
  padding-bottom: var(--spacing-sm);
  color: var(--color-text-primary);
}

.markdown-content :deep(h2) {
  font-size: var(--text-xl);
  margin-top: var(--spacing-xl);
  margin-bottom: var(--spacing-md);
  font-weight: var(--font-semibold);
  color: var(--color-text-primary);
}

.markdown-content :deep(h3) {
  font-size: var(--text-lg);
  margin-top: var(--spacing-lg);
  margin-bottom: var(--spacing-sm);
  font-weight: var(--font-semibold);
  color: var(--color-text-primary);
}

.markdown-content :deep(p) {
  margin-bottom: var(--spacing-lg);
  color: var(--color-text-primary);
}

.markdown-content :deep(code) {
  background: var(--color-bg-secondary);
  padding: 0.2rem 0.4rem;
  border-radius: var(--radius-sm);
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  color: var(--color-text-primary);
}

.markdown-content :deep(pre) {
  background: var(--color-text-primary);
  color: var(--color-bg-primary);
  padding: var(--spacing-lg);
  border-radius: var(--radius-md);
  overflow-x: auto;
  margin-bottom: var(--spacing-lg);
}

.markdown-content :deep(pre code) {
  background: transparent;
  padding: 0;
  color: inherit;
}

.markdown-content :deep(blockquote) {
  border-left: 4px solid var(--color-primary);
  padding-left: var(--spacing-lg);
  margin-left: 0;
  color: var(--color-text-secondary);
  font-style: italic;
}

.markdown-content :deep(ul),
.markdown-content :deep(ol) {
  margin-bottom: var(--spacing-lg);
  padding-left: var(--spacing-2xl);
}

.markdown-content :deep(li) {
  margin-bottom: var(--spacing-xs);
}

.markdown-content :deep(a) {
  color: var(--color-primary);
  text-decoration: none;
}

.markdown-content :deep(a:hover) {
  text-decoration: underline;
}

.markdown-content :deep(table) {
  border-collapse: collapse;
  width: 100%;
  margin-bottom: var(--spacing-lg);
}

.markdown-content :deep(th),
.markdown-content :deep(td) {
  border: 1px solid var(--color-border-light);
  padding: var(--spacing-sm);
  text-align: left;
  color: var(--color-text-primary);
}

.markdown-content :deep(th) {
  background: var(--color-bg-secondary);
  font-weight: var(--font-semibold);
}

.markdown-content :deep(img) {
  max-width: 100%;
  height: auto;
  border-radius: var(--radius-sm);
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
