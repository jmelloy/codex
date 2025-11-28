<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { useNotebooksStore } from "@/stores/notebooks";

const notebooksStore = useNotebooksStore();
const router = useRouter();

const showModal = ref(false);
const newNotebook = ref({
  title: "",
  description: "",
  tags: "",
});
const creating = ref(false);

onMounted(() => {
  notebooksStore.loadNotebooks();
});

async function handleCreateNotebook() {
  if (!newNotebook.value.title.trim()) return;

  creating.value = true;
  const tags = newNotebook.value.tags
    .split(",")
    .map((t) => t.trim())
    .filter(Boolean);

  const notebook = await notebooksStore.createNotebook(
    newNotebook.value.title,
    newNotebook.value.description,
    tags
  );

  creating.value = false;

  if (notebook) {
    showModal.value = false;
    newNotebook.value = { title: "", description: "", tags: "" };
    router.push(`/notebooks/${notebook.id}`);
  }
}

function closeModal() {
  showModal.value = false;
  newNotebook.value = { title: "", description: "", tags: "" };
}
</script>

<template>
  <div class="notebooks-view">
    <header class="page-header">
      <h1>Notebooks</h1>
      <button class="btn btn-primary" @click="showModal = true">+ New Notebook</button>
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

    <!-- Create Notebook Modal -->
    <div v-if="showModal" class="modal-overlay" @click.self="closeModal">
      <div class="modal">
        <h2>Create New Notebook</h2>
        <form @submit.prevent="handleCreateNotebook">
          <div class="form-group">
            <label for="title">Title *</label>
            <input
              id="title"
              v-model="newNotebook.title"
              type="text"
              placeholder="My Notebook"
              required
            />
          </div>
          <div class="form-group">
            <label for="description">Description</label>
            <textarea
              id="description"
              v-model="newNotebook.description"
              placeholder="What is this notebook about?"
              rows="3"
            ></textarea>
          </div>
          <div class="form-group">
            <label for="tags">Tags (comma-separated)</label>
            <input
              id="tags"
              v-model="newNotebook.tags"
              type="text"
              placeholder="project, research, ideas"
            />
          </div>
          <div class="modal-actions">
            <button type="button" class="btn" @click="closeModal">Cancel</button>
            <button type="submit" class="btn btn-primary" :disabled="creating">
              {{ creating ? "Creating..." : "Create Notebook" }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<style scoped>
.notebooks-view {
  padding: 2rem;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
}

.page-header h1 {
  font-family: var(--font-handwritten);
  font-size: 2.5rem;
  color: var(--color-primary);
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
  transition: transform 0.2s ease, box-shadow 0.2s ease;
  position: relative;
}

.notebook-card:hover {
  transform: rotate(-1deg) translateY(-4px);
  box-shadow: var(--shadow-lg);
  text-decoration: none;
}

.notebook-card:nth-child(even):hover {
  transform: rotate(0.5deg) translateY(-4px);
}

.notebook-card h3 {
  margin-bottom: 0.5rem;
  color: var(--color-primary);
  font-family: var(--font-handwritten);
  font-size: 1.5rem;
}

.description {
  color: var(--color-text-secondary);
  margin-bottom: 1rem;
  font-style: italic;
}

.tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.meta {
  font-size: 0.8rem;
  color: var(--color-text-secondary);
  font-family: var(--font-mono);
}

.loading,
.error,
.empty {
  text-align: center;
  padding: 3rem;
  color: var(--color-text-secondary);
  font-style: italic;
}

.error {
  color: var(--color-error);
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
  font-family: var(--font-body);
  font-size: 1rem;
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
