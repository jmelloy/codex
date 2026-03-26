<template>
  <div class="link-editor-overlay" @mousedown.self="$emit('close')">
    <div
      class="link-editor"
      :style="positionStyle"
    >
      <div class="link-editor-header">
        <input
          ref="searchInput"
          v-model="query"
          class="link-search-input"
          placeholder="Search pages..."
          @keydown="handleKeydown"
        />
      </div>
      <div class="link-editor-results" ref="resultsRef">
        <div v-if="filteredPages.length === 0" class="link-editor-empty">
          No pages found
        </div>
        <button
          v-for="(page, index) in filteredPages"
          :key="page.block_id || page.path"
          class="link-result-item"
          :class="{ active: index === selectedIndex }"
          @mousedown.prevent="selectPage(page)"
          @mouseenter="selectedIndex = index"
        >
          <span class="link-result-icon">{{ getPageIcon(page) }}</span>
          <div class="link-result-info">
            <span class="link-result-title">{{ page.title || page.name || page.path }}</span>
            <span v-if="page.path" class="link-result-path">{{ page.path }}</span>
          </div>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, nextTick } from "vue"
import type { BlockTreeNode } from "../utils/blockTree"

interface Props {
  pages: BlockTreeNode[]
  anchorRect?: { top: number; left: number; bottom: number }
}

const props = defineProps<Props>()

const emit = defineEmits<{
  select: [page: BlockTreeNode]
  close: []
}>()

const searchInput = ref<HTMLInputElement | null>(null)
const resultsRef = ref<HTMLDivElement | null>(null)
const query = ref("")
const selectedIndex = ref(0)

/** Flatten pages tree into a flat list of all pages */
function flattenPages(nodes: BlockTreeNode[]): BlockTreeNode[] {
  const result: BlockTreeNode[] = []
  function walk(items: BlockTreeNode[]) {
    for (const item of items) {
      if (item.isPage || item.type === "page") {
        result.push(item)
      }
      if (item.children) {
        walk(item.children)
      }
    }
  }
  walk(nodes)
  return result
}

const allPages = computed(() => flattenPages(props.pages))

const filteredPages = computed(() => {
  const q = query.value.toLowerCase().trim()
  if (!q) return allPages.value
  return allPages.value.filter((p) => {
    const title = (p.title || p.name || "").toLowerCase()
    const path = (p.path || "").toLowerCase()
    return title.includes(q) || path.includes(q)
  })
})

watch(filteredPages, () => {
  selectedIndex.value = 0
})

const positionStyle = computed(() => {
  if (!props.anchorRect) return {}
  return {
    top: `${props.anchorRect.bottom + 4}px`,
    left: `${props.anchorRect.left}px`,
  }
})

function getPageIcon(page: BlockTreeNode): string {
  const props = page.pageMeta?.properties || page.block?.properties
  if (props && typeof props === "object" && "icon" in props) {
    return props.icon as string
  }
  return "\uD83D\uDCC4"
}

function selectPage(page: BlockTreeNode) {
  emit("select", page)
}

function handleKeydown(event: KeyboardEvent) {
  if (event.key === "ArrowDown") {
    event.preventDefault()
    if (selectedIndex.value < filteredPages.value.length - 1) {
      selectedIndex.value++
      scrollToSelected()
    }
  } else if (event.key === "ArrowUp") {
    event.preventDefault()
    if (selectedIndex.value > 0) {
      selectedIndex.value--
      scrollToSelected()
    }
  } else if (event.key === "Enter") {
    event.preventDefault()
    const page = filteredPages.value[selectedIndex.value]
    if (page) selectPage(page)
  } else if (event.key === "Escape") {
    event.preventDefault()
    emit("close")
  }
}

function scrollToSelected() {
  nextTick(() => {
    const container = resultsRef.value
    if (!container) return
    const items = container.querySelectorAll(".link-result-item")
    const item = items[selectedIndex.value] as HTMLElement | undefined
    if (item) {
      item.scrollIntoView({ block: "nearest" })
    }
  })
}

onMounted(() => {
  nextTick(() => searchInput.value?.focus())
})
</script>

<style scoped>
.link-editor-overlay {
  position: fixed;
  inset: 0;
  z-index: 100;
}

.link-editor {
  position: fixed;
  width: 320px;
  max-height: 340px;
  background: var(--bg-primary, #fff);
  border: 1px solid var(--border-color, #e0e0e0);
  border-radius: 8px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.link-editor-header {
  padding: 8px;
  border-bottom: 1px solid var(--border-color, #e0e0e0);
}

.link-search-input {
  width: 100%;
  padding: 6px 10px;
  border: 1px solid var(--border-color, #e0e0e0);
  border-radius: 6px;
  background: var(--bg-secondary, #fafafa);
  color: var(--text-primary, #333);
  font-size: 0.875rem;
  outline: none;
  box-sizing: border-box;
}

.link-search-input:focus {
  border-color: var(--accent-color, #2563eb);
  box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.15);
}

.link-editor-results {
  overflow-y: auto;
  flex: 1;
  padding: 4px;
}

.link-editor-empty {
  padding: 16px;
  text-align: center;
  color: var(--text-tertiary, #999);
  font-size: 0.8125rem;
}

.link-result-item {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 6px 10px;
  border: none;
  background: transparent;
  color: var(--text-primary, #333);
  cursor: pointer;
  border-radius: 4px;
  font-size: 0.8125rem;
  text-align: left;
}

.link-result-item:hover,
.link-result-item.active {
  background: var(--hover-bg, #f5f5f5);
}

.link-result-icon {
  font-size: 1rem;
  flex-shrink: 0;
  width: 20px;
  text-align: center;
}

.link-result-info {
  display: flex;
  flex-direction: column;
  min-width: 0;
  flex: 1;
}

.link-result-title {
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.link-result-path {
  font-size: 0.6875rem;
  color: var(--text-tertiary, #999);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
