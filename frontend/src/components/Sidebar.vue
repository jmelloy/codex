<script setup lang="ts">
import { ref, computed, onMounted, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useNotebooksStore } from "@/stores/notebooks";
import { pagesApi, filesApi, type FileTreeItem } from "@/api";
import type {  Page } from "@/types";

const route = useRoute();
const router = useRouter();
const notebooksStore = useNotebooksStore();

const expandedNotebooks = ref<Set<string>>(new Set());
const expandedDirs = ref<Set<string>>(new Set());
const notebookPages = ref<Map<string, Page[]>>(new Map());
const notebookFiles = ref<FileTreeItem[]>([]);
const loading = ref(true);


const currentNotebookId = computed(() => route.params.notebookId as string | undefined);
const currentFilePath = computed(() => route.query.path as string | undefined);

onMounted(async () => {
  await Promise.all([
    notebooksStore.loadNotebooks(),
    loadNotebookFiles(),
  ]);
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

async function loadNotebookFiles() {
  try {
    const result = await filesApi.listNotebooks(notebooksStore.workspacePath);
    notebookFiles.value = result.files;
  } catch (e) {
    console.error("Failed to load notebook files:", e);
  }
}



function toggleDir(path: string) {
  if (expandedDirs.value.has(path)) {
    expandedDirs.value.delete(path);
  } else {
    expandedDirs.value.add(path);
  }
}

function navigateToFile(filePath: string) {
  // Ensure path is properly passed to router - Vue Router will handle encoding
  router.push({ path: '/files', query: { path: filePath } });
}

function isFileActive(path: string) {
  // Normalize both paths for comparison to handle encoding differences
  const normalizedCurrent = currentFilePath.value?.replace(/\+/g, ' ').trim();
  const normalizedPath = path?.replace(/\+/g, ' ').trim();
  return normalizedCurrent === normalizedPath;
}

function getFileIcon(item: FileTreeItem): string {
  // Use specific icons for items with properties
  if (item.properties?.type === "notebook") {
    return "📓";
  }
  if (item.properties?.type === "page") {
    return "📄";
  }
  
  if (item.type === "directory") {
    return "📁";
  }
  
  const ext = item.extension?.toLowerCase() || "";
  const iconMap: Record<string, string> = {
    ".md": "📝",
    ".txt": "📄",
    ".json": "📋",
    ".py": "🐍",
    ".js": "📜",
    ".ts": "📜",
    ".html": "🌐",
    ".css": "🎨",
    ".png": "🖼️",
    ".jpg": "🖼️",
    ".jpeg": "🖼️",
    ".gif": "🖼️",
    ".svg": "🖼️",
    ".pdf": "📕",
  };
  
  return iconMap[ext] || "📄";
}

function getDisplayName(item: FileTreeItem): string {
  // Use title from properties if available
  if (item.properties?.title) {
    return item.properties.title;
  }
  return item.name;
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

    <nav class="sidebar-nav">
      <!-- Files Section -->
      <div class="nav-section">
        <div class="nav-section-header">
          <span>Files</span>
        </div>

        <div class="tree">
          <template v-for="item in notebookFiles" :key="item.path">
            <!-- Directory -->
            <div v-if="item.type === 'directory'" class="tree-item">
              <div class="tree-node dir-node">
                <button
                  class="tree-toggle"
                  @click="toggleDir(item.path)"
                >
                  <span v-if="expandedDirs.has(item.path)">▼</span>
                  <span v-else>▶</span>
                </button>
                <span class="tree-icon">{{ getFileIcon(item) }}</span>
                <span class="tree-label">{{ getDisplayName(item) }}</span>
              </div>

              <div
                v-if="expandedDirs.has(item.path) && item.children"
                class="tree-children"
              >
                <template v-for="child in item.children" :key="child.path">
                  <div
                    v-if="child.type === 'file'"
                    class="tree-node file-node"
                    :class="{ active: isFileActive(child.path) }"
                    @click="navigateToFile(child.path)"
                  >
                    <span class="tree-icon">{{ getFileIcon(child) }}</span>
                    <span class="tree-label">{{ getDisplayName(child) }}</span>
                  </div>
                  <div v-else class="tree-item">
                    <div class="tree-node dir-node">
                      <button
                        class="tree-toggle"
                        @click="toggleDir(child.path)"
                      >
                        <span v-if="expandedDirs.has(child.path)">▼</span>
                        <span v-else>▶</span>
                      </button>
                      <span class="tree-icon">{{ getFileIcon(child) }}</span>
                      <span class="tree-label">{{ getDisplayName(child) }}</span>
                    </div>
                    <div
                      v-if="expandedDirs.has(child.path) && child.children"
                      class="tree-children"
                    >
                      <div
                        v-for="grandchild in child.children"
                        :key="grandchild.path"
                        class="tree-node file-node"
                        :class="{ active: isFileActive(grandchild.path) }"
                        @click="navigateToFile(grandchild.path)"
                      >
                        <span class="tree-icon">{{ getFileIcon(grandchild) }}</span>
                        <span class="tree-label">{{ getDisplayName(grandchild) }}</span>
                      </div>
                    </div>
                  </div>
                </template>
              </div>
            </div>

            <!-- File at root level -->
            <div
              v-else
              class="tree-node file-node"
              :class="{ active: isFileActive(item.path) }"
              @click="navigateToFile(item.path)"
            >
              <span class="tree-icon">{{ getFileIcon(item) }}</span>
              <span class="tree-label">{{ getDisplayName(item) }}</span>
            </div>
          </template>

          <div v-if="!notebookFiles.length" class="tree-empty">
            No files yet
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

.file-node {
  padding-left: 0.75rem;
}

.file-node .tree-icon {
  font-size: 0.75rem;
}

.dir-node .tree-icon {
  font-size: 0.875rem;
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
