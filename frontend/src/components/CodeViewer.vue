<template>
  <div class="code-viewer" :class="[themeClass]">
    <div class="code-toolbar">
      <div class="code-info">
        <span v-if="filename" class="filename">{{ filename }}</span>
        <span v-if="detectedLanguage" class="language-badge">{{ detectedLanguage }}</span>
      </div>
      <div class="toolbar-actions">
        <button @click="copyCode" class="btn-copy" :title="copied ? 'Copied!' : 'Copy code'">
          {{ copied ? 'Copied!' : 'Copy' }}
        </button>
        <slot name="toolbar-actions"></slot>
      </div>
    </div>
    <div class="code-container" ref="codeContainer">
      <div class="line-numbers" v-if="showLineNumbers" aria-hidden="true">
        <span v-for="n in lineCount" :key="n" class="line-number">{{ n }}</span>
      </div>
      <pre class="code-content"><code ref="codeElement" :class="languageClass" v-html="highlightedCode"></code></pre>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useThemeStore } from '../stores/theme'
import { useCopyToClipboard } from '../composables/useCopyToClipboard'
import { useSyntaxHighlight } from '../composables/useSyntaxHighlight'

const themeStore = useThemeStore()

interface Props {
  content: string
  language?: string
  filename?: string
  showLineNumbers?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  content: '',
  showLineNumbers: true
})

const { copied, copy } = useCopyToClipboard()
const { detectLanguageFromFilename, highlightCode } = useSyntaxHighlight()

// Detect language from filename or use provided language
const detectedLanguage = computed(() => {
  if (props.language) {
    return props.language
  }
  if (props.filename) {
    // Handle special filenames
    const lowerFilename = props.filename.toLowerCase()
    if (lowerFilename === 'dockerfile') return 'dockerfile'
    if (lowerFilename === 'makefile' || lowerFilename === 'gnumakefile') return 'makefile'
    if (lowerFilename.endsWith('.d.ts')) return 'typescript'

    return detectLanguageFromFilename(props.filename) || null
  }
  return null
})

const languageClass = computed(() => {
  return detectedLanguage.value ? `language-${detectedLanguage.value}` : ''
})

const themeClass = computed(() => {
  // Use theme from store - 'light' or 'dark'
  return themeStore.theme.className?.includes('dark') ? 'code-theme-dark' : 'code-theme-light'
})

// Highlight the code
const highlightedCode = computed(() => {
  if (!props.content) {
    return '<span class="hljs-comment">// No content</span>'
  }
  return highlightCode(props.content, detectedLanguage.value || undefined)
})

// Count lines for line numbers
const lineCount = computed(() => {
  if (!props.content) return 1
  return props.content.split('\n').length
})

// Copy code to clipboard
async function copyCode() {
  await copy(props.content)
}
</script>

<style scoped>
.code-viewer {
  display: flex;
  flex-direction: column;
  height: 100%;
  border-radius: var(--radius-lg);
  overflow: hidden;
  box-shadow: var(--shadow-md);
  font-family: var(--font-mono);
}

/* Light theme */
.code-theme-light {
  --code-bg: #f6f8fa;
  --code-text: #24292e;
  --code-line-number: #6e7781;
  --code-line-number-bg: #f0f0f0;
  --code-border: #e1e4e8;
  --code-toolbar-bg: #f6f8fa;
  --code-badge-bg: #e1e4e8;
  --code-badge-text: #57606a;
}

/* Dark theme */
.code-theme-dark {
  --code-bg: #0d1117;
  --code-text: #c9d1d9;
  --code-line-number: #6e7681;
  --code-line-number-bg: #161b22;
  --code-border: #30363d;
  --code-toolbar-bg: #161b22;
  --code-badge-bg: #30363d;
  --code-badge-text: #8b949e;
}

.code-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-sm) var(--spacing-md);
  background: var(--code-toolbar-bg);
  border-bottom: 1px solid var(--code-border);
  min-height: 40px;
}

.code-info {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.filename {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--code-text);
}

.language-badge {
  font-size: var(--text-xs);
  padding: 2px 8px;
  background: var(--code-badge-bg);
  color: var(--code-badge-text);
  border-radius: var(--radius-sm);
  text-transform: uppercase;
  font-weight: var(--font-medium);
}

.toolbar-actions {
  display: flex;
  gap: var(--spacing-sm);
}

.btn-copy {
  padding: var(--spacing-xs) var(--spacing-md);
  font-size: var(--text-sm);
  background: var(--code-badge-bg);
  color: var(--code-badge-text);
  border: 1px solid var(--code-border);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all 0.2s;
}

.btn-copy:hover {
  background: var(--color-primary);
  color: white;
  border-color: var(--color-primary);
}

.code-container {
  flex: 1;
  display: flex;
  overflow: auto;
  background: var(--code-bg);
}

.line-numbers {
  display: flex;
  flex-direction: column;
  padding: var(--spacing-md) 0;
  background: var(--code-line-number-bg);
  border-right: 1px solid var(--code-border);
  user-select: none;
  text-align: right;
  min-width: 50px;
  position: sticky;
  left: 0;
  z-index: 1;
}

.line-number {
  padding: 0 var(--spacing-md);
  font-size: var(--text-sm);
  line-height: 1.5;
  color: var(--code-line-number);
}

.code-content {
  flex: 1;
  margin: 0;
  padding: var(--spacing-md);
  background: transparent;
  overflow: visible;
  font-size: var(--text-sm);
  line-height: 1.5;
  color: var(--code-text);
  tab-size: 4;
}

.code-content code {
  display: block;
  background: transparent;
  padding: 0;
  font-family: inherit;
  white-space: pre;
}

/* highlight.js theme overrides for light mode */
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

/* highlight.js theme overrides for dark mode */
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
</style>
