<script setup lang="ts">
import { ref, computed, onMounted, watch, nextTick } from "vue";
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

// New cell creation state (Notion-like inline creation)
const showNewCellMenu = ref(false);
const newCellPosition = ref<number | null>(null);
const isCreatingTextCell = ref(false);
const newTextCellContent = ref("");
const newTextCellTitle = ref("");
const newTextCellInputRef = ref<HTMLInputElement | null>(null);

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

// Notion-like inline cell creation
function startInlineTextCell(position: number) {
  newCellPosition.value = position;
  isCreatingTextCell.value = true;
  newTextCellTitle.value = "";
  newTextCellContent.value = "";
  nextTick(() => {
    newTextCellInputRef.value?.focus();
  });
}

function cancelInlineTextCell() {
  isCreatingTextCell.value = false;
  newCellPosition.value = null;
  newTextCellTitle.value = "";
  newTextCellContent.value = "";
}

async function saveInlineTextCell() {
  if (!newTextCellTitle.value.trim() && !newTextCellContent.value.trim()) {
    cancelInlineTextCell();
    return;
  }

  const title = newTextCellTitle.value.trim() || "Untitled";
  
  try {
    const newEntry = await entriesApi.create(
      notebooksStore.workspacePath,
      pageId.value,
      {
        entry_type: "text",
        title: title,
        inputs: {
          content: newTextCellContent.value,
        },
        tags: [],
      }
    );
    entries.value.push(newEntry);
    cancelInlineTextCell();
  } catch (e) {
    console.error("Failed to create cell:", e);
    alert("Failed to create cell");
  }
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
  // For text cells, create inline; for others, navigate to form
  if (entryType === "text") {
    startInlineTextCell(newCellPosition.value ?? entries.value.length);
  } else {
    router.push({
      path: `/notebooks/${notebookId.value}/pages/${pageId.value}/entries/new`,
      query: { type: entryType }
    });
  }
}

const entryTypes = [
  { type: "text", label: "Text", icon: "📝", description: "Plain text or markdown content" },
  { type: "custom", label: "Custom", icon: "🔧", description: "Custom entry with JSON data" },
  { type: "database_query", label: "Database Query", icon: "🗃️", description: "Execute SQL queries" },
  { type: "api_call", label: "API Call", icon: "🌐", description: "HTTP API requests" },
  { type: "graphql", label: "GraphQL", icon: "◈", description: "GraphQL queries and mutations" },
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

      <!-- Entries (Cells) - Notion-like layout -->
      <div class="cells-container">
        <!-- Inline text cell creation at top -->
        <div v-if="isCreatingTextCell && newCellPosition === 0" class="inline-cell-creator">
          <input
            ref="newTextCellInputRef"
            v-model="newTextCellTitle"
            type="text"
            class="inline-title-input"
            placeholder="Title (optional)"
            @keydown.enter.prevent="saveInlineTextCell"
            @keydown.escape="cancelInlineTextCell"
          />
          <textarea
            v-model="newTextCellContent"
            class="inline-content-input"
            placeholder="Start typing your content..."
            rows="3"
            @keydown.escape="cancelInlineTextCell"
          ></textarea>
          <div class="inline-cell-actions">
            <button class="btn btn-sm" @click="cancelInlineTextCell">Cancel</button>
            <button class="btn btn-sm btn-primary" @click="saveInlineTextCell">Save</button>
          </div>
        </div>

        <!-- Add Cell Button (before entries) -->
        <div v-if="!isCreatingTextCell || newCellPosition !== 0" class="add-cell-row">
          <button class="add-cell-btn" @click="startInlineTextCell(0)" title="Add text cell">
            <span class="add-icon">+</span>
            <span>Add</span>
          </button>
          <button class="add-cell-menu-btn" @click="showAddCell(0)" title="More cell types">
            <span>▾</span>
          </button>
        </div>

        <template v-for="(entry, index) in entries" :key="entry.id">
          <CellBlock
            :entry="entry"
            :executing="executingEntries.has(entry.id)"
            @execute="executeEntry(entry)"
            @delete="deleteEntry(entry)"
            @create-variation="openVariationModal(entry)"
          />

          <!-- Inline text cell creation after entry -->
          <div v-if="isCreatingTextCell && newCellPosition === index + 1" class="inline-cell-creator">
            <input
              ref="newTextCellInputRef"
              v-model="newTextCellTitle"
              type="text"
              class="inline-title-input"
              placeholder="Title (optional)"
              @keydown.enter.prevent="saveInlineTextCell"
              @keydown.escape="cancelInlineTextCell"
            />
            <textarea
              v-model="newTextCellContent"
              class="inline-content-input"
              placeholder="Start typing your content..."
              rows="3"
              @keydown.escape="cancelInlineTextCell"
            ></textarea>
            <div class="inline-cell-actions">
              <button class="btn btn-sm" @click="cancelInlineTextCell">Cancel</button>
              <button class="btn btn-sm btn-primary" @click="saveInlineTextCell">Save</button>
            </div>
          </div>

          <!-- Add Cell Button after each entry -->
          <div v-if="!isCreatingTextCell || newCellPosition !== index + 1" class="add-cell-row">
            <button class="add-cell-btn" @click="startInlineTextCell(index + 1)" title="Add text cell">
              <span class="add-icon">+</span>
            </button>
            <button class="add-cell-menu-btn" @click="showAddCell(index + 1)" title="More cell types">
              <span>▾</span>
            </button>
          </div>
        </template>

        <div v-if="entries.length === 0 && !isCreatingTextCell" class="empty-cells">
          <p>No cells yet. Click + to add your first cell.</p>
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
        <h3>Choose Cell Type</h3>
        <div class="cell-menu-options">
          <button
            v-for="cellType in entryTypes"
            :key="cellType.type"
            class="cell-menu-option"
            @click="addNewCell(cellType.type)"
          >
            <span class="cell-menu-icon">{{ cellType.icon }}</span>
            <div class="cell-menu-text">
              <span class="cell-menu-label">{{ cellType.label }}</span>
              <span class="cell-menu-description">{{ cellType.description }}</span>
            </div>
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
  padding: 2rem 3rem;
  background: var(--color-surface);
  background-image: 
    linear-gradient(var(--color-margin-line) 0, transparent 0),
    repeating-linear-gradient(
      transparent,
      transparent var(--line-height-spacing),
      var(--color-page-lines) var(--line-height-spacing),
      var(--color-page-lines) calc(var(--line-height-spacing) + var(--line-stroke-width))
    );
  background-position: var(--margin-offset) 0, 0 8px;
  min-height: 100vh;
  box-shadow: var(--shadow-lg);
  position: relative;
}

/* Red margin line */
.notebook-page::before {
  content: '';
  position: absolute;
  left: var(--margin-offset);
  top: 0;
  bottom: 0;
  width: var(--line-stroke-width);
  background: var(--color-margin-line);
  opacity: 0.7;
}

/* Spiral binding holes indicator */
.notebook-page::after {
  content: '';
  position: absolute;
  left: 20px;
  top: 0;
  bottom: 0;
  width: 8px;
  background: repeating-linear-gradient(
    to bottom,
    transparent 0px,
    transparent 24px,
    var(--color-border) 24px,
    var(--color-border) 32px
  );
  border-radius: 4px;
}

.page-header {
  margin-bottom: 2rem;
  padding-bottom: 1.5rem;
  border-bottom: 2px solid var(--color-border);
  margin-left: 30px;
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
  font-family: var(--font-mono);
}

.page-title {
  font-size: 2.25rem;
  font-weight: 600;
  color: var(--color-text);
  margin: 0;
  font-family: var(--font-handwritten);
  letter-spacing: 0.01em;
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
  margin-left: 30px;
}

.notebook-section {
  padding: 0.5rem 0;
}

.section-label {
  font-size: 0.7rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--color-text-secondary);
  margin-bottom: 0.5rem;
  font-family: var(--font-mono);
}

.cells-container {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 1rem 0;
}

.notebook-content:hover .add-cell-row,
.add-cell-row:hover {
  opacity: 1;
}

.add-icon {
  font-size: 1rem;
  font-weight: 600;
}

.empty-cells {
  text-align: center;
  padding: 3rem;
  background: rgba(245, 240, 230, 0.5);
  border: 2px dashed var(--color-border);
  border-radius: var(--radius-lg);
  color: var(--color-text-secondary);
  font-style: italic;
  font-family: var(--font-handwritten);
  font-size: 1.1rem;
}

.cell-menu-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(44, 36, 22, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.cell-menu {
  background: var(--color-surface);
  background-image: var(--paper-texture);
  border-radius: var(--radius-lg);
  padding: 1.5rem;
  box-shadow: var(--shadow-lg);
  min-width: 280px;
  border: 1px solid var(--color-border);
}

.cell-menu h3 {
  margin-bottom: 1rem;
  font-size: 1.25rem;
  color: var(--color-primary);
  font-family: var(--font-handwritten);
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
  font-family: var(--font-body);
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
  margin-bottom: 0.5rem;
  font-family: var(--font-handwritten);
  font-size: 1.75rem;
  color: var(--color-primary);
}

.modal-subtitle {
  color: var(--color-text-secondary);
  margin-bottom: 1.5rem;
  font-style: italic;
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

/* Inline cell creator styles (Notion-like) */
.inline-cell-creator {
  background: var(--color-surface);
  border: 2px solid var(--color-primary);
  border-radius: var(--radius-md);
  padding: 1rem;
  margin: 0.5rem 0;
  box-shadow: var(--shadow-md);
}

.inline-title-input {
  width: 100%;
  padding: 0.5rem;
  border: none;
  border-bottom: 1px solid var(--color-border);
  font-size: 1rem;
  font-weight: 500;
  font-family: var(--font-body);
  background: transparent;
  margin-bottom: 0.5rem;
}

.inline-title-input:focus {
  outline: none;
  border-bottom-color: var(--color-primary);
}

.inline-content-input {
  width: 100%;
  padding: 0.5rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  font-size: 0.9375rem;
  font-family: var(--font-body);
  resize: vertical;
  min-height: 80px;
  background: var(--color-background);
}

.inline-content-input:focus {
  outline: none;
  border-color: var(--color-primary);
}

.inline-cell-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
  margin-top: 0.75rem;
}

.btn-sm {
  padding: 0.375rem 0.75rem;
  font-size: 0.8125rem;
}

/* Updated add cell button styles for split button */
.add-cell-row {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 0;
  padding: 0.25rem 0;
  opacity: 0;
  transition: opacity 0.2s;
}

.add-cell-btn {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.375rem 0.625rem;
  background: var(--color-background);
  border: 1px dashed var(--color-border);
  border-right: none;
  border-radius: var(--radius-md) 0 0 var(--radius-md);
  color: var(--color-text-secondary);
  font-size: 0.8125rem;
  cursor: pointer;
  transition: all 0.2s;
}

.add-cell-btn:hover {
  background: var(--color-surface);
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.add-cell-menu-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0.375rem 0.5rem;
  background: var(--color-background);
  border: 1px dashed var(--color-border);
  border-radius: 0 var(--radius-md) var(--radius-md) 0;
  color: var(--color-text-secondary);
  font-size: 0.75rem;
  cursor: pointer;
  transition: all 0.2s;
}

.add-cell-menu-btn:hover {
  background: var(--color-surface);
  border-color: var(--color-primary);
  color: var(--color-primary);
}

/* Updated cell menu styles with descriptions */
.cell-menu-text {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
}

.cell-menu-label {
  font-weight: 500;
}

.cell-menu-description {
  font-size: 0.75rem;
  opacity: 0.7;
}

.cell-menu-option:hover .cell-menu-description {
  opacity: 0.9;
}
</style>
