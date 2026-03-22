<template>
  <div class="custom-block database-block">
    <div class="block-header">
      <span class="block-icon">&#x1F5C4;</span>
      <span class="block-title">Database</span>
      <span class="source-badge">{{ config.source || 'notebook' }}</span>
      <button v-if="!loading" class="refresh-btn" @click="runQuery" title="Refresh">&#x21bb;</button>
    </div>
    <div class="block-content">
      <!-- Loading state -->
      <div v-if="loading" class="loading">
        <div class="loading-spinner"></div>
        <span>Running query...</span>
      </div>

      <!-- Error state -->
      <div v-else-if="error" class="error">
        <div class="query-display"><code>{{ config.query }}</code></div>
        <div class="error-message">{{ error }}</div>
        <button class="retry-btn" @click="runQuery">Retry</button>
      </div>

      <!-- Results -->
      <div v-else-if="result" class="query-result">
        <div class="result-meta">
          <span class="row-count">{{ result.total }} row{{ result.total !== 1 ? 's' : '' }}</span>
          <span v-if="result.truncated" class="truncated-badge">truncated</span>
        </div>

        <!-- Table display (default) -->
        <div v-if="displayMode === 'table'" class="table-wrapper">
          <table v-if="result.columns.length > 0">
            <thead>
              <tr>
                <th
                  v-for="col in result.columns"
                  :key="col"
                  @click="toggleSort(col)"
                  class="sortable-th"
                >
                  {{ col }}
                  <span v-if="sortColumn === col" class="sort-indicator">
                    {{ sortDirection === 'asc' ? '&#x25B2;' : '&#x25BC;' }}
                  </span>
                </th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, i) in sortedRows" :key="i">
                <td v-for="col in result.columns" :key="col">{{ formatCell(row[col]) }}</td>
              </tr>
            </tbody>
          </table>
          <div v-else class="empty-table">No results</div>
        </div>

        <!-- JSON display -->
        <pre v-else class="json-output"><code>{{ formattedJson }}</code></pre>
      </div>

      <!-- Not configured -->
      <div v-else class="not-configured">
        <div class="block-note">
          <em>Specify a SQL query to run against the notebook database.</em>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue"
import { executeIntegrationEndpoint } from "../../services/integration"

interface DatabaseConfig {
  query?: string
  source?: string
  display?: string
  limit?: string | number
  [key: string]: any
}

interface QueryResult {
  columns: string[]
  rows: Record<string, any>[]
  total: number
  truncated: boolean
}

interface Props {
  config: DatabaseConfig
  workspaceId?: number
  notebookId?: number
}

const props = defineProps<Props>()

const loading = ref(false)
const error = ref<string | null>(null)
const result = ref<QueryResult | null>(null)
const sortColumn = ref<string | null>(null)
const sortDirection = ref<"asc" | "desc">("asc")

const displayMode = computed(() => props.config.display || "table")

const formattedJson = computed(() => {
  if (!result.value) return ""
  return JSON.stringify(result.value.rows, null, 2)
})

const sortedRows = computed(() => {
  if (!result.value || !sortColumn.value) return result.value?.rows || []
  const col = sortColumn.value
  const dir = sortDirection.value === "asc" ? 1 : -1
  return [...result.value.rows].sort((a, b) => {
    const va = a[col]
    const vb = b[col]
    if (va === vb) return 0
    if (va === null || va === undefined) return 1
    if (vb === null || vb === undefined) return -1
    if (typeof va === "number" && typeof vb === "number") return (va - vb) * dir
    return String(va).localeCompare(String(vb)) * dir
  })
})

function toggleSort(col: string) {
  if (sortColumn.value === col) {
    sortDirection.value = sortDirection.value === "asc" ? "desc" : "asc"
  } else {
    sortColumn.value = col
    sortDirection.value = "asc"
  }
}

function formatCell(value: any): string {
  if (value === null || value === undefined) return ""
  if (typeof value === "object") return JSON.stringify(value)
  return String(value)
}

async function runQuery() {
  if (!props.config.query || !props.workspaceId || !props.notebookId) return

  loading.value = true
  error.value = null

  try {
    const response = await executeIntegrationEndpoint(
      "database-query",
      props.workspaceId,
      props.notebookId,
      "query",
      {
        query: props.config.query,
        source: props.config.source || "notebook",
        limit: props.config.limit ? parseInt(String(props.config.limit)) : undefined,
      }
    )

    if (response.success) {
      result.value = response.data as QueryResult
    } else {
      error.value = response.error || "Query failed"
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : "Failed to execute query"
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  runQuery()
})
</script>

<style scoped>
.custom-block {
  border: 2px solid var(--color-border-medium, #e5e7eb);
  border-radius: var(--radius-md, 8px);
  padding: var(--spacing-lg, 16px);
  margin: var(--spacing-lg, 16px) 0;
  background: var(--color-bg-secondary, #f9fafb);
}

.database-block {
  border-color: #059669;
  background: var(--color-bg-secondary, #f0fdf4);
}

.block-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm, 8px);
  margin-bottom: var(--spacing-md, 12px);
  font-weight: var(--font-semibold, 600);
  color: var(--color-text-primary, #111827);
}

.block-icon {
  font-size: var(--text-xl, 1.25rem);
}

.block-title {
  font-size: var(--text-lg, 1.125rem);
}

.source-badge {
  font-size: var(--text-xs, 0.75rem);
  font-weight: 600;
  padding: 2px 6px;
  border-radius: 4px;
  background: #d1fae5;
  color: #065f46;
  font-family: monospace;
}

.refresh-btn, .retry-btn {
  margin-left: auto;
  background: none;
  border: 1px solid var(--color-border-medium, #d1d5db);
  border-radius: 4px;
  padding: 2px 8px;
  cursor: pointer;
  font-size: var(--text-sm, 0.875rem);
  color: var(--color-text-secondary, #6b7280);
}

.refresh-btn:hover, .retry-btn:hover {
  background: var(--color-bg-tertiary, #f3f4f6);
}

.block-content {
  color: var(--color-text-primary, #111827);
}

.loading {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm, 8px);
  padding: var(--spacing-lg, 16px);
  color: var(--color-text-secondary, #6b7280);
}

.loading-spinner {
  width: 20px;
  height: 20px;
  border: 2px solid var(--color-border-medium, #e5e7eb);
  border-top-color: #059669;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.result-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  font-size: var(--text-xs, 0.75rem);
  color: var(--color-text-secondary, #6b7280);
}

.truncated-badge {
  background: #fef3c7;
  color: #92400e;
  padding: 1px 4px;
  border-radius: 3px;
  font-weight: 600;
}

.table-wrapper {
  overflow-x: auto;
  max-height: 400px;
  overflow-y: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--text-sm, 0.875rem);
}

th, td {
  text-align: left;
  padding: 6px 10px;
  border: 1px solid var(--color-border-light, #e5e7eb);
  max-width: 300px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sortable-th {
  cursor: pointer;
  user-select: none;
  background: var(--color-bg-tertiary, #f3f4f6);
  font-weight: 600;
  position: sticky;
  top: 0;
}

.sortable-th:hover {
  background: var(--color-bg-quaternary, #e5e7eb);
}

.sort-indicator {
  font-size: 0.6rem;
  margin-left: 4px;
}

.empty-table {
  padding: 16px;
  text-align: center;
  color: var(--color-text-secondary, #6b7280);
}

.json-output {
  background: var(--color-bg-primary, #fff);
  border: 1px solid var(--color-border-light, #e5e7eb);
  border-radius: 4px;
  padding: 12px;
  overflow-x: auto;
  font-size: var(--text-sm, 0.875rem);
  max-height: 400px;
  overflow-y: auto;
  white-space: pre-wrap;
  word-break: break-word;
}

.query-display code {
  font-size: var(--text-sm, 0.875rem);
  background: var(--color-bg-tertiary, #f3f4f6);
  padding: 4px 8px;
  border-radius: 4px;
  display: block;
  margin-bottom: 8px;
  white-space: pre-wrap;
}

.error-message {
  color: #dc2626;
  font-size: var(--text-sm, 0.875rem);
  margin-bottom: 8px;
}

.block-note {
  padding: var(--spacing-sm, 8px);
  background: rgba(255, 255, 255, 0.5);
  border-radius: var(--radius-sm, 4px);
  font-size: var(--text-sm, 0.875rem);
  color: var(--color-text-secondary, #6b7280);
}
</style>
