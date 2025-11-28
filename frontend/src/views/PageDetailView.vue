<script setup lang="ts">
import { ref, computed, onMounted, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useNotebooksStore } from "@/stores/notebooks";
import { pagesApi, entriesApi } from "@/api";
import type { Page, Entry } from "@/types";
import TextBlock from "@/components/blocks/TextBlock.vue";
import CellBlock from "@/components/blocks/CellBlock.vue";

const route = useRoute();
const router = useRouter();
const notebooksStore = useNotebooksStore();

const page = ref<Page | null>(null);
const entries = ref<Entry[]>([]);
const loading = ref(true);
const executingEntries = ref<Set<string>>(new Set());

// New cell creation state
const showNewCellMenu = ref(false);
const newCellPosition = ref<number | null>(null);

// Variation modal state
const showVariationModal = ref(false);
const variationEntry = ref<Entry | null>(null);
const variationTitle = ref("");
const creatingVariation = ref(false);

const notebookId = computed(() => route.params.notebookId as string);
const pageId = computed(() => route.params.pageId as string);

onMounted(async () => {
  await loadPage();
});

watch([notebookId, pageId], async () => {
  await loadPage();
});

async function loadPage() {
  loading.value = true;
  await notebooksStore.loadNotebook(notebookId.value);
  try {
    page.value = await pagesApi.get(notebooksStore.workspacePath, pageId.value);
    entries.value = await entriesApi.list(
      notebooksStore.workspacePath,
      pageId.value,
    );
  } catch (e) {
    console.error("Failed to load page:", e);
  } finally {
    loading.value = false;
  }
}

async function updateNarrative(field: string, content: string) {
  if (!page.value) return;
  try {
    const updatedNarrative = { ...page.value.narrative, [field]: content };
    await pagesApi.update(notebooksStore.workspacePath, pageId.value, {
      narrative: updatedNarrative,
    });
    page.value.narrative = updatedNarrative;
  } catch (e) {
    console.error("Failed to update narrative:", e);
  }
}

async function executeEntry(entry: Entry) {
  executingEntries.value.add(entry.id);
  try {
    const updated = await entriesApi.execute(notebooksStore.workspacePath, entry.id);
    const idx = entries.value.findIndex(e => e.id === entry.id);
    if (idx >= 0) {
      entries.value[idx] = updated;
    }
  } catch (e) {
    console.error("Failed to execute entry:", e);
    alert("Failed to execute entry: " + (e instanceof Error ? e.message : "Unknown error"));
  } finally {
    executingEntries.value.delete(entry.id);
  }
}

async function deleteEntry(entry: Entry) {
  if (!confirm(`Delete "${entry.title}"?`)) return;
  try {
    await entriesApi.delete(notebooksStore.workspacePath, entry.id);
    entries.value = entries.value.filter(e => e.id !== entry.id);
  } catch (e) {
    console.error("Failed to delete entry:", e);
  }
}

function openVariationModal(entry: Entry) {
  variationEntry.value = entry;
  variationTitle.value = `${entry.title} - Variation`;
  showVariationModal.value = true;
}

async function createVariation() {
  if (!variationEntry.value || !variationTitle.value.trim()) return;

  creatingVariation.value = true;
  try {
    const response = await fetch(`/api/entries/${variationEntry.value.id}/variations`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        workspace_path: notebooksStore.workspacePath,
        title: variationTitle.value,
        input_overrides: {},
        tags: [],
      }),
    });

    if (!response.ok) throw new Error("Failed to create variation");

    const newEntry = await response.json();
    entries.value.push(newEntry);
    showVariationModal.value = false;
    variationEntry.value = null;
    variationTitle.value = "";
  } catch (e) {
    console.error("Failed to create variation:", e);
    alert("Failed to create variation");
  } finally {
    creatingVariation.value = false;
  }
}

function closeVariationModal() {
  showVariationModal.value = false;
  variationEntry.value = null;
  variationTitle.value = "";
}

function showAddCell(position: number) {
  newCellPosition.value = position;
  showNewCellMenu.value = true;
}

function hideAddCell() {
  showNewCellMenu.value = false;
  newCellPosition.value = null;
}

function addNewCell(entryType: string) {
  hideAddCell();
  router.push({
    path: `/notebooks/${notebookId.value}/pages/${pageId.value}/entries/new`,
    query: { type: entryType }
  });
}

const entryTypes = [
  { type: "custom", label: "Custom", icon: "📝" },
  { type: "database_query", label: "Database Query", icon: "🗃️" },
  { type: "api_call", label: "API Call", icon: "🌐" },
  { type: "graphql", label: "GraphQL", icon: "◈" },
];
</script>

<template>
  <div class="notebook-page" v-if="page">
    <!-- Page Header -->
    <header class="page-header">
      <div class="page-meta">
        <span class="page-date">
          {{ page.date ? new Date(page.date).toLocaleDateString() : "Undated" }}
        </span>
        <div v-if="page.tags?.length" class="tags">
          <span v-for="tag in page.tags" :key="tag" class="tag">{{ tag }}</span>
        </div>
      </div>
      <h1 class="page-title">{{ page.title }}</h1>
    </header>

    <!-- Notebook Content -->
    <div class="notebook-content">
      <!-- Goals Section -->
      <section class="notebook-section">
        <h2 class="section-label">Goals</h2>
        <TextBlock
          :content="page.narrative?.goals || ''"
          placeholder="What are you trying to achieve?"
          :editable="true"
          @update="content => updateNarrative('goals', content)"
        />
      </section>

      <!-- Hypothesis Section -->
      <section class="notebook-section">
        <h2 class="section-label">Hypothesis</h2>
        <TextBlock
          :content="page.narrative?.hypothesis || ''"
          placeholder="What do you expect to happen?"
          :editable="true"
          @update="content => updateNarrative('hypothesis', content)"
        />
      </section>

      <!-- Add Cell Button (before entries) -->
      <div class="add-cell-row">
        <button class="add-cell-btn" @click="showAddCell(0)">
          <span class="add-icon">+</span>
          <span>Add Cell</span>
        </button>
      </div>

      <!-- Entries (Cells) -->
      <div class="cells-container">
        <template v-for="(entry, index) in entries" :key="entry.id">
          <CellBlock
            :entry="entry"
            :executing="executingEntries.has(entry.id)"
            @execute="executeEntry(entry)"
            @delete="deleteEntry(entry)"
            @create-variation="openVariationModal(entry)"
          />

          <!-- Add Cell Button after each entry -->
          <div class="add-cell-row">
            <button class="add-cell-btn" @click="showAddCell(index + 1)">
              <span class="add-icon">+</span>
            </button>
          </div>
        </template>

        <div v-if="entries.length === 0" class="empty-cells">
          <p>No cells yet. Add your first cell to start experimenting.</p>
        </div>
      </div>

      <!-- Observations Section -->
      <section class="notebook-section">
        <h2 class="section-label">Observations</h2>
        <TextBlock
          :content="page.narrative?.observations || ''"
          placeholder="What did you observe?"
          :editable="true"
          @update="content => updateNarrative('observations', content)"
        />
      </section>

      <!-- Conclusions Section -->
      <section class="notebook-section">
        <h2 class="section-label">Conclusions</h2>
        <TextBlock
          :content="page.narrative?.conclusions || ''"
          placeholder="What conclusions can you draw?"
          :editable="true"
          @update="content => updateNarrative('conclusions', content)"
        />
      </section>

      <!-- Next Steps Section -->
      <section class="notebook-section">
        <h2 class="section-label">Next Steps</h2>
        <TextBlock
          :content="page.narrative?.next_steps || ''"
          placeholder="What should you try next?"
          :editable="true"
          @update="content => updateNarrative('next_steps', content)"
        />
      </section>
    </div>

    <!-- New Cell Menu (Dropdown) -->
    <div v-if="showNewCellMenu" class="cell-menu-overlay" @click="hideAddCell">
      <div class="cell-menu" @click.stop>
        <h3>Add Cell</h3>
        <div class="cell-menu-options">
          <button
            v-for="cellType in entryTypes"
            :key="cellType.type"
            class="cell-menu-option"
            @click="addNewCell(cellType.type)"
          >
            <span class="cell-menu-icon">{{ cellType.icon }}</span>
            <span>{{ cellType.label }}</span>
          </button>
        </div>
      </div>
    </div>

    <!-- Variation Modal -->
    <div v-if="showVariationModal" class="modal-overlay" @click.self="closeVariationModal">
      <div class="modal">
        <h2>Create Variation</h2>
        <p class="modal-subtitle">Based on: {{ variationEntry?.title }}</p>
        <form @submit.prevent="createVariation">
          <div class="form-group">
            <label for="variation-title">Title *</label>
            <input
              id="variation-title"
              v-model="variationTitle"
              type="text"
              required
            />
          </div>
          <div class="modal-actions">
            <button type="button" class="btn" @click="closeVariationModal">Cancel</button>
            <button type="submit" class="btn btn-primary" :disabled="creatingVariation">
              {{ creatingVariation ? "Creating..." : "Create Variation" }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>

  <div v-else-if="loading" class="loading">Loading page...</div>
</template>

<style scoped>
.notebook-page {
  max-width: 900px;
  margin: 0 auto;
  padding: 2rem;
}

.page-header {
  margin-bottom: 2rem;
  padding-bottom: 1.5rem;
  border-bottom: 1px solid var(--color-border);
}

.page-meta {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 0.5rem;
}

.page-date {
  font-size: 0.875rem;
  color: var(--color-text-secondary);
}

.page-title {
  font-size: 2rem;
  font-weight: 700;
  color: var(--color-text);
  margin: 0;
}

.tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.notebook-content {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.notebook-section {
  padding: 0.5rem 0;
}

.section-label {
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--color-text-secondary);
  margin-bottom: 0.5rem;
}

.cells-container {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 1rem 0;
}

.add-cell-row {
  display: flex;
  justify-content: center;
  padding: 0.25rem 0;
  opacity: 0;
  transition: opacity 0.2s;
}

.notebook-content:hover .add-cell-row,
.add-cell-row:hover {
  opacity: 1;
}

.add-cell-btn {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.375rem 0.75rem;
  background: var(--color-background);
  border: 1px dashed var(--color-border);
  border-radius: var(--radius-md);
  color: var(--color-text-secondary);
  font-size: 0.875rem;
  cursor: pointer;
  transition: all 0.2s;
}

.add-cell-btn:hover {
  background: var(--color-surface);
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.add-icon {
  font-size: 1rem;
  font-weight: 600;
}

.empty-cells {
  text-align: center;
  padding: 3rem;
  background: var(--color-background);
  border: 2px dashed var(--color-border);
  border-radius: var(--radius-lg);
  color: var(--color-text-secondary);
}

.cell-menu-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.3);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.cell-menu {
  background: var(--color-surface);
  border-radius: var(--radius-lg);
  padding: 1.5rem;
  box-shadow: var(--shadow-lg);
  min-width: 280px;
}

.cell-menu h3 {
  margin-bottom: 1rem;
  font-size: 1rem;
  color: var(--color-text);
}

.cell-menu-options {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.cell-menu-option {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 1rem;
  background: var(--color-background);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all 0.2s;
  text-align: left;
  font-size: 0.9375rem;
}

.cell-menu-option:hover {
  background: var(--color-primary);
  border-color: var(--color-primary);
  color: white;
}

.cell-menu-icon {
  font-size: 1.25rem;
}

.loading {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 50vh;
  color: var(--color-text-secondary);
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal {
  background: var(--color-background);
  padding: 2rem;
  border-radius: 8px;
  width: 100%;
  max-width: 500px;
  box-shadow: var(--shadow-lg);
}

.modal h2 {
  margin-bottom: 0.5rem;
}

.modal-subtitle {
  color: var(--color-text-secondary);
  margin-bottom: 1.5rem;
}

.form-group {
  margin-bottom: 1rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 500;
}

.form-group input,
.form-group textarea {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  font-size: 1rem;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 1rem;
  margin-top: 1.5rem;
}
</style>
