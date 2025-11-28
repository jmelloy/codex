<script setup lang="ts">
import { onMounted } from 'vue'
import { useNotebooksStore } from '@/stores/notebooks'

const notebooksStore = useNotebooksStore()

onMounted(() => {
  notebooksStore.loadNotebooks()
})
</script>

<template>
  <div class="notebooks-view">
    <header class="page-header">
      <h1>Notebooks</h1>
      <button class="btn btn-primary">+ New Notebook</button>
    </header>

    <div v-if="notebooksStore.loading" class="loading">
      Loading notebooks...
    </div>

    <div v-else-if="notebooksStore.error" class="error">
      {{ notebooksStore.error }}
    </div>

    <div v-else-if="notebooksStore.notebooksList.length === 0" class="empty">
      <p>No notebooks yet.</p>
      <p>Create your first notebook to get started.</p>
    </div>

    <div v-else class="notebooks-grid">
      <RouterLink
        v-for="notebook in notebooksStore.notebooksList"
        :key="notebook.id"
        :to="`/notebooks/${notebook.id}`"
        class="notebook-card card"
      >
        <h3>{{ notebook.title }}</h3>
        <p v-if="notebook.description" class="description">
          {{ notebook.description }}
        </p>
        <div v-if="notebook.tags.length > 0" class="tags">
          <span v-for="tag in notebook.tags" :key="tag" class="tag">
            {{ tag }}
          </span>
        </div>
        <div class="meta">
          Created: {{ new Date(notebook.created_at).toLocaleDateString() }}
        </div>
      </RouterLink>
    </div>
  </div>
</template>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
}

.notebooks-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 1.5rem;
}

.notebook-card {
  display: block;
  text-decoration: none;
  color: inherit;
  transition: transform 0.2s, box-shadow 0.2s;
}

.notebook-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
  text-decoration: none;
}

.notebook-card h3 {
  margin-bottom: 0.5rem;
  color: var(--color-primary);
}

.description {
  color: var(--color-text-secondary);
  margin-bottom: 1rem;
}

.tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.meta {
  font-size: 0.875rem;
  color: var(--color-text-secondary);
}

.loading,
.error,
.empty {
  text-align: center;
  padding: 3rem;
  color: var(--color-text-secondary);
}

.error {
  color: var(--color-error);
}
</style>
