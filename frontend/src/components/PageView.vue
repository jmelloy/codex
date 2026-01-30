<template>
  <div class="page-view">
    <div v-if="loading" class="loading">Loading page...</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else-if="page">
      <!-- Page Header -->
      <div class="page-header">
        <button @click="$emit('back')" class="back-btn">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="20"
            height="20"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <line x1="19" y1="12" x2="5" y2="12"></line>
            <polyline points="12 19 5 12 12 5"></polyline>
          </svg>
          Back
        </button>
        <div class="page-title-section">
          <h1>{{ page.title || "Untitled Page" }}</h1>
          <p v-if="page.description" class="page-description">{{ page.description }}</p>
        </div>
        <button @click="$emit('add-block')" class="add-block-btn">
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
          Add Block
        </button>
      </div>

      <!-- Blocks List -->
      <div v-if="page.blocks.length === 0" class="empty">
        No blocks yet. Add a block to start building your page!
      </div>
      <div v-else class="blocks-list">
        <div
          v-for="block in page.blocks"
          :key="block.position"
          class="block-item"
          @click="$emit('select-block', block)"
        >
          <div class="block-position">{{ block.position }}</div>
          <div class="block-content">
            <div class="block-header">
              <div class="block-icon">
                <svg
                  v-if="block.type === 'markdown'"
                  xmlns="http://www.w3.org/2000/svg"
                  width="20"
                  height="20"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                >
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                  <polyline points="14 2 14 8 20 8"></polyline>
                  <line x1="16" y1="13" x2="8" y2="13"></line>
                  <line x1="16" y1="17" x2="8" y2="17"></line>
                  <polyline points="10 9 9 9 8 9"></polyline>
                </svg>
                <svg
                  v-else
                  xmlns="http://www.w3.org/2000/svg"
                  width="20"
                  height="20"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                >
                  <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"></path>
                  <polyline points="13 2 13 9 20 9"></polyline>
                </svg>
              </div>
              <span class="block-name">{{ block.name }}</span>
            </div>
            <div class="block-type">{{ block.type }}</div>
          </div>
          <button @click.stop="$emit('delete-block', block)" class="delete-block-btn">
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
              <polyline points="3 6 5 6 21 6"></polyline>
              <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
            </svg>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue"
import { pageService, type PageWithBlocks, type Block } from "../services/codex"

const props = defineProps<{
  pageId: number
  workspaceId: number
}>()

const emit = defineEmits<{
  (e: "back"): void
  (e: "add-block"): void
  (e: "select-block", block: Block): void
  (e: "delete-block", block: Block): void
}>()

const page = ref<PageWithBlocks | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)

const loadPage = async () => {
  loading.value = true
  error.value = null
  try {
    page.value = await pageService.get(props.pageId, props.workspaceId)
  } catch (err: any) {
    error.value = err.response?.data?.detail || "Failed to load page"
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadPage()
})

defineExpose({
  loadPage,
})
</script>

<style scoped>
.page-view {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
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

.page-header {
  display: flex;
  align-items: start;
  gap: 20px;
  margin-bottom: 30px;
  padding-bottom: 20px;
  border-bottom: 2px solid var(--page-border);
}

.back-btn,
.add-block-btn {
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

.back-btn:hover,
.add-block-btn:hover {
  background: var(--page-selected);
  transform: translateY(-1px);
}

.page-title-section {
  flex: 1;
}

.page-title-section h1 {
  margin: 0 0 8px 0;
  font-size: 28px;
  color: var(--page-text);
}

.page-description {
  margin: 0;
  font-size: 16px;
  color: var(--page-text-secondary);
  line-height: 1.5;
}

.blocks-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.block-item {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px;
  background: var(--page-background);
  border: 1px solid var(--page-border);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.block-item:hover {
  background: var(--page-hover);
  transform: translateX(4px);
}

.block-position {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  background: var(--page-hover);
  border-radius: 50%;
  font-size: 14px;
  font-weight: bold;
  color: var(--page-text);
}

.block-content {
  flex: 1;
}

.block-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 4px;
}

.block-icon {
  color: var(--page-text-secondary);
}

.block-name {
  font-size: 16px;
  font-weight: 500;
  color: var(--page-text);
}

.block-type {
  font-size: 12px;
  color: var(--page-text-secondary);
}

.delete-block-btn {
  padding: 8px;
  background: transparent;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  color: var(--page-text-secondary);
  transition: all 0.2s;
}

.delete-block-btn:hover {
  background: #fee2e2;
  color: #ef4444;
}
</style>
