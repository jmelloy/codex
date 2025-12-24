<template>
  <div class="markdown-viewer">
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
      class="markdown-content" 
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
  background: white;
  border-radius: 8px;
  overflow: hidden;
}

.markdown-toolbar {
  display: flex;
  gap: 0.5rem;
  padding: 0.75rem;
  background: #f7fafc;
  border-bottom: 1px solid #e2e8f0;
  align-items: center;
}

.markdown-toolbar button {
  padding: 0.5rem 1rem;
  border: 1px solid #cbd5e0;
  background: white;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.875rem;
  transition: all 0.2s;
}

.markdown-toolbar button:hover {
  background: #edf2f7;
  border-color: #a0aec0;
}

.btn-edit {
  color: #667eea;
  border-color: #667eea !important;
}

.btn-edit:hover {
  background: #667eea !important;
  color: white !important;
}

.markdown-content {
  flex: 1;
  padding: 2rem;
  overflow-y: auto;
  line-height: 1.6;
}

.markdown-content.loading {
  opacity: 0.5;
}

.markdown-content :deep(h1) {
  font-size: 2rem;
  margin-top: 1.5rem;
  margin-bottom: 1rem;
  font-weight: 600;
  border-bottom: 2px solid #e2e8f0;
  padding-bottom: 0.5rem;
}

.markdown-content :deep(h2) {
  font-size: 1.5rem;
  margin-top: 1.25rem;
  margin-bottom: 0.75rem;
  font-weight: 600;
}

.markdown-content :deep(h3) {
  font-size: 1.25rem;
  margin-top: 1rem;
  margin-bottom: 0.5rem;
  font-weight: 600;
}

.markdown-content :deep(p) {
  margin-bottom: 1rem;
  color: #2d3748;
}

.markdown-content :deep(code) {
  background: #f7fafc;
  padding: 0.2rem 0.4rem;
  border-radius: 3px;
  font-family: 'Monaco', 'Courier New', monospace;
  font-size: 0.875rem;
}

.markdown-content :deep(pre) {
  background: #2d3748;
  color: #e2e8f0;
  padding: 1rem;
  border-radius: 6px;
  overflow-x: auto;
  margin-bottom: 1rem;
}

.markdown-content :deep(pre code) {
  background: transparent;
  padding: 0;
  color: inherit;
}

.markdown-content :deep(blockquote) {
  border-left: 4px solid #667eea;
  padding-left: 1rem;
  margin-left: 0;
  color: #4a5568;
  font-style: italic;
}

.markdown-content :deep(ul),
.markdown-content :deep(ol) {
  margin-bottom: 1rem;
  padding-left: 2rem;
}

.markdown-content :deep(li) {
  margin-bottom: 0.25rem;
}

.markdown-content :deep(a) {
  color: #667eea;
  text-decoration: none;
}

.markdown-content :deep(a:hover) {
  text-decoration: underline;
}

.markdown-content :deep(table) {
  border-collapse: collapse;
  width: 100%;
  margin-bottom: 1rem;
}

.markdown-content :deep(th),
.markdown-content :deep(td) {
  border: 1px solid #e2e8f0;
  padding: 0.5rem;
  text-align: left;
}

.markdown-content :deep(th) {
  background: #f7fafc;
  font-weight: 600;
}

.markdown-content :deep(img) {
  max-width: 100%;
  height: auto;
  border-radius: 4px;
}

.empty-content,
.error-content {
  color: #a0aec0;
  text-align: center;
  padding: 2rem;
}

.error-content {
  color: #f56565;
}

.frontmatter-section {
  padding: 1rem;
  background: #f7fafc;
  border-top: 1px solid #e2e8f0;
}

.frontmatter-section h4 {
  margin: 0 0 0.5rem;
  font-size: 0.875rem;
  color: #4a5568;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.frontmatter-section pre {
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 4px;
  padding: 0.75rem;
  font-size: 0.75rem;
  overflow-x: auto;
  margin: 0;
}
</style>
