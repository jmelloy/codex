<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useNotebooksStore } from '@/stores/notebooks'
import { pagesApi, entriesApi } from '@/api'
import type { Page, Entry } from '@/types'

const route = useRoute()
const router = useRouter()
const notebooksStore = useNotebooksStore()

const page = ref<Page | null>(null)
const entries = ref<Entry[]>([])
const loading = ref(true)

const notebookId = computed(() => route.params.notebookId as string)
const pageId = computed(() => route.params.pageId as string)
const notebook = computed(() => notebooksStore.notebooks.get(notebookId.value))

onMounted(async () => {
  await notebooksStore.loadNotebook(notebookId.value)
  try {
    page.value = await pagesApi.get(notebooksStore.workspacePath, pageId.value)
    entries.value = await entriesApi.list(notebooksStore.workspacePath, pageId.value)
  } catch (e) {
    console.error('Failed to load page:', e)
  } finally {
    loading.value = false
  }
})

const getStatusClass = (status: string) => {
  return {
    created: 'status-created',
    running: 'status-running',
    completed: 'status-completed',
    failed: 'status-failed'
  }[status] || ''
}

const getEntryTypeIcon = (entryType: string) => {
  const icons: Record<string, string> = {
    'custom': '📝',
    'api_call': '🌐',
    'database_query': '🗃️',
    'graphql': '◈',
  }
  return icons[entryType] || '📄'
}

const createNewEntry = () => {
  router.push(`/notebooks/${notebookId.value}/pages/${pageId.value}/entries/new`)
}
</script>

<template>
  <div class="page-detail" v-if="page">
    <header class="page-header">
      <div class="breadcrumb">
        <RouterLink to="/notebooks">Notebooks</RouterLink>
        <span>/</span>
        <RouterLink :to="`/notebooks/${notebookId}`">{{ notebook?.title }}</RouterLink>
        <span>/</span>
        <span>{{ page.title }}</span>
      </div>

      <div class="title-row">
        <h1>{{ page.title }}</h1>
        <span class="date">{{ page.date ? new Date(page.date).toLocaleDateString() : 'Undated' }}</span>
      </div>

      <div v-if="page.tags.length > 0" class="tags">
        <span v-for="tag in page.tags" :key="tag" class="tag">{{ tag }}</span>
      </div>
    </header>

    <section class="narrative-section card" v-if="Object.values(page.narrative || {}).some(Boolean)">
      <h2>Narrative</h2>
      <div class="narrative-fields">
        <div v-if="page.narrative?.goals" class="narrative-field">
          <h4>Goals</h4>
          <p>{{ page.narrative.goals }}</p>
        </div>
        <div v-if="page.narrative?.hypothesis" class="narrative-field">
          <h4>Hypothesis</h4>
          <p>{{ page.narrative.hypothesis }}</p>
        </div>
        <div v-if="page.narrative?.observations" class="narrative-field">
          <h4>Observations</h4>
          <p>{{ page.narrative.observations }}</p>
        </div>
        <div v-if="page.narrative?.conclusions" class="narrative-field">
          <h4>Conclusions</h4>
          <p>{{ page.narrative.conclusions }}</p>
        </div>
        <div v-if="page.narrative?.next_steps" class="narrative-field">
          <h4>Next Steps</h4>
          <p>{{ page.narrative.next_steps }}</p>
        </div>
      </div>
    </section>

    <section class="entries-section">
      <div class="section-header">
        <h2>Entries ({{ entries.length }})</h2>
        <button class="btn btn-primary" @click="createNewEntry">+ New Entry</button>
      </div>

      <div v-if="entries.length === 0" class="empty">
        <p>No entries in this page yet.</p>
        <p>Create your first entry to start documenting your work.</p>
        <button class="btn btn-primary" @click="createNewEntry">Create Entry</button>
      </div>

      <div v-else class="entries-list">
        <div v-for="entry in entries" :key="entry.id" class="entry-card card">
          <div class="entry-header">
            <div class="entry-info">
              <span class="entry-type">
                <span class="entry-type-icon">{{ getEntryTypeIcon(entry.entry_type) }}</span>
                {{ entry.entry_type }}
              </span>
              <h3>{{ entry.title }}</h3>
            </div>
            <span class="entry-status" :class="getStatusClass(entry.status)">
              {{ entry.status }}
            </span>
          </div>

          <div class="entry-meta">
            <span>Created: {{ new Date(entry.created_at).toLocaleString() }}</span>
            <span v-if="entry.parent_id">Parent: {{ entry.parent_id }}</span>
          </div>

          <div v-if="entry.metadata?.tags?.length" class="tags">
            <span v-for="tag in entry.metadata.tags" :key="tag" class="tag">{{ tag }}</span>
          </div>

          <div class="entry-actions">
            <button class="btn btn-secondary" v-if="entry.status === 'created'">Execute</button>
            <button class="btn btn-secondary">Create Variation</button>
            <button class="btn btn-secondary">View Lineage</button>
          </div>
        </div>
      </div>
    </section>
  </div>

  <div v-else-if="loading" class="loading">Loading page...</div>
</template>

<style scoped>
.breadcrumb {
  display: flex;
  gap: 0.5rem;
  color: var(--color-text-secondary);
  margin-bottom: 1rem;
}

.breadcrumb a {
  color: var(--color-text-secondary);
}

.breadcrumb a:hover {
  color: var(--color-primary);
}

.title-row {
  display: flex;
  align-items: baseline;
  gap: 1rem;
  margin-bottom: 0.5rem;
}

.date {
  color: var(--color-text-secondary);
  font-size: 1rem;
}

.tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-top: 0.75rem;
}

.page-header {
  margin-bottom: 2rem;
}

.narrative-section {
  margin-bottom: 2rem;
}

.narrative-section h2 {
  margin-bottom: 1rem;
}

.narrative-fields {
  display: grid;
  gap: 1rem;
}

.narrative-field h4 {
  color: var(--color-text-secondary);
  font-size: 0.875rem;
  margin-bottom: 0.25rem;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.entries-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.entry-card {
  transition: transform 0.2s, box-shadow 0.2s;
}

.entry-card:hover {
  box-shadow: var(--shadow-md);
}

.entry-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 0.75rem;
}

.entry-type {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  font-size: 0.75rem;
  text-transform: uppercase;
  color: var(--color-text-secondary);
  letter-spacing: 0.05em;
}

.entry-info h3 {
  margin-top: 0.25rem;
}

.entry-status {
  padding: 0.25rem 0.75rem;
  border-radius: var(--radius-sm);
  font-size: 0.875rem;
  font-weight: 500;
}

.status-created {
  background: #e0e7ff;
  color: #4338ca;
}

.status-running {
  background: #fef3c7;
  color: #b45309;
}

.status-completed {
  background: #dcfce7;
  color: #15803d;
}

.status-failed {
  background: #fee2e2;
  color: #b91c1c;
}

.entry-meta {
  display: flex;
  gap: 1.5rem;
  font-size: 0.875rem;
  color: var(--color-text-secondary);
  margin-bottom: 0.75rem;
}

.entry-actions {
  display: flex;
  gap: 0.5rem;
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid var(--color-border);
}

.loading,
.empty {
  text-align: center;
  padding: 3rem;
  color: var(--color-text-secondary);
}
</style>
