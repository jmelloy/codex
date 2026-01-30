<template>
  <div class="page-list">
    <div class="page-list-header">
      <h2>Pages</h2>
      <button @click="$emit('create-page')" class="create-page-btn">
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <line x1="12" y1="5" x2="12" y2="19"></line>
          <line x1="5" y1="12" x2="19" y2="12"></line>
        </svg>
        New Page
      </button>
    </div>

    <div v-if="loading" class="loading">Loading pages...</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else-if="pages.length === 0" class="empty">
      No pages yet. Create your first page to get started!
    </div>
    <div v-else class="pages-grid">
      <div
        v-for="page in pages"
        :key="page.id"
        class="page-card"
        @click="$emit('select-page', page)"
      >
        <div class="page-card-header">
          <h3>{{ page.title || "Untitled Page" }}</h3>
          <span class="block-count">{{ page.block_count }} blocks</span>
        </div>
        <p v-if="page.description" class="page-description">{{ page.description }}</p>
        <div class="page-card-footer">
          <span class="page-date">{{ formatDate(page.updated_at) }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from "vue"
import { pageService, type PageListItem } from "../services/codex"

const props = defineProps<{
  notebookId: number
  workspaceId: number
}>()

const emit = defineEmits<{
  (e: "create-page"): void
  (e: "select-page", page: PageListItem): void
}>()

const pages = ref<PageListItem[]>([])
const loading = ref(true)
const error = ref<string | null>(null)

const formatDate = (dateStr: string) => {
  const date = new Date(dateStr)
  return date.toLocaleDateString()
}

const loadPages = async () => {
  loading.value = true
  error.value = null
  try {
    pages.value = await pageService.list(props.notebookId, props.workspaceId)
  } catch (err: any) {
    error.value = err.response?.data?.detail || "Failed to load pages"
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadPages()
})

defineExpose({
  loadPages,
})
</script>

<style scoped>
.page-list {
  padding: 20px;
}

.page-list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-list-header h2 {
  margin: 0;
  font-size: 24px;
  color: var(--page-text);
}

.create-page-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: var(--page-hover);
  border: 1px solid var(--page-border);
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  color: var(--page-text);
  transition: all 0.2s;
}

.create-page-btn:hover {
  background: var(--page-selected);
  transform: translateY(-1px);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.loading,
.error,
.empty {
  padding: 40px;
  text-align: center;
  color: var(--page-text-secondary);
}

.error {
  color: #ef4444;
}

.pages-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;
}

.page-card {
  background: var(--page-background);
  border: 1px solid var(--page-border);
  border-radius: 8px;
  padding: 20px;
  cursor: pointer;
  transition: all 0.2s;
}

.page-card:hover {
  background: var(--page-hover);
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
}

.page-card-header {
  display: flex;
  justify-content: space-between;
  align-items: start;
  margin-bottom: 12px;
}

.page-card-header h3 {
  margin: 0;
  font-size: 18px;
  color: var(--page-text);
}

.block-count {
  font-size: 12px;
  color: var(--page-text-secondary);
  background: var(--page-hover);
  padding: 2px 8px;
  border-radius: 12px;
}

.page-description {
  margin: 0 0 12px 0;
  font-size: 14px;
  color: var(--page-text-secondary);
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.page-card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 12px;
  border-top: 1px solid var(--page-border);
}

.page-date {
  font-size: 12px;
  color: var(--page-text-secondary);
}
</style>
