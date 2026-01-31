<template>
  <div class="markdown-viewer notebook-page" :class="[themeStore.theme.className, codeThemeClass]">
    <div class="markdown-toolbar" v-if="showToolbar">
      <button @click="$emit('edit')" v-if="editable" class="btn-edit">Edit</button>
      <button @click="copyContent" class="btn-copy">Copy</button>
      <slot name="toolbar-actions"></slot>
    </div>
    <div
      class="markdown-content notebook-content"
      v-html="renderedHtml"
      :class="{ loading: isLoading }"
      :key="contentKey"
    ></div>
    <div v-if="showFrontmatter && frontmatter" class="frontmatter-section">
      <h4>Metadata</h4>
      <pre>{{ JSON.stringify(frontmatter, null, 2) }}</pre>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, defineAsyncComponent, h, type Component } from "vue"
import { marked } from "marked"
import hljs from "highlight.js"
import { useThemeStore } from "../stores/theme"
import { createApp } from "vue"

// Fallback component for when plugin blocks fail to load
const createFallbackComponent = (blockType: string) => ({
  props: ["config"] as const,
  setup(props: { config?: Record<string, unknown> }) {
    return () =>
      h("div", { class: "custom-block plugin-fallback-block" }, [
        h("div", { class: "block-header" }, [
          h("span", { class: "block-icon" }, "⚠️"),
          h("span", { class: "block-title" }, `${blockType} Block`),
        ]),
        h("div", { class: "block-content" }, [
          h("div", { class: "block-note" }, [
            h("em", {}, "Plugin component not available. Please ensure the plugin is installed."),
          ]),
          props.config &&
            h("pre", { class: "config-preview" }, JSON.stringify(props.config, null, 2)),
        ]),
      ])
  },
})

// Loading component
const LoadingComponent = {
  setup() {
    return () => h("div", { class: "custom-block loading-block" }, "Loading...")
  },
}

// Dynamically load plugin components with fallback
const loadPluginComponent = (pluginPath: string, blockType: string): Component => {
  return defineAsyncComponent({
    loader: () => import(/* @vite-ignore */ `@plugins/${pluginPath}`),
    errorComponent: createFallbackComponent(blockType),
    loadingComponent: LoadingComponent,
  })
}

// Plugin block components - loaded dynamically
const WeatherBlock = loadPluginComponent("weather-api/components/WeatherBlock.vue", "Weather")
const LinkPreviewBlock = loadPluginComponent("opengraph/components/LinkPreviewBlock.vue", "Link Preview")

const themeStore = useThemeStore()

// Props
interface Props {
  content: string
  frontmatter?: Record<string, any>
  editable?: boolean
  showToolbar?: boolean
  showFrontmatter?: boolean
  extensions?: MarkdownExtension[]
  workspaceId?: number
  notebookId?: number
  currentFilePath?: string
}

const props = withDefaults(defineProps<Props>(), {
  content: "",
  editable: true,
  showToolbar: true,
  showFrontmatter: false,
  extensions: () => [],
  workspaceId: undefined,
  notebookId: undefined,
  currentFilePath: undefined,
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

// Helper function to check if a URL is a local file reference
const isLocalFileReference = (href: string): boolean => {
  // Check if it's a markdown or text file
  if (href.endsWith(".md") || href.endsWith(".txt")) {
    return true
  }
  // Check if it's not an external URL or absolute path
  return !href.startsWith("http://") && !href.startsWith("https://") && !href.startsWith("/")
}

// Helper function to resolve file references
const resolveFileUrl = (href: string): string => {
  // If workspace and notebook IDs are available, resolve the file
  if (props.workspaceId && props.notebookId) {
    // Check if it's already a full URL or API path
    if (href.startsWith("http://") || href.startsWith("https://") || href.startsWith("/api/")) {
      return href
    }

    // For relative or filename-only references, use the by-path/content endpoint
    const encodedPath = encodeURIComponent(href)
    return `/api/v1/files/by-path/content?path=${encodedPath}&workspace_id=${props.workspaceId}&notebook_id=${props.notebookId}`
  }

  // Fallback to original href if no context
  return href
}

// Type for marked renderer token
interface RendererToken {
  href: string
  title?: string | null
  text: string
}

// Configure marked with extensions
const configureMarked = () => {
  // Create a custom renderer for images and links
  const renderer = {
    // Override image rendering to resolve file references
    image(token: RendererToken): string {
      if (token.href) {
        // Resolve the image URL
        const resolvedHref = resolveFileUrl(token.href)
        // Build the img tag manually
        const title = token.title ? ` title="${token.title}"` : ""
        const alt = token.text || ""
        return `<img src="${resolvedHref}" alt="${alt}"${title}>`
      }
      return ""
    },

    // Override link rendering to resolve file references
    link(token: RendererToken): string {
      if (token.href) {
        // Check if it's a file reference (markdown or other files)
        if (isLocalFileReference(token.href)) {
          // For markdown files, we could navigate to them in the app
          // For now, just resolve the URL to view the content
          const resolvedHref = resolveFileUrl(token.href)
          const title = token.title ? ` title="${token.title}"` : ""
          const text = token.text || ""
          return `<a href="${resolvedHref}"${title}>${text}</a>`
        }
      }
      // Use default behavior for external links
      const title = token.title ? ` title="${token.title}"` : ""
      const text = token.text || ""
      return `<a href="${token.href}"${title}>${text}</a>`
    },
  }

  marked.use({ renderer })

  marked.setOptions({
    breaks: true,
    gfm: true,
  })

  // Apply custom extensions after base renderer
  if (props.extensions && props.extensions.length > 0) {
    props.extensions.forEach((ext) => {
      if (ext.renderer) {
        marked.use({
          renderer: ext.renderer,
        })
      }
    })
  }
}

// Configure marked with extensions immediately
configureMarked()

// Theme class for code blocks
const codeThemeClass = computed(() => {
  const className = themeStore.theme?.className ?? ""
  return className.includes("dark") ? "code-theme-dark" : "code-theme-light"
})

// Generate a unique key for the content to force Vue to replace the DOM
// instead of patching it, which can cause "nextSibling" errors with v-html
const contentKey = computed(() => {
  // Simple hash based on content length and first/last characters
  const content = props.content || ""
  return `${content.length}-${content.charCodeAt(0) || 0}-${content.charCodeAt(content.length - 1) || 0}`
})

// Extract language from code block class (e.g., "language-javascript" -> "javascript")
const extractLanguage = (className: string): string | null => {
  const match = className.match(/language-(\w+)/)
  return match && match[1] ? match[1] : null
}

// Custom block registry
const customBlockComponents: Record<string, any> = {
  weather: WeatherBlock,
  "link-preview": LinkPreviewBlock,
  // More block types can be registered here
}

// Parse custom blocks from code fences
const parseCustomBlocks = (html: string): { html: string; blocks: any[] } => {
  const parser = new DOMParser()
  const doc = parser.parseFromString(html, "text/html")
  const blocks: any[] = []

  // Find code blocks that might be custom blocks
  const codeBlocks = doc.querySelectorAll("pre code")
  codeBlocks.forEach((codeBlock, index) => {
    const className = codeBlock.className
    const language = extractLanguage(className)

    if (language && language in customBlockComponents) {
      // This is a custom block
      const content = codeBlock.textContent || ""
      
      // Try to parse as YAML config
      let config: Record<string, any> = {}
      try {
        // Simple YAML parser for key: value pairs
        content.split("\n").forEach((line) => {
          const match = line.match(/^(\w+):\s*(.+)$/)
          if (match && match[1] && match[2]) {
            config[match[1]] = match[2].trim()
          }
        })
      } catch (e) {
        console.warn("Failed to parse custom block config:", e)
      }

      // Create a placeholder div with a unique ID
      const blockId = `custom-block-${language}-${index}`
      const placeholder = doc.createElement("div")
      placeholder.id = blockId
      placeholder.className = "custom-block-placeholder"

      // Replace the pre element with our placeholder
      codeBlock.parentElement?.replaceWith(placeholder)

      blocks.push({
        id: blockId,
        type: language,
        config,
        component: customBlockComponents[language],
      })
    }
  })

  return {
    html: doc.body.innerHTML,
    blocks,
  }
}

// Mount Vue components for custom blocks
const mountCustomBlocks = (blocks: any[]) => {
  blocks.forEach((block) => {
    setTimeout(() => {
      const container = document.getElementById(block.id)
      if (container) {
        const app = createApp(block.component, { config: block.config })
        app.mount(container)
      }
    }, 0)
  })
}

// Computed
const renderedHtml = computed(() => {
  if (!props.content) {
    return '<p class="empty-content">No content to display</p>'
  }

  try {
    const html = marked(props.content) as string
    
    // Parse and handle custom blocks first
    const { html: htmlWithPlaceholders, blocks } = parseCustomBlocks(html)
    
    // Apply syntax highlighting to remaining standard code blocks
    const parser = new DOMParser()
    const doc = parser.parseFromString(htmlWithPlaceholders, "text/html")
    const codeBlocks = doc.querySelectorAll("pre code")
    codeBlocks.forEach((block) => {
      const code = block.textContent || ""
      const language = extractLanguage(block.className)

      let highlighted
      if (language) {
        // Use specified language for highlighting
        try {
          highlighted = hljs.highlight(code, {
            language,
            ignoreIllegals: true,
          })
        } catch {
          // Fallback to auto-detection if language is not supported
          highlighted = hljs.highlightAuto(code)
        }
      } else {
        // Auto-detect language
        highlighted = hljs.highlightAuto(code)
      }

      // Create a new element to safely set the highlighted HTML
      const highlightedElement = document.createElement("code")
      highlightedElement.innerHTML = highlighted.value
      // Copy classes and add hljs class
      highlightedElement.className = block.className + " hljs"
      // Replace the code block
      block.parentNode?.replaceChild(highlightedElement, block)
    })
    
    const finalHtml = doc.body.innerHTML
    
    // Mount custom blocks after HTML is rendered
    if (blocks.length > 0) {
      mountCustomBlocks(blocks)
    }
    
    return finalHtml
  } catch (e) {
    console.error("Markdown parsing error:", e)
    return '<p class="error-content">Error rendering markdown</p>'
  }
})

// Methods
const copyContent = async () => {
  try {
    await navigator.clipboard.writeText(props.content)
    emit("copy")
  } catch (e) {
    console.error("Copy failed:", e)
  }
}

// Lifecycle
onMounted(() => {
  configureMarked()
})

// Watch for extension changes
watch(
  () => props.extensions,
  () => {
    configureMarked()
  },
  { deep: true }
)

// Watch for context changes (workspace/notebook)
watch(
  () => [props.workspaceId, props.notebookId, props.currentFilePath],
  () => {
    configureMarked()
  }
)
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

/* Syntax highlighting - Light theme */
.code-theme-light :deep(.hljs-keyword),
.code-theme-light :deep(.hljs-selector-tag),
.code-theme-light :deep(.hljs-literal),
.code-theme-light :deep(.hljs-section),
.code-theme-light :deep(.hljs-link) {
  color: #d73a49;
}

.code-theme-light :deep(.hljs-string),
.code-theme-light :deep(.hljs-title),
.code-theme-light :deep(.hljs-name),
.code-theme-light :deep(.hljs-type),
.code-theme-light :deep(.hljs-attribute),
.code-theme-light :deep(.hljs-symbol),
.code-theme-light :deep(.hljs-bullet),
.code-theme-light :deep(.hljs-addition),
.code-theme-light :deep(.hljs-variable),
.code-theme-light :deep(.hljs-template-tag),
.code-theme-light :deep(.hljs-template-variable) {
  color: #032f62;
}

.code-theme-light :deep(.hljs-comment),
.code-theme-light :deep(.hljs-quote),
.code-theme-light :deep(.hljs-deletion),
.code-theme-light :deep(.hljs-meta) {
  color: #6a737d;
}

.code-theme-light :deep(.hljs-function),
.code-theme-light :deep(.hljs-title.function_) {
  color: #6f42c1;
}

.code-theme-light :deep(.hljs-number),
.code-theme-light :deep(.hljs-regexp),
.code-theme-light :deep(.hljs-built_in),
.code-theme-light :deep(.hljs-class) {
  color: #005cc5;
}

.code-theme-light :deep(.hljs-attr) {
  color: #005cc5;
}

/* Syntax highlighting - Dark theme */
.code-theme-dark :deep(.hljs-keyword),
.code-theme-dark :deep(.hljs-selector-tag),
.code-theme-dark :deep(.hljs-literal),
.code-theme-dark :deep(.hljs-section),
.code-theme-dark :deep(.hljs-link) {
  color: #ff7b72;
}

.code-theme-dark :deep(.hljs-string),
.code-theme-dark :deep(.hljs-title),
.code-theme-dark :deep(.hljs-name),
.code-theme-dark :deep(.hljs-type),
.code-theme-dark :deep(.hljs-attribute),
.code-theme-dark :deep(.hljs-symbol),
.code-theme-dark :deep(.hljs-bullet),
.code-theme-dark :deep(.hljs-addition),
.code-theme-dark :deep(.hljs-variable),
.code-theme-dark :deep(.hljs-template-tag),
.code-theme-dark :deep(.hljs-template-variable) {
  color: #a5d6ff;
}

.code-theme-dark :deep(.hljs-comment),
.code-theme-dark :deep(.hljs-quote),
.code-theme-dark :deep(.hljs-deletion),
.code-theme-dark :deep(.hljs-meta) {
  color: #8b949e;
}

.code-theme-dark :deep(.hljs-function),
.code-theme-dark :deep(.hljs-title.function_) {
  color: #d2a8ff;
}

.code-theme-dark :deep(.hljs-number),
.code-theme-dark :deep(.hljs-regexp),
.code-theme-dark :deep(.hljs-built_in),
.code-theme-dark :deep(.hljs-class) {
  color: #79c0ff;
}

.code-theme-dark :deep(.hljs-attr) {
  color: #79c0ff;
}

/* Dark theme code block background */
.code-theme-dark :deep(pre) {
  background: #0d1117;
  color: #c9d1d9;
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

/* Plugin block fallback styles */
.markdown-content :deep(.plugin-fallback-block) {
  border: 2px dashed var(--color-border-medium);
  border-radius: var(--radius-md);
  padding: var(--spacing-lg);
  margin: var(--spacing-lg) 0;
  background: var(--color-bg-secondary);
}

.markdown-content :deep(.plugin-fallback-block .block-header) {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-md);
  font-weight: var(--font-semibold);
  color: var(--color-text-secondary);
}

.markdown-content :deep(.plugin-fallback-block .block-icon) {
  font-size: var(--text-xl);
}

.markdown-content :deep(.plugin-fallback-block .block-note) {
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
}

.markdown-content :deep(.plugin-fallback-block .config-preview) {
  margin-top: var(--spacing-sm);
  padding: var(--spacing-sm);
  background: var(--color-bg-primary);
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
  overflow-x: auto;
}

.markdown-content :deep(.loading-block) {
  border: 2px solid var(--color-border-light);
  border-radius: var(--radius-md);
  padding: var(--spacing-lg);
  margin: var(--spacing-lg) 0;
  background: var(--color-bg-secondary);
  color: var(--color-text-secondary);
  text-align: center;
  font-style: italic;
}
</style>
