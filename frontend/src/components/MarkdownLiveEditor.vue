<template>
  <div
    class="markdown-live-editor notebook-page"
    :class="themeStore.theme.className"
  >
    <div
      ref="editorRef"
      class="live-editor-content notebook-content"
      contenteditable="true"
      @input="handleInput"
      @keydown="handleKeydown"
      @paste="handlePaste"
      @drop="handleDrop"
      @dragover="handleDragOver"
      @dragleave="handleDragLeave"
      @blur="handleBlur"
      :data-placeholder="placeholder"
      :class="{ 'drag-over': isDragOver }"
    ></div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, nextTick } from "vue"
import { useThemeStore } from "../stores/theme"

const themeStore = useThemeStore()

// Props
interface Props {
  modelValue: string
  placeholder?: string
  onImageUpload?: (file: File) => Promise<string | null>
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: "",
  placeholder: "Start writing...",
})

// Emits
const emit = defineEmits<{
  "update:modelValue": [value: string]
  change: [content: string]
}>()

// Refs
const editorRef = ref<HTMLDivElement | null>(null)
const isComposing = ref(false)
const lastContent = ref("")
const isDragOver = ref(false)

// Image MIME types we accept
const IMAGE_TYPES = ["image/png", "image/jpeg", "image/gif", "image/webp", "image/svg+xml"]

const isImageFile = (file: File): boolean => IMAGE_TYPES.includes(file.type)

// Block type patterns - detect markdown syntax at start of line
const blockPatterns = [
  { pattern: /^#{6}\s/, type: "h6", prefix: "###### " },
  { pattern: /^#{5}\s/, type: "h5", prefix: "##### " },
  { pattern: /^#{4}\s/, type: "h4", prefix: "#### " },
  { pattern: /^#{3}\s/, type: "h3", prefix: "### " },
  { pattern: /^#{2}\s/, type: "h2", prefix: "## " },
  { pattern: /^#\s/, type: "h1", prefix: "# " },
  { pattern: /^>\s/, type: "blockquote", prefix: "> " },
  { pattern: /^[-*]\s/, type: "ul", prefix: "- " },
  { pattern: /^\d+\.\s/, type: "ol", prefix: "1. " },
  { pattern: /^```/, type: "code", prefix: "```" },
]

// Convert markdown to HTML blocks for live editing
const markdownToBlocks = (markdown: string): string => {
  if (!markdown.trim()) {
    return '<div class="block block-p" data-type="p"><br></div>'
  }

  const lines = markdown.split("\n")
  const blocks: string[] = []
  let inCodeBlock = false
  let codeContent: string[] = []
  let codeLanguage = ""

  for (const line of lines) {
    // Handle code blocks
    if (line.startsWith("```")) {
      if (!inCodeBlock) {
        inCodeBlock = true
        codeLanguage = line.slice(3).trim()
        codeContent = []
      } else {
        // End of code block
        blocks.push(
          `<div class="block block-code" data-type="code" data-language="${codeLanguage}"><pre><code>${escapeHtml(codeContent.join("\n"))}</code></pre></div>`
        )
        inCodeBlock = false
        codeLanguage = ""
      }
      continue
    }

    if (inCodeBlock) {
      codeContent.push(line)
      continue
    }

    // Handle other block types
    let matched = false
    for (const { pattern, type } of blockPatterns) {
      if (type === "code") continue // Skip code pattern here
      if (pattern.test(line)) {
        const content = line.replace(pattern, "")
        const htmlContent = formatInlineContent(content) || "<br>"
        blocks.push(
          `<div class="block block-${type}" data-type="${type}">${htmlContent}</div>`
        )
        matched = true
        break
      }
    }

    if (!matched) {
      // Regular paragraph
      const content = formatInlineContent(line)
      if (content || blocks.length === 0) {
        blocks.push(
          `<div class="block block-p" data-type="p">${content || "<br>"}</div>`
        )
      } else if (line === "") {
        // Empty line creates empty paragraph
        blocks.push('<div class="block block-p" data-type="p"><br></div>')
      }
    }
  }

  // Handle unclosed code block
  if (inCodeBlock && codeContent.length > 0) {
    blocks.push(
      `<div class="block block-code" data-type="code" data-language="${codeLanguage}"><pre><code>${escapeHtml(codeContent.join("\n"))}</code></pre></div>`
    )
  }

  return blocks.join("") || '<div class="block block-p" data-type="p"><br></div>'
}

// Format inline markdown (bold, italic, code, links)
const formatInlineContent = (text: string): string => {
  if (!text) return ""

  let result = escapeHtml(text)

  // Code (must be first to prevent conflicts)
  result = result.replace(
    /`([^`]+)`/g,
    '<code class="inline-code">$1</code>'
  )

  // Bold with ** or __
  result = result.replace(
    /\*\*([^*]+)\*\*/g,
    '<strong class="inline-bold">$1</strong>'
  )
  result = result.replace(
    /__([^_]+)__/g,
    '<strong class="inline-bold">$1</strong>'
  )

  // Italic with * or _
  result = result.replace(
    /\*([^*]+)\*/g,
    '<em class="inline-italic">$1</em>'
  )
  result = result.replace(
    /_([^_]+)_/g,
    '<em class="inline-italic">$1</em>'
  )

  // Links
  result = result.replace(
    /\[([^\]]+)\]\(([^)]+)\)/g,
    '<a href="$2" class="inline-link">$1</a>'
  )

  return result
}

// Convert blocks back to markdown
const blocksToMarkdown = (): string => {
  if (!editorRef.value) return ""

  const blocks = editorRef.value.querySelectorAll(".block")
  const lines: string[] = []

  blocks.forEach((block) => {
    const type = block.getAttribute("data-type") || "p"
    let content = ""

    if (type === "code") {
      const code = block.querySelector("code")
      const language = block.getAttribute("data-language") || ""
      content = code?.textContent || ""
      lines.push("```" + language)
      lines.push(content)
      lines.push("```")
      return
    }

    // Get text content and convert inline formatting back to markdown
    content = extractMarkdownFromElement(block as HTMLElement)

    // Add block prefix
    switch (type) {
      case "h1":
        lines.push("# " + content)
        break
      case "h2":
        lines.push("## " + content)
        break
      case "h3":
        lines.push("### " + content)
        break
      case "h4":
        lines.push("#### " + content)
        break
      case "h5":
        lines.push("##### " + content)
        break
      case "h6":
        lines.push("###### " + content)
        break
      case "blockquote":
        lines.push("> " + content)
        break
      case "ul":
        lines.push("- " + content)
        break
      case "ol":
        lines.push("1. " + content)
        break
      default:
        lines.push(content)
    }
  })

  return lines.join("\n")
}

// Extract markdown from HTML element (convert inline formatting back)
const extractMarkdownFromElement = (element: HTMLElement): string => {
  let result = ""

  element.childNodes.forEach((node) => {
    if (node.nodeType === Node.TEXT_NODE) {
      result += node.textContent || ""
    } else if (node.nodeType === Node.ELEMENT_NODE) {
      const el = node as HTMLElement
      const tagName = el.tagName.toLowerCase()
      const content = extractMarkdownFromElement(el)

      switch (tagName) {
        case "strong":
        case "b":
          result += `**${content}**`
          break
        case "em":
        case "i":
          result += `*${content}*`
          break
        case "code":
          result += `\`${content}\``
          break
        case "a":
          const href = el.getAttribute("href") || ""
          result += `[${content}](${href})`
          break
        case "br":
          // Don't add content for br
          break
        default:
          result += content
      }
    }
  })

  return result
}

// Escape HTML special characters
const escapeHtml = (text: string): string => {
  const div = document.createElement("div")
  div.textContent = text
  return div.innerHTML
}

// Handle input events
const handleInput = () => {
  if (isComposing.value) return

  // Check for block type conversion
  checkBlockConversion()

  // Emit updated content
  emitContent()
}

// Check if current block should be converted based on typed prefix
const checkBlockConversion = () => {
  const selection = window.getSelection()
  if (!selection || !selection.rangeCount) return

  const range = selection.getRangeAt(0)
  const block = findParentBlock(range.startContainer)
  if (!block) return

  const currentType = block.getAttribute("data-type")
  const text = block.textContent || ""

  // Only check for conversion in paragraph blocks
  if (currentType !== "p") return

  for (const { pattern, type } of blockPatterns) {
    if (type === "code") {
      // Special handling for code blocks
      if (text.startsWith("```")) {
        convertToCodeBlock(block, text.slice(3))
        return
      }
      continue
    }

    if (pattern.test(text)) {
      // Convert block type
      const newContent = text.replace(pattern, "")
      convertBlock(block, type, newContent)
      return
    }
  }
}

// Convert a block to a new type
const convertBlock = (
  block: Element,
  newType: string,
  content: string
) => {
  block.className = `block block-${newType}`
  block.setAttribute("data-type", newType)

  // Set content and place cursor at end
  const formattedContent = formatInlineContent(content)
  block.innerHTML = formattedContent || "<br>"

  // Move cursor to end
  nextTick(() => {
    placeCursorAtEnd(block)
  })
}

// Convert to code block
const convertToCodeBlock = (block: Element, language: string) => {
  block.className = "block block-code"
  block.setAttribute("data-type", "code")
  block.setAttribute("data-language", language.trim())
  block.innerHTML = "<pre><code><br></code></pre>"

  nextTick(() => {
    const code = block.querySelector("code")
    if (code) {
      placeCursorAtEnd(code)
    }
  })
}

// Find parent block element
const findParentBlock = (node: Node | null): Element | null => {
  while (node && node !== editorRef.value) {
    if (node instanceof Element && node.classList.contains("block")) {
      return node
    }
    node = node.parentNode
  }
  return null
}

// Place cursor at end of element
const placeCursorAtEnd = (element: Element | Node) => {
  const range = document.createRange()
  const selection = window.getSelection()

  range.selectNodeContents(element)
  range.collapse(false)

  selection?.removeAllRanges()
  selection?.addRange(range)
}

// Handle keydown events
const handleKeydown = (e: KeyboardEvent) => {
  // Handle Enter key
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault()
    handleEnter()
    return
  }

  // Handle Backspace at start of block
  if (e.key === "Backspace") {
    handleBackspace(e)
    return
  }

  // Handle Tab for indentation
  if (e.key === "Tab") {
    e.preventDefault()
    document.execCommand("insertText", false, "  ")
    return
  }

  // Keyboard shortcuts for formatting
  if (e.ctrlKey || e.metaKey) {
    switch (e.key.toLowerCase()) {
      case "b":
        e.preventDefault()
        toggleInlineFormat("bold")
        break
      case "i":
        e.preventDefault()
        toggleInlineFormat("italic")
        break
      case "`":
        e.preventDefault()
        toggleInlineFormat("code")
        break
    }
  }
}

// Handle Enter key - create new block
const handleEnter = () => {
  const selection = window.getSelection()
  if (!selection || !selection.rangeCount) return

  const range = selection.getRangeAt(0)
  const currentBlock = findParentBlock(range.startContainer)

  if (!currentBlock) return

  const currentType = currentBlock.getAttribute("data-type")

  // For code blocks, insert newline instead of new block
  if (currentType === "code") {
    document.execCommand("insertText", false, "\n")
    return
  }

  // Check if we're at the end of the block
  const isAtEnd = isCaretAtEnd(currentBlock)

  // Create new paragraph block
  const newBlock = document.createElement("div")
  newBlock.className = "block block-p"
  newBlock.setAttribute("data-type", "p")
  newBlock.innerHTML = "<br>"

  // If not at end, split the content
  if (!isAtEnd) {
    // Extract content after cursor
    range.setEndAfter(currentBlock.lastChild || currentBlock)
    const afterContent = range.extractContents()

    // Put remaining content in new block
    if (afterContent.textContent?.trim()) {
      newBlock.innerHTML = ""
      newBlock.appendChild(afterContent)
    }
  }

  // Insert new block after current
  currentBlock.after(newBlock)

  // Move cursor to new block
  nextTick(() => {
    placeCursorAtStart(newBlock)
  })

  emitContent()
}

// Check if caret is at end of element
const isCaretAtEnd = (element: Element): boolean => {
  const selection = window.getSelection()
  if (!selection || !selection.rangeCount) return false

  const range = selection.getRangeAt(0)
  const testRange = document.createRange()
  testRange.selectNodeContents(element)
  testRange.setStart(range.endContainer, range.endOffset)

  return testRange.toString().length === 0
}

// Place cursor at start of element
const placeCursorAtStart = (element: Element) => {
  const range = document.createRange()
  const selection = window.getSelection()

  // Find first text node or use element
  const firstText = findFirstTextNode(element) || element
  range.setStart(firstText, 0)
  range.collapse(true)

  selection?.removeAllRanges()
  selection?.addRange(range)
}

// Find first text node in element
const findFirstTextNode = (element: Node): Text | null => {
  if (element.nodeType === Node.TEXT_NODE) {
    return element as Text
  }
  for (const child of element.childNodes) {
    const found = findFirstTextNode(child)
    if (found) return found
  }
  return null
}

// Handle Backspace - potentially merge or convert blocks
const handleBackspace = (e: KeyboardEvent) => {
  const selection = window.getSelection()
  if (!selection || !selection.rangeCount) return

  const range = selection.getRangeAt(0)
  const block = findParentBlock(range.startContainer)

  if (!block) return

  // Check if at start of block
  const isAtStart = isCaretAtStart(block, range)

  if (!isAtStart) return // Normal backspace behavior

  const blockType = block.getAttribute("data-type")

  // If it's a non-paragraph block, convert to paragraph
  if (blockType !== "p") {
    e.preventDefault()
    block.className = "block block-p"
    block.setAttribute("data-type", "p")
    emitContent()
    return
  }

  // If it's a paragraph at start, try to merge with previous
  const prevBlock = block.previousElementSibling
  if (prevBlock && prevBlock.classList.contains("block")) {
    e.preventDefault()

    // Merge content
    const prevType = prevBlock.getAttribute("data-type")
    if (prevType !== "code") {
      // Get content from current block
      const currentContent = block.innerHTML
      if (currentContent !== "<br>") {
        // Append to previous block
        if (prevBlock.innerHTML === "<br>") {
          prevBlock.innerHTML = currentContent
        } else {
          prevBlock.innerHTML += currentContent
        }
      }

      // Place cursor at merge point and remove block
      placeCursorAtEnd(prevBlock)
      block.remove()
      emitContent()
    }
  }
}

// Check if caret is at start of element
const isCaretAtStart = (element: Element, range: Range): boolean => {
  const testRange = document.createRange()
  testRange.selectNodeContents(element)
  testRange.setEnd(range.startContainer, range.startOffset)

  return testRange.toString().length === 0
}

// Toggle inline formatting
const toggleInlineFormat = (format: "bold" | "italic" | "code") => {
  const selection = window.getSelection()
  if (!selection || selection.rangeCount === 0) return

  const range = selection.getRangeAt(0)
  if (range.collapsed) return // No selection

  const selectedText = range.toString()
  if (!selectedText) return

  let wrapper: HTMLElement
  switch (format) {
    case "bold":
      wrapper = document.createElement("strong")
      wrapper.className = "inline-bold"
      break
    case "italic":
      wrapper = document.createElement("em")
      wrapper.className = "inline-italic"
      break
    case "code":
      wrapper = document.createElement("code")
      wrapper.className = "inline-code"
      break
  }

  // Check if already formatted
  const parentElement = range.commonAncestorContainer.parentElement
  if (
    parentElement &&
    ((format === "bold" &&
      (parentElement.tagName === "STRONG" || parentElement.tagName === "B")) ||
      (format === "italic" &&
        (parentElement.tagName === "EM" || parentElement.tagName === "I")) ||
      (format === "code" && parentElement.tagName === "CODE"))
  ) {
    // Remove formatting
    const text = document.createTextNode(parentElement.textContent || "")
    parentElement.parentNode?.replaceChild(text, parentElement)
  } else {
    // Apply formatting
    range.surroundContents(wrapper)
  }

  emitContent()
}

// Handle paste - convert to plain text, or upload images
const handlePaste = (e: ClipboardEvent) => {
  e.preventDefault()

  // Check for image files in clipboard
  const files = e.clipboardData?.files
  if (files && files.length > 0 && props.onImageUpload) {
    const imageFiles = Array.from(files).filter(isImageFile)
    if (imageFiles.length > 0) {
      uploadAndInsertImages(imageFiles)
      return
    }
  }

  const text = e.clipboardData?.getData("text/plain") || ""
  document.execCommand("insertText", false, text)

  nextTick(() => {
    emitContent()
  })
}

// Handle drag over - show visual feedback
const handleDragOver = (e: DragEvent) => {
  if (!e.dataTransfer) return
  // Only react to files being dragged (not internal text drags)
  if (e.dataTransfer.types.includes("Files")) {
    e.preventDefault()
    e.dataTransfer.dropEffect = "copy"
    isDragOver.value = true
  }
}

// Handle drag leave
const handleDragLeave = () => {
  isDragOver.value = false
}

// Handle drop - upload image files
const handleDrop = (e: DragEvent) => {
  isDragOver.value = false
  if (!e.dataTransfer) return

  const files = e.dataTransfer.files
  if (files.length === 0 || !props.onImageUpload) return

  const imageFiles = Array.from(files).filter(isImageFile)
  if (imageFiles.length === 0) return

  e.preventDefault()

  // Place cursor at drop position
  const range = document.caretRangeFromPoint(e.clientX, e.clientY)
  if (range) {
    const selection = window.getSelection()
    selection?.removeAllRanges()
    selection?.addRange(range)
  }

  uploadAndInsertImages(imageFiles)
}

// Upload image files and insert markdown links at cursor
const uploadAndInsertImages = async (files: File[]) => {
  if (!props.onImageUpload) return

  for (const file of files) {
    // Insert a placeholder while uploading
    const placeholder = `![Uploading ${file.name}...]()`
    document.execCommand("insertText", false, placeholder)
    emitContent()

    try {
      const filename = await props.onImageUpload(file)
      if (filename) {
        // Replace the placeholder with the actual image link
        const markdown = blocksToMarkdown()
        const updated = markdown.replace(placeholder, `![${file.name}](${filename})`)
        lastContent.value = updated
        emit("update:modelValue", updated)
        emit("change", updated)
        // Re-render editor with updated content
        if (editorRef.value) {
          const html = markdownToBlocks(updated)
          editorRef.value.innerHTML = html
          // Place cursor at end
          const lastBlock = editorRef.value.querySelector(".block:last-child")
          if (lastBlock) {
            placeCursorAtEnd(lastBlock)
          }
        }
      }
    } catch (err) {
      // Replace placeholder with error indicator
      const markdown = blocksToMarkdown()
      const updated = markdown.replace(placeholder, `![Failed to upload ${file.name}]()`)
      lastContent.value = updated
      emit("update:modelValue", updated)
      emit("change", updated)
      if (editorRef.value) {
        const html = markdownToBlocks(updated)
        editorRef.value.innerHTML = html
      }
      console.error("Image upload failed:", err)
    }
  }
}

// Handle blur
const handleBlur = () => {
  emitContent()
}

// Emit content as markdown
const emitContent = () => {
  const markdown = blocksToMarkdown()
  if (markdown !== lastContent.value) {
    lastContent.value = markdown
    emit("update:modelValue", markdown)
    emit("change", markdown)
  }
}

// Initialize editor content
const initializeContent = () => {
  if (!editorRef.value) return

  const html = markdownToBlocks(props.modelValue)
  editorRef.value.innerHTML = html
  lastContent.value = props.modelValue
}

// Watch for external value changes
watch(
  () => props.modelValue,
  (newValue) => {
    // Only update if content is different (to avoid cursor jumping)
    if (newValue !== lastContent.value) {
      initializeContent()
    }
  }
)

// Initialize on mount
onMounted(() => {
  initializeContent()

  // Focus the editor
  nextTick(() => {
    if (editorRef.value) {
      const firstBlock = editorRef.value.querySelector(".block")
      if (firstBlock) {
        placeCursorAtEnd(firstBlock)
      }
      editorRef.value.focus()
    }
  })
})

// Expose methods
defineExpose({
  getContent: blocksToMarkdown,
  focus: () => editorRef.value?.focus(),
})
</script>

<style scoped>
.markdown-live-editor {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--color-bg-primary);
  overflow: hidden;
}

.live-editor-content {
  flex: 1;
  padding: var(--spacing-xl) var(--spacing-xl) var(--spacing-xl) 80px;
  overflow-y: auto;
  outline: none;
  font-family: var(--font-serif);
  font-size: var(--text-base);
  line-height: var(--leading-relaxed);
  color: var(--color-text-primary);
}

.live-editor-content:empty::before {
  content: attr(data-placeholder);
  color: var(--color-text-placeholder);
  font-style: italic;
  pointer-events: none;
}

/* Block styles */
.live-editor-content :deep(.block) {
  margin-bottom: var(--spacing-sm);
  min-height: 1.5em;
}

.live-editor-content :deep(.block-h1) {
  font-size: var(--text-3xl);
  font-weight: var(--font-bold);
  margin-top: var(--spacing-xl);
  margin-bottom: var(--spacing-lg);
  border-bottom: 2px solid var(--color-border-light);
  padding-bottom: var(--spacing-sm);
}

.live-editor-content :deep(.block-h2) {
  font-size: var(--text-2xl);
  font-weight: var(--font-semibold);
  margin-top: var(--spacing-lg);
  margin-bottom: var(--spacing-md);
}

.live-editor-content :deep(.block-h3) {
  font-size: var(--text-xl);
  font-weight: var(--font-semibold);
  margin-top: var(--spacing-md);
  margin-bottom: var(--spacing-sm);
}

.live-editor-content :deep(.block-h4) {
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  margin-top: var(--spacing-md);
}

.live-editor-content :deep(.block-h5) {
  font-size: var(--text-base);
  font-weight: var(--font-semibold);
  margin-top: var(--spacing-sm);
}

.live-editor-content :deep(.block-h6) {
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  color: var(--color-text-secondary);
  margin-top: var(--spacing-sm);
}

.live-editor-content :deep(.block-blockquote) {
  border-left: 4px solid var(--color-primary);
  padding-left: var(--spacing-lg);
  color: var(--color-text-secondary);
  font-style: italic;
}

.live-editor-content :deep(.block-ul) {
  padding-left: var(--spacing-xl);
  position: relative;
}

.live-editor-content :deep(.block-ul)::before {
  content: "•";
  position: absolute;
  left: var(--spacing-md);
  color: var(--color-text-secondary);
}

.live-editor-content :deep(.block-ol) {
  padding-left: var(--spacing-xl);
  position: relative;
  counter-increment: list-counter;
}

.live-editor-content :deep(.block-ol)::before {
  content: counter(list-counter) ".";
  position: absolute;
  left: var(--spacing-sm);
  color: var(--color-text-secondary);
}

.live-editor-content :deep(.block-code) {
  background: var(--color-bg-secondary);
  border-radius: var(--radius-md);
  padding: var(--spacing-md);
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  overflow-x: auto;
}

.live-editor-content :deep(.block-code pre) {
  margin: 0;
  white-space: pre-wrap;
}

.live-editor-content :deep(.block-code code) {
  background: transparent;
  padding: 0;
}

/* Inline formatting styles */
.live-editor-content :deep(.inline-bold) {
  font-weight: var(--font-bold);
}

.live-editor-content :deep(.inline-italic) {
  font-style: italic;
}

.live-editor-content :deep(.inline-code) {
  background: var(--color-bg-secondary);
  padding: 0.15rem 0.4rem;
  border-radius: var(--radius-sm);
  font-family: var(--font-mono);
  font-size: 0.9em;
}

.live-editor-content :deep(.inline-link) {
  color: var(--color-primary);
  text-decoration: underline;
  cursor: pointer;
}

/* Selection styling */
.live-editor-content ::selection {
  background: var(--color-primary);
  color: var(--color-text-inverse);
}

/* Focus state */
.live-editor-content:focus {
  outline: none;
}

/* Drag-over state */
.live-editor-content.drag-over {
  background: color-mix(in srgb, var(--color-primary) 5%, var(--color-bg-primary));
  outline: 2px dashed var(--color-primary);
  outline-offset: -4px;
}

/* Placeholder for empty blocks */
.live-editor-content :deep(.block-p:only-child:empty)::before,
.live-editor-content :deep(.block-p:only-child:has(br:only-child))::before {
  content: attr(data-placeholder);
  color: var(--color-text-placeholder);
  font-style: italic;
  pointer-events: none;
}
</style>
