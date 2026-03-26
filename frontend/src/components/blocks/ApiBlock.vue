<template>
  <div class="custom-block api-block">
    <div class="block-header">
      <span class="block-icon">&#x1F310;</span>
      <span class="block-title">API</span>
      <span v-if="config.method" class="method-badge" :class="methodClass">{{ config.method || 'GET' }}</span>
      <button v-if="!loading" class="refresh-btn" @click="fetchData" title="Refresh">&#x21bb;</button>
    </div>
    <div class="block-content">
      <!-- Loading state -->
      <div v-if="loading" class="loading">
        <div class="loading-spinner"></div>
        <span>Fetching {{ config.url }}...</span>
      </div>

      <!-- Error state -->
      <div v-else-if="error" class="error">
        <div class="error-url">{{ config.method || 'GET' }} {{ config.url }}</div>
        <div class="error-message">{{ error }}</div>
        <button class="retry-btn" @click="fetchData">Retry</button>
      </div>

      <!-- Response data -->
      <div v-else-if="responseData !== null" class="response-data">
        <div class="response-meta">
          <span class="response-url">{{ config.method || 'GET' }} {{ config.url }}</span>
        </div>

        <!-- JSON display -->
        <pre v-if="displayMode === 'json'" class="json-output"><code>{{ formattedJson }}</code></pre>

        <!-- Table display -->
        <div v-else-if="displayMode === 'table' && tableData" class="table-wrapper">
          <table>
            <thead>
              <tr>
                <th v-for="col in tableData.columns" :key="col">{{ col }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, i) in tableData.rows" :key="i">
                <td v-for="col in tableData.columns" :key="col">{{ formatCell(row[col]) }}</td>
              </tr>
            </tbody>
          </table>
          <div v-if="tableData.rows.length === 0" class="empty-table">No data returned</div>
        </div>

        <!-- Text display -->
        <pre v-else class="text-output">{{ typeof responseData === 'string' ? responseData : JSON.stringify(responseData, null, 2) }}</pre>
      </div>

      <!-- Not configured -->
      <div v-else class="not-configured">
        <code>{{ config.url || 'No URL specified' }}</code>
        <div class="block-note">
          <em>Specify a URL to fetch data from.</em>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from "vue"
import { executeIntegrationEndpoint } from "../../services/integration"

interface ApiConfig {
  url?: string
  method?: string
  headers?: string | Record<string, string>
  body?: string
  display?: string
  refresh?: string | number
  [key: string]: any
}

interface Props {
  config: ApiConfig
  workspaceId?: string
  notebookId?: string
}

const props = defineProps<Props>()

const loading = ref(false)
const error = ref<string | null>(null)
const responseData = ref<any>(null)
let refreshTimer: ReturnType<typeof setInterval> | null = null

const displayMode = computed(() => props.config.display || "json")

const methodClass = computed(() => {
  const method = (props.config.method || "GET").toUpperCase()
  return `method-${method.toLowerCase()}`
})

const formattedJson = computed(() => {
  if (responseData.value === null) return ""
  try {
    return JSON.stringify(responseData.value, null, 2)
  } catch {
    return String(responseData.value)
  }
})

interface TableData {
  columns: string[]
  rows: Record<string, any>[]
}

const tableData = computed((): TableData | null => {
  const data = responseData.value
  if (!data) return null

  // If it's an array of objects, use as-is
  if (Array.isArray(data)) {
    if (data.length === 0) return { columns: [], rows: [] }
    const columns = Object.keys(data[0])
    return { columns, rows: data }
  }

  // If it's a single object, display as key-value table
  if (typeof data === "object") {
    return {
      columns: ["Key", "Value"],
      rows: Object.entries(data).map(([k, v]) => ({ Key: k, Value: v })),
    }
  }

  return null
})

function formatCell(value: any): string {
  if (value === null || value === undefined) return ""
  if (typeof value === "object") return JSON.stringify(value)
  return String(value)
}

function parseHeaders(headers: string | Record<string, string> | undefined): Record<string, string> {
  if (!headers) return {}
  if (typeof headers === "object") return headers
  try {
    return JSON.parse(headers)
  } catch {
    // Try key: value format
    const result: Record<string, string> = {}
    String(headers)
      .split(",")
      .forEach((h) => {
        const [k, ...rest] = h.split(":")
        if (k && rest.length) result[k.trim()] = rest.join(":").trim()
      })
    return result
  }
}

async function fetchData() {
  if (!props.config.url || !props.workspaceId || !props.notebookId) return

  loading.value = true
  error.value = null

  try {
    const result = await executeIntegrationEndpoint(
      "api-fetch",
      props.workspaceId,
      props.notebookId,
      "fetch",
      {
        url: props.config.url,
        method: (props.config.method || "GET").toUpperCase(),
        headers: parseHeaders(props.config.headers),
        body: props.config.body || undefined,
      }
    )

    if (result.success) {
      responseData.value = result.data
    } else {
      error.value = result.error || "Request failed"
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : "Failed to fetch data"
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchData()

  // Set up auto-refresh if configured
  const interval = parseInt(String(props.config.refresh || 0))
  if (interval > 0) {
    refreshTimer = setInterval(fetchData, interval * 1000)
  }
})

onUnmounted(() => {
  if (refreshTimer) {
    clearInterval(refreshTimer)
  }
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

.api-block {
  border-color: #6366f1;
  background: var(--color-bg-secondary, #f8f7ff);
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

.method-badge {
  font-size: var(--text-xs, 0.75rem);
  font-weight: 700;
  padding: 2px 6px;
  border-radius: 4px;
  text-transform: uppercase;
  font-family: monospace;
}

.method-get { background: #d1fae5; color: #065f46; }
.method-post { background: #dbeafe; color: #1e40af; }
.method-put { background: #fef3c7; color: #92400e; }
.method-delete { background: #fee2e2; color: #991b1b; }

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
  border-top-color: #6366f1;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.response-meta {
  margin-bottom: 8px;
}

.response-url {
  font-family: monospace;
  font-size: var(--text-xs, 0.75rem);
  color: var(--color-text-secondary, #6b7280);
}

.json-output, .text-output {
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

.table-wrapper {
  overflow-x: auto;
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

th {
  background: var(--color-bg-tertiary, #f3f4f6);
  font-weight: 600;
  position: sticky;
  top: 0;
}

.empty-table {
  padding: 16px;
  text-align: center;
  color: var(--color-text-secondary, #6b7280);
}

.error-url {
  font-family: monospace;
  font-size: var(--text-sm, 0.875rem);
  margin-bottom: 4px;
}

.error-message {
  color: #dc2626;
  font-size: var(--text-sm, 0.875rem);
  margin-bottom: 8px;
}

.not-configured code {
  display: block;
  margin-bottom: 8px;
  font-size: var(--text-sm, 0.875rem);
}

.block-note {
  padding: var(--spacing-sm, 8px);
  background: rgba(255, 255, 255, 0.5);
  border-radius: var(--radius-sm, 4px);
  font-size: var(--text-sm, 0.875rem);
  color: var(--color-text-secondary, #6b7280);
}
</style>
