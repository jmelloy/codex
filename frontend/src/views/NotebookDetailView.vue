<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useNotebooksStore } from "@/stores/notebooks";
import { pagesApi } from "@/api";
import type { Page } from "@/types";

const route = useRoute();
const router = useRouter();
const notebooksStore = useNotebooksStore();

const pages = ref<Page[]>([]);
const loading = ref(true);

const showModal = ref(false);
const newPage = ref({
  title: "",
  date: new Date().toISOString().split("T")[0],
  goals: "",
});
const creating = ref(false);

const notebookId = computed(() => route.params.notebookId as string);
const notebook = computed(() => notebooksStore.notebooks.get(notebookId.value));

onMounted(async () => {
  await notebooksStore.loadNotebook(notebookId.value);
  try {
    pages.value = await pagesApi.list(notebookId.value);
  } catch (e) {
    console.error("Failed to load pages:", e);
  } finally {
    loading.value = false;
  }
});

async function handleCreatePage() {
  if (!newPage.value.title.trim()) return;

  creating.value = true;

  try {
    const page = await pagesApi.create(notebookId.value, {
      title: newPage.value.title,
      date: newPage.value.date || undefined,
      narrative: newPage.value.goals ? { goals: newPage.value.goals } : undefined,
    });

    showModal.value = false;
    newPage.value = { title: "", date: new Date().toISOString().split("T")[0], goals: "" };
    router.push(`/notebooks/${notebookId.value}/pages/${page.id}`);
  } catch (e) {
    console.error("Failed to create page:", e);
  } finally {
    creating.value = false;
  }
}

function closeModal() {
  showModal.value = false;
  newPage.value = { title: "", date: new Date().toISOString().split("T")[0], goals: "" };
}
</script>

<template>
  <div class="notebook-detail" v-if="notebook">
    <header class="page-header">
      <div>
        <RouterLink to="/notebooks" class="back-link"
          >← Back to Notebooks</RouterLink
        >
        <h1>{{ notebook.title }}</h1>
        <p v-if="notebook.description" class="description">
          {{ notebook.description }}
        </p>
        <div v-if="notebook.tags.length > 0" class="tags">
          <span v-for="tag in notebook.tags" :key="tag" class="tag">{{
            tag
          }}</span>
        </div>
      </div>
      <button class="btn btn-primary" @click="showModal = true">+ New Page</button>
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
          <div class="page-date">
            {{
              page.date ? new Date(page.date).toLocaleDateString() : "Undated"
            }}
          </div>
          <h3>{{ page.title }}</h3>
          <p v-if="page.narrative?.goals" class="goals">
            {{ page.narrative.goals }}
          </p>
          <div v-if="page.tags.length > 0" class="tags">
            <span v-for="tag in page.tags" :key="tag" class="tag">{{
              tag
            }}</span>
          </div>
        </RouterLink>
      </div>
    </section>

    <!-- Create Page Modal -->
    <div v-if="showModal" class="modal-overlay" @click.self="closeModal">
      <div class="modal">
        <h2>Create New Page</h2>
        <form @submit.prevent="handleCreatePage">
          <div class="form-group">
            <label for="title">Title *</label>
            <input
              id="title"
              v-model="newPage.title"
              type="text"
              placeholder="Session #1"
              required
            />
          </div>
          <div class="form-group">
            <label for="date">Date</label>
            <input
              id="date"
              v-model="newPage.date"
              type="date"
            />
          </div>
          <div class="form-group">
            <label for="goals">Goals</label>
            <textarea
              id="goals"
              v-model="newPage.goals"
              placeholder="What do you want to achieve?"
              rows="3"
            ></textarea>
          </div>
          <div class="modal-actions">
            <button type="button" class="btn" @click="closeModal">Cancel</button>
            <button type="submit" class="btn btn-primary" :disabled="creating">
              {{ creating ? "Creating..." : "Create Page" }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>

  <div v-else-if="loading" class="loading">Loading notebook...</div>
</template>

<style scoped>
.notebook-detail {
  padding: 2rem;
}

.back-link {
  color: var(--color-text-secondary);
  display: inline-block;
  margin-bottom: 0.5rem;
  font-size: 0.9rem;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 2rem;
}

.page-header h1 {
  font-family: var(--font-handwritten);
  font-size: 2.5rem;
  color: var(--color-primary);
}

.description {
  color: var(--color-text-secondary);
  margin-top: 0.5rem;
  font-style: italic;
}

.tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-top: 0.75rem;
}

.pages-section h2 {
  margin-bottom: 1rem;
  font-family: var(--font-handwritten);
  font-size: 1.75rem;
  color: var(--color-text);
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
  transform: translateX(6px);
  box-shadow: var(--shadow-md);
  text-decoration: none;
}

.page-date {
  font-size: 0.8rem;
  color: var(--color-text-secondary);
  margin-bottom: 0.25rem;
  font-family: var(--font-mono);
}

.page-card h3 {
  color: var(--color-primary);
  margin-bottom: 0.5rem;
  font-family: var(--font-handwritten);
  font-size: 1.4rem;
}

.goals {
  color: var(--color-text-secondary);
  margin-bottom: 0.75rem;
  font-style: italic;
}

.loading,
.empty {
  text-align: center;
  padding: 3rem;
  color: var(--color-text-secondary);
  font-style: italic;
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(44, 36, 22, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal {
  background: var(--color-surface);
  background-image: var(--paper-texture);
  padding: 2rem;
  border-radius: var(--radius-lg);
  width: 100%;
  max-width: 500px;
  box-shadow: var(--shadow-lg);
  border: 1px solid var(--color-border);
}

.modal h2 {
  margin-bottom: 1.5rem;
  font-family: var(--font-handwritten);
  font-size: 1.75rem;
  color: var(--color-primary);
}

.form-group {
  margin-bottom: 1rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 500;
  font-size: 0.9rem;
}

.form-group input,
.form-group textarea {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  font-size: 1rem;
  font-family: var(--font-body);
  background: var(--color-surface);
  color: var(--color-text);
}

.form-group input:focus,
.form-group textarea:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 2px rgba(45, 90, 39, 0.1);
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 1rem;
  margin-top: 1.5rem;
}
</style>
