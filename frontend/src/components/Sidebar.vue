<script setup lang="ts">
import { ref, computed, onMounted, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useNotebooksStore } from "@/stores/notebooks";
import { pagesApi } from "@/api";
import type { Notebook, Page } from "@/types";

const route = useRoute();
const router = useRouter();
const notebooksStore = useNotebooksStore();

const expandedNotebooks = ref<Set<string>>(new Set());
const notebookPages = ref<Map<string, Page[]>>(new Map());
const loading = ref(true);

const notebooks = computed(() => Array.from(notebooksStore.notebooks.values()));

const currentNotebookId = computed(() => route.params.notebookId as string | undefined);
const currentPageId = computed(() => route.params.pageId as string | undefined);

onMounted(async () => {
  await notebooksStore.loadNotebooks();
  loading.value = false;
  
  // Auto-expand current notebook
  if (currentNotebookId.value) {
    expandedNotebooks.value.add(currentNotebookId.value);
    await loadPagesForNotebook(currentNotebookId.value);
  }
});

watch(currentNotebookId, async (newId) => {
  if (newId && !expandedNotebooks.value.has(newId)) {
    expandedNotebooks.value.add(newId);
    await loadPagesForNotebook(newId);
  }
});

async function loadPagesForNotebook(notebookId: string) {
  if (!notebookPages.value.has(notebookId)) {
    try {
      const pages = await pagesApi.list(notebooksStore.workspacePath, notebookId);
      notebookPages.value.set(notebookId, pages);
    } catch (e) {
      console.error("Failed to load pages:", e);
    }
  }
}

async function toggleNotebook(notebook: Notebook) {
  if (expandedNotebooks.value.has(notebook.id)) {
    expandedNotebooks.value.delete(notebook.id);
  } else {
    expandedNotebooks.value.add(notebook.id);
    await loadPagesForNotebook(notebook.id);
  }
}

function navigateToNotebook(notebook: Notebook) {
  router.push(`/notebooks/${notebook.id}`);
}

function navigateToPage(notebookId: string, page: Page) {
  router.push(`/notebooks/${notebookId}/pages/${page.id}`);
}

function isNotebookActive(notebook: Notebook) {
  return currentNotebookId.value === notebook.id && !currentPageId.value;
}

function isPageActive(page: Page) {
  return currentPageId.value === page.id;
}
</script>

<template>
  <aside class="sidebar">
    <div class="sidebar-header">
      <RouterLink to="/" class="logo">
        <span class="logo-icon">📓</span>
        <span class="logo-text">Codex</span>
      </RouterLink>
    </div>

    <div class="sidebar-search">
      <RouterLink to="/search" class="search-link">
        <span class="search-icon">🔍</span>
        <span>Search</span>
      </RouterLink>
    </div>

    <div class="sidebar-tools">
      <RouterLink to="/sql" class="tool-link">
        <span class="tool-icon">🗃️</span>
        <span>SQL Viewer</span>
      </RouterLink>
    </div>

    <nav class="sidebar-nav">
      <div class="nav-section">
        <div class="nav-section-header">
          <span>Notebooks</span>
        </div>

        <div v-if="loading" class="loading">Loading...</div>

        <div v-else class="tree">
          <div v-for="notebook in notebooks" :key="notebook.id" class="tree-item">
            <div
              class="tree-node notebook-node"
              :class="{ active: isNotebookActive(notebook) }"
            >
              <button
                class="tree-toggle"
                @click="toggleNotebook(notebook)"
              >
                <span v-if="expandedNotebooks.has(notebook.id)">▼</span>
                <span v-else>▶</span>
              </button>
              <span class="tree-icon">📓</span>
              <span
                class="tree-label"
                @click="navigateToNotebook(notebook)"
              >
                {{ notebook.title }}
              </span>
            </div>

            <div
              v-if="expandedNotebooks.has(notebook.id)"
              class="tree-children"
            >
              <div
                v-for="page in notebookPages.get(notebook.id) || []"
                :key="page.id"
                class="tree-node page-node"
                :class="{ active: isPageActive(page) }"
                @click="navigateToPage(notebook.id, page)"
              >
                <span class="tree-icon">📄</span>
                <span class="tree-label">{{ page.title }}</span>
              </div>

              <div
                v-if="!notebookPages.get(notebook.id)?.length"
                class="tree-empty"
              >
                No pages
              </div>
            </div>
          </div>

          <div v-if="!notebooks.length" class="tree-empty">
            No notebooks yet
          </div>
        </div>
      </div>
    </nav>

    <div class="sidebar-footer">
      <RouterLink to="/notebooks" class="footer-link">
        + New Notebook
      </RouterLink>
    </div>
  </aside>
</template>

<style scoped>
.sidebar {
  width: 260px;
  min-width: 260px;
  background: linear-gradient(
    90deg,
    var(--color-binding) 0%,
    #4d3b2f 8px,
    var(--color-surface) 8px,
    var(--color-surface) 100%
  );
  border-right: 1px solid var(--color-border);
  display: flex;
  flex-direction: column;
  height: 100vh;
  position: sticky;
  top: 0;
  box-shadow: 2px 0 8px rgba(0, 0, 0, 0.1);
}

/* Notebook binding rings effect */
.sidebar::before {
  content: '';
  position: absolute;
  left: 4px;
  top: 0;
  bottom: 0;
  width: 1px;
  background: repeating-linear-gradient(
    to bottom,
    transparent 0px,
    transparent 20px,
    #2a1f17 20px,
    #2a1f17 24px,
    transparent 24px,
    transparent 44px
  );
  opacity: 0.6;
}

.sidebar-header {
  padding: 1rem 1rem 1rem 1.5rem;
  border-bottom: 1px solid var(--color-border);
  background: var(--color-surface);
  margin-left: 8px;
}

.logo {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  text-decoration: none;
  color: var(--color-text);
}

.logo-icon {
  font-size: 1.5rem;
}

.logo-text {
  font-size: 1.5rem;
  font-weight: 700;
  font-family: var(--font-handwritten);
  color: var(--color-primary);
  letter-spacing: 0.02em;
}

.sidebar-search {
  padding: 0.75rem 1rem 0.75rem 1.5rem;
  border-bottom: 1px solid var(--color-border);
  background: var(--color-surface);
  margin-left: 8px;
}

.search-link {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  background: var(--color-background);
  border-radius: var(--radius-md);
  color: var(--color-text-secondary);
  text-decoration: none;
  font-size: 0.875rem;
  border: 1px dashed var(--color-border);
}

.search-link:hover {
  background: var(--color-border);
  text-decoration: none;
  border-style: solid;
}

.sidebar-tools {
  padding: 0.5rem 1rem 0.75rem 1.5rem;
  border-bottom: 1px solid var(--color-border);
  background: var(--color-surface);
  margin-left: 8px;
}

.tool-link {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  background: var(--color-background);
  border-radius: var(--radius-md);
  color: var(--color-text-secondary);
  text-decoration: none;
  font-size: 0.875rem;
  border: 1px dashed var(--color-border);
}

.tool-link:hover {
  background: var(--color-border);
  text-decoration: none;
  border-style: solid;
  color: var(--color-primary);
}

.tool-icon {
  font-size: 1rem;
}

.sidebar-nav {
  flex: 1;
  overflow-y: auto;
  padding: 0.75rem 0;
  background: var(--color-surface);
  margin-left: 8px;
}

.nav-section-header {
  padding: 0.5rem 1rem;
  font-size: 0.7rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--color-text-secondary);
  font-family: var(--font-mono);
}

.tree {
  padding: 0 0.5rem;
}

.tree-item {
  margin-bottom: 0.25rem;
}

.tree-node {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.375rem 0.5rem;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: background-color 0.15s;
  font-family: var(--font-body);
}

.tree-node:hover {
  background: var(--color-background);
}

.tree-node.active {
  background: var(--color-primary);
  color: white;
}

.tree-node.active .tree-label {
  color: white;
}

.tree-toggle {
  width: 1.25rem;
  height: 1.25rem;
  display: flex;
  align-items: center;
  justify-content: center;
  background: none;
  border: none;
  padding: 0;
  font-size: 0.625rem;
  color: var(--color-text-secondary);
  cursor: pointer;
}

.tree-icon {
  font-size: 0.875rem;
  flex-shrink: 0;
}

.tree-label {
  flex: 1;
  font-size: 0.875rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  color: var(--color-text);
}

.tree-children {
  padding-left: 1.5rem;
  margin-top: 0.25rem;
}

.page-node {
  padding-left: 0.75rem;
}

.page-node .tree-icon {
  font-size: 0.75rem;
}

.tree-empty {
  padding: 0.5rem 0.75rem;
  font-size: 0.75rem;
  color: var(--color-text-secondary);
  font-style: italic;
}

.loading {
  padding: 1rem;
  text-align: center;
  color: var(--color-text-secondary);
  font-size: 0.875rem;
}

.sidebar-footer {
  padding: 1rem;
  border-top: 1px solid var(--color-border);
  background: var(--color-surface);
  margin-left: 8px;
}

.footer-link {
  display: block;
  text-align: center;
  padding: 0.5rem;
  background: var(--color-primary);
  color: white;
  border-radius: var(--radius-md);
  text-decoration: none;
  font-size: 0.875rem;
  font-weight: 500;
  font-family: var(--font-body);
}

.footer-link:hover {
  background: var(--color-primary-dark);
  text-decoration: none;
}
</style>
