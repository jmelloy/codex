<script setup lang="ts">
import { ref, computed, onMounted, watch } from "vue";
import { useNotebooksStore } from "@/stores/notebooks";
import { pagesApi, entriesApi } from "@/api";
import type { Notebook, Page, Entry } from "@/types";

const notebooksStore = useNotebooksStore();

// Connection and query state
const connectionString = ref("sqlite:///:memory:");
const query = ref("SELECT 1 as test_column;");
const maxRows = ref(1000);

// Execution state
const executing = ref(false);
const results = ref<Record<string, unknown>[] | null>(null);
const columns = ref<string[]>([]);
const error = ref<string | null>(null);
const executionTime = ref<number | null>(null);
const rowCount = ref<number | null>(null);

// Query history (recent experiments)
const queryHistory = ref<Entry[]>([]);

// Experiment tracking
const notebooks = ref<Notebook[]>([]);
const pages = ref<Page[]>([]);
const selectedNotebookId = ref<string>("");
const selectedPageId = ref<string>("");
const autoSaveEnabled = ref(true);
const queryTitle = ref("");

// Predefined connection string templates
const connectionTemplates = [
  { label: "SQLite (memory)", value: "sqlite:///:memory:" },
  { label: "SQLite (file)", value: "sqlite:///path/to/database.db" },
  { label: "PostgreSQL", value: "postgresql://user:password@localhost:5432/dbname" },
  { label: "MySQL", value: "mysql://user:password@localhost:3306/dbname" },
];

const pagesForNotebook = computed(() => {
  if (!selectedNotebookId.value) return [];
  return pages.value.filter(p => p.notebook_id === selectedNotebookId.value);
});

// Detect if user is on macOS for keyboard shortcut display
const isMac = computed(() => {
  return typeof navigator !== 'undefined' && navigator.platform.toUpperCase().indexOf('MAC') >= 0;
});

onMounted(async () => {
  await notebooksStore.loadNotebooks();
  notebooks.value = Array.from(notebooksStore.notebooks.values());
  
  // If there's a notebook, select the first one and load its pages
  if (notebooks.value.length > 0) {
    selectedNotebookId.value = notebooks.value[0].id;
    await loadPagesForNotebook(notebooks.value[0].id);
  }
});

watch(selectedNotebookId, async (newId) => {
  if (newId) {
    await loadPagesForNotebook(newId);
  }
});

async function loadPagesForNotebook(notebookId: string) {
  try {
    const loadedPages = await pagesApi.list(notebooksStore.workspacePath, notebookId);
    pages.value = loadedPages;
    if (loadedPages.length > 0) {
      selectedPageId.value = loadedPages[0].id;
    } else {
      selectedPageId.value = "";
    }
  } catch (e) {
    console.error("Failed to load pages:", e);
  }
}

function applyTemplate(template: string) {
  connectionString.value = template;
}

function generateQueryTitle(): string {
  if (queryTitle.value.trim()) return queryTitle.value.trim();
  
  // Try to extract a meaningful title from the query
  const q = query.value.trim().toUpperCase();
  if (q.startsWith("SELECT")) {
    const match = query.value.match(/FROM\s+["'`]?(\w+)["'`]?/i);
    if (match) {
      return `Query: ${match[1]}`;
    }
    return "SELECT Query";
  } else if (q.startsWith("INSERT")) {
    return "INSERT Query";
  } else if (q.startsWith("UPDATE")) {
    return "UPDATE Query";
  } else if (q.startsWith("DELETE")) {
    return "DELETE Query";
  } else if (q.startsWith("CREATE")) {
    return "CREATE Statement";
  }
  return `SQL Query ${new Date().toLocaleTimeString()}`;
}

async function executeQuery() {
  if (!query.value.trim()) return;
  
  executing.value = true;
  error.value = null;
  results.value = null;
  columns.value = [];
  executionTime.value = null;
  rowCount.value = null;
  
  try {
    // If auto-save is enabled and we have a page, create an entry first
    if (autoSaveEnabled.value && selectedPageId.value) {
      const entryTitle = generateQueryTitle();
      const entry = await entriesApi.create(
        notebooksStore.workspacePath,
        selectedPageId.value,
        {
          entry_type: "database_query",
          title: entryTitle,
          inputs: {
            connection_string: connectionString.value,
            query: query.value,
            max_rows: maxRows.value,
          },
          tags: ["sql-viewer"],
        }
      );
      
      // Execute the entry
      const executedEntry = await entriesApi.execute(
        notebooksStore.workspacePath,
        entry.id
      );
      
      // Parse results
      if (executedEntry.outputs) {
        if (executedEntry.outputs.error) {
          error.value = executedEntry.outputs.error as string;
        } else {
          columns.value = (executedEntry.outputs.columns as string[]) || [];
          results.value = (executedEntry.outputs.results as Record<string, unknown>[]) || [];
          rowCount.value = executedEntry.outputs.row_count as number;
          executionTime.value = executedEntry.outputs.duration_seconds as number;
        }
      }
      
      // Add to history
      queryHistory.value.unshift(executedEntry);
      if (queryHistory.value.length > 20) {
        queryHistory.value = queryHistory.value.slice(0, 20);
      }
    } else {
      // Execute without saving - use direct API call
      const response = await fetch("/api/sql/execute", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          workspace_path: notebooksStore.workspacePath,
          connection_string: connectionString.value,
          query: query.value,
          max_rows: maxRows.value,
        }),
      });
      
      const data = await response.json();
      
      if (data.error) {
        error.value = data.error;
      } else {
        columns.value = data.columns || [];
        results.value = data.results || [];
        rowCount.value = data.row_count;
        executionTime.value = data.duration_seconds;
      }
    }
    
    // Clear title for next query
    queryTitle.value = "";
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed to execute query";
  } finally {
    executing.value = false;
  }
}

function loadHistoryQuery(entry: Entry) {
  if (entry.inputs) {
    connectionString.value = entry.inputs.connection_string as string || "";
    query.value = entry.inputs.query as string || "";
    maxRows.value = entry.inputs.max_rows as number || 1000;
  }
}

function formatValue(value: unknown): string {
  if (value === null) return "NULL";
  if (value === undefined) return "";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function handleKeyDown(event: KeyboardEvent) {
  // Execute with Cmd/Ctrl + Enter
  if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
    event.preventDefault();
    executeQuery();
  }
}
</script>

<template>
  <div class="sql-viewer">
    <!-- Left Panel: Query Editor -->
    <div class="query-panel">
      <header class="panel-header">
        <h1>🗃️ SQL Viewer</h1>
        <p class="subtitle">Execute queries and automatically track experiments</p>
      </header>

      <!-- Connection Settings -->
      <section class="connection-section">
        <h2 class="section-title">Connection</h2>
        <div class="connection-input-group">
          <input
            v-model="connectionString"
            type="text"
            class="connection-input"
            placeholder="sqlite:///path/to/db.sqlite"
          />
          <div class="template-buttons">
            <button
              v-for="template in connectionTemplates"
              :key="template.label"
              type="button"
              class="template-btn"
              @click="applyTemplate(template.value)"
            >
              {{ template.label }}
            </button>
          </div>
        </div>
      </section>

      <!-- Query Editor -->
      <section class="query-section">
        <div class="query-header">
          <h2 class="section-title">Query</h2>
          <span class="shortcut-hint">{{ isMac ? '⌘' : 'Ctrl' }} + Enter to run</span>
        </div>
        <textarea
          v-model="query"
          class="query-editor"
          placeholder="SELECT * FROM users WHERE id = 1"
          rows="10"
          @keydown="handleKeyDown"
        ></textarea>
      </section>

      <!-- Experiment Tracking -->
      <section class="tracking-section">
        <div class="tracking-header">
          <label class="auto-save-toggle">
            <input type="checkbox" v-model="autoSaveEnabled" />
            <span>Auto-save as experiment</span>
          </label>
        </div>
        
        <div v-if="autoSaveEnabled" class="tracking-form">
          <div class="form-row">
            <div class="form-group">
              <label>Notebook</label>
              <select v-model="selectedNotebookId" class="form-select">
                <option value="">Select notebook...</option>
                <option v-for="nb in notebooks" :key="nb.id" :value="nb.id">
                  {{ nb.title }}
                </option>
              </select>
            </div>
            <div class="form-group">
              <label>Page</label>
              <select v-model="selectedPageId" class="form-select" :disabled="!selectedNotebookId">
                <option value="">Select page...</option>
                <option v-for="pg in pagesForNotebook" :key="pg.id" :value="pg.id">
                  {{ pg.title }}
                </option>
              </select>
            </div>
          </div>
          <div class="form-group">
            <label>Title (optional)</label>
            <input
              v-model="queryTitle"
              type="text"
              class="form-input"
              placeholder="Auto-generated from query if empty"
            />
          </div>
        </div>
      </section>

      <!-- Execute Button -->
      <div class="execute-section">
        <button
          class="btn btn-primary execute-btn"
          :disabled="executing || !query.trim()"
          @click="executeQuery"
        >
          {{ executing ? "Executing..." : "▶ Execute Query" }}
        </button>
        <div class="max-rows-group">
          <label>Max Rows:</label>
          <input v-model.number="maxRows" type="number" min="1" max="10000" class="max-rows-input" />
        </div>
      </div>
    </div>

    <!-- Right Panel: Results -->
    <div class="results-panel">
      <!-- Results Header -->
      <div class="results-header">
        <h2>Results</h2>
        <div v-if="executionTime !== null" class="execution-stats">
          <span class="stat">{{ rowCount }} rows</span>
          <span class="stat">{{ executionTime.toFixed(3) }}s</span>
        </div>
      </div>

      <!-- Error Display -->
      <div v-if="error" class="error-display">
        <h3>Error</h3>
        <pre class="error-content">{{ error }}</pre>
      </div>

      <!-- Results Table -->
      <div v-else-if="results && results.length > 0" class="results-table-container">
        <table class="results-table">
          <thead>
            <tr>
              <th v-for="col in columns" :key="col">{{ col }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, idx) in results" :key="idx">
              <td v-for="col in columns" :key="col">{{ formatValue(row[col]) }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Empty State -->
      <div v-else-if="results && results.length === 0" class="empty-results">
        <p>Query executed successfully. No rows returned.</p>
      </div>

      <div v-else class="empty-state">
        <span class="empty-icon">📊</span>
        <p>Execute a query to see results</p>
      </div>

      <!-- Query History -->
      <div v-if="queryHistory.length > 0" class="history-section">
        <h3>Recent Queries</h3>
        <div class="history-list">
          <button
            v-for="entry in queryHistory"
            :key="entry.id"
            class="history-item"
            @click="loadHistoryQuery(entry)"
          >
            <span class="history-title">{{ entry.title }}</span>
            <span class="history-time">{{ new Date(entry.created_at).toLocaleTimeString() }}</span>
            <span class="history-status" :class="entry.status">{{ entry.status }}</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.sql-viewer {
  display: grid;
  grid-template-columns: 1fr 1fr;
  min-height: 100vh;
  background: var(--color-background);
}

/* Left Panel - Query Editor */
.query-panel {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  padding: 1.5rem;
  background: var(--color-surface);
  border-right: 1px solid var(--color-border);
  overflow-y: auto;
}

.panel-header {
  margin-bottom: 0.5rem;
}

.panel-header h1 {
  font-family: var(--font-handwritten);
  font-size: 2rem;
  color: var(--color-primary);
  margin: 0;
}

.subtitle {
  font-size: 0.875rem;
  color: var(--color-text-secondary);
  margin-top: 0.25rem;
}

.section-title {
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--color-text-secondary);
  margin-bottom: 0.5rem;
  font-family: var(--font-mono);
}

/* Connection Section */
.connection-section {
  background: var(--color-background);
  padding: 1rem;
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
}

.connection-input-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.connection-input {
  padding: 0.625rem 0.75rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  font-family: var(--font-mono);
  font-size: 0.875rem;
  background: var(--color-surface);
}

.connection-input:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 2px rgba(45, 90, 39, 0.1);
}

.template-buttons {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.template-btn {
  padding: 0.25rem 0.5rem;
  font-size: 0.75rem;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  cursor: pointer;
  color: var(--color-text-secondary);
  font-family: var(--font-body);
}

.template-btn:hover {
  background: var(--color-primary);
  border-color: var(--color-primary);
  color: white;
}

/* Query Section */
.query-section {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 200px;
}

.query-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}

.shortcut-hint {
  font-size: 0.75rem;
  color: var(--color-text-secondary);
  font-family: var(--font-mono);
}

.query-editor {
  flex: 1;
  width: 100%;
  padding: 1rem;
  font-family: var(--font-mono);
  font-size: 0.875rem;
  line-height: 1.6;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  resize: vertical;
  min-height: 200px;
}

.query-editor:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 2px rgba(45, 90, 39, 0.1);
}

/* Tracking Section */
.tracking-section {
  background: var(--color-background);
  padding: 1rem;
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
}

.tracking-header {
  margin-bottom: 0.75rem;
}

.auto-save-toggle {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
  font-size: 0.875rem;
  font-weight: 500;
}

.auto-save-toggle input {
  width: 1rem;
  height: 1rem;
  accent-color: var(--color-primary);
}

.tracking-form {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.75rem;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.form-group label {
  font-size: 0.75rem;
  color: var(--color-text-secondary);
  font-weight: 500;
}

.form-select,
.form-input {
  padding: 0.5rem 0.625rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  font-size: 0.875rem;
  background: var(--color-surface);
  font-family: var(--font-body);
}

.form-select:focus,
.form-input:focus {
  outline: none;
  border-color: var(--color-primary);
}

.form-select:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Execute Section */
.execute-section {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.execute-btn {
  flex: 1;
  padding: 0.75rem 1.5rem;
  font-size: 1rem;
  font-weight: 600;
}

.execute-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.max-rows-group {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.75rem;
  color: var(--color-text-secondary);
}

.max-rows-input {
  width: 80px;
  padding: 0.375rem 0.5rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  font-size: 0.875rem;
  font-family: var(--font-mono);
}

/* Right Panel - Results */
.results-panel {
  display: flex;
  flex-direction: column;
  background: var(--color-surface);
  overflow: hidden;
}

.results-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.5rem;
  border-bottom: 1px solid var(--color-border);
  background: var(--color-background);
}

.results-header h2 {
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--color-text);
  margin: 0;
}

.execution-stats {
  display: flex;
  gap: 1rem;
}

.stat {
  font-family: var(--font-mono);
  font-size: 0.875rem;
  color: var(--color-text-secondary);
  background: var(--color-surface);
  padding: 0.25rem 0.5rem;
  border-radius: var(--radius-sm);
}

/* Error Display */
.error-display {
  padding: 1.5rem;
  background: #fdf5f5;
  border-left: 4px solid var(--color-error);
  margin: 1rem;
  border-radius: var(--radius-md);
}

.error-display h3 {
  color: var(--color-error);
  margin-bottom: 0.5rem;
  font-size: 0.875rem;
  font-weight: 600;
}

.error-content {
  font-family: var(--font-mono);
  font-size: 0.8rem;
  color: var(--color-error);
  white-space: pre-wrap;
  word-break: break-word;
}

/* Results Table */
.results-table-container {
  flex: 1;
  overflow: auto;
  padding: 1rem;
}

.results-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.875rem;
  font-family: var(--font-mono);
}

.results-table th,
.results-table td {
  padding: 0.5rem 0.75rem;
  text-align: left;
  border: 1px solid var(--color-border);
}

.results-table th {
  background: var(--color-background);
  font-weight: 600;
  position: sticky;
  top: 0;
  color: var(--color-text);
}

.results-table tr:nth-child(even) {
  background: rgba(245, 240, 230, 0.5);
}

.results-table tr:hover {
  background: rgba(45, 90, 39, 0.05);
}

.results-table td {
  max-width: 300px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* Empty States */
.empty-results {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 3rem;
  color: var(--color-text-secondary);
  font-style: italic;
}

.empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: var(--color-text-secondary);
  padding: 3rem;
}

.empty-icon {
  font-size: 3rem;
  margin-bottom: 1rem;
  opacity: 0.5;
}

/* History Section */
.history-section {
  border-top: 1px solid var(--color-border);
  padding: 1rem 1.5rem;
  background: var(--color-background);
}

.history-section h3 {
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--color-text-secondary);
  margin-bottom: 0.75rem;
  font-family: var(--font-mono);
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  max-height: 200px;
  overflow-y: auto;
}

.history-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.5rem 0.75rem;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  cursor: pointer;
  text-align: left;
  font-size: 0.8rem;
  transition: all 0.2s;
}

.history-item:hover {
  border-color: var(--color-primary);
  background: rgba(45, 90, 39, 0.05);
}

.history-title {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--color-text);
}

.history-time {
  font-family: var(--font-mono);
  font-size: 0.7rem;
  color: var(--color-text-secondary);
}

.history-status {
  font-family: var(--font-mono);
  font-size: 0.65rem;
  padding: 0.125rem 0.375rem;
  border-radius: var(--radius-sm);
  text-transform: uppercase;
  font-weight: 600;
}

.history-status.completed {
  background: #e8f5e3;
  color: var(--color-success);
}

.history-status.failed {
  background: #fbe8e8;
  color: var(--color-error);
}

/* Responsive */
@media (max-width: 1024px) {
  .sql-viewer {
    grid-template-columns: 1fr;
    grid-template-rows: auto 1fr;
  }
  
  .query-panel {
    border-right: none;
    border-bottom: 1px solid var(--color-border);
    max-height: 50vh;
  }
  
  .results-panel {
    min-height: 50vh;
  }
}
</style>
