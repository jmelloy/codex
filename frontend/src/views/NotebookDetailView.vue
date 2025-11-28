<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useNotebooksStore } from '@/stores/notebooks'
import { pagesApi } from '@/api'
import type { Page } from '@/types'

const route = useRoute()
const notebooksStore = useNotebooksStore()

const pages = ref<Page[]>([])
const loading = ref(true)

const notebookId = computed(() => route.params.notebookId as string)
const notebook = computed(() => notebooksStore.notebooks.get(notebookId.value))

onMounted(async () => {
  await notebooksStore.loadNotebook(notebookId.value)
  try {
    pages.value = await pagesApi.list(notebooksStore.workspacePath, notebookId.value)
  } catch (e) {
    console.error('Failed to load pages:', e)
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="notebook-detail" v-if="notebook">
    <header class="page-header">
      <div>
        <RouterLink to="/notebooks" class="back-link">← Back to Notebooks</RouterLink>
        <h1>{{ notebook.title }}</h1>
        <p v-if="notebook.description" class="description">{{ notebook.description }}</p>
        <div v-if="notebook.tags.length > 0" class="tags">
          <span v-for="tag in notebook.tags" :key="tag" class="tag">{{ tag }}</span>
        </div>
      </div>
      <button class="btn btn-primary">+ New Page</button>
    </header>

    <section class="pages-section">
      <h2>Pages</h2>

      <div v-if="loading" class="loading">Loading pages...</div>

      <div v-else-if="pages.length === 0" class="empty">
        <p>No pages in this notebook yet.</p>
      </div>

      <div v-else class="pages-list">
        <RouterLink
          v-for="page in pages"
          :key="page.id"
          :to="`/notebooks/${notebookId}/pages/${page.id}`"
          class="page-card card"
        >
          <div class="page-date">{{ page.date ? new Date(page.date).toLocaleDateString() : 'Undated' }}</div>
          <h3>{{ page.title }}</h3>
          <p v-if="page.narrative?.goals" class="goals">{{ page.narrative.goals }}</p>
          <div v-if="page.tags.length > 0" class="tags">
            <span v-for="tag in page.tags" :key="tag" class="tag">{{ tag }}</span>
          </div>
        </RouterLink>
      </div>
    </section>
  </div>

  <div v-else-if="loading" class="loading">Loading notebook...</div>
</template>

<style scoped>
.back-link {
  color: var(--color-text-secondary);
  display: inline-block;
  margin-bottom: 0.5rem;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 2rem;
}

.description {
  color: var(--color-text-secondary);
  margin-top: 0.5rem;
}

.tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-top: 0.75rem;
}

.pages-section h2 {
  margin-bottom: 1rem;
}

.pages-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.page-card {
  display: block;
  text-decoration: none;
  color: inherit;
  transition: transform 0.2s, box-shadow 0.2s;
}

.page-card:hover {
  transform: translateX(4px);
  box-shadow: var(--shadow-md);
  text-decoration: none;
}

.page-date {
  font-size: 0.875rem;
  color: var(--color-text-secondary);
  margin-bottom: 0.25rem;
}

.page-card h3 {
  color: var(--color-primary);
  margin-bottom: 0.5rem;
}

.goals {
  color: var(--color-text-secondary);
  margin-bottom: 0.75rem;
}

.loading,
.empty {
  text-align: center;
  padding: 3rem;
  color: var(--color-text-secondary);
}
</style>
