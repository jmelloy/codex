<template>
  <div class="custom-block database-block">
    <div class="block-header">
      <span class="block-icon">&#x1F5C4;</span>
      <span class="block-title">{{ isChildrenMode ? 'Pages' : 'Database' }}</span>
      <span v-if="!isChildrenMode" class="source-badge">{{ config.source || 'notebook' }}</span>

      <!-- View mode switcher -->
      <div v-if="!loading && (isChildrenMode ? childPages.length > 0 : result)" class="view-switcher">
        <button
          class="view-btn"
          :class="{ active: activeDisplayMode === 'table' }"
          @click="activeDisplayMode = 'table'"
          title="Table view"
        >
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.5">
            <rect x="1" y="1" width="12" height="12" rx="1" />
            <line x1="1" y1="5" x2="13" y2="5" />
            <line x1="1" y1="9" x2="13" y2="9" />
            <line x1="5" y1="1" x2="5" y2="13" />
          </svg>
        </button>
        <button
          v-if="isChildrenMode"
          class="view-btn"
          :class="{ active: activeDisplayMode === 'gallery' }"
          @click="activeDisplayMode = 'gallery'"
          title="Gallery view"
        >
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.5">
            <rect x="1" y="1" width="5" height="5" rx="1" />
            <rect x="8" y="1" width="5" height="5" rx="1" />
            <rect x="1" y="8" width="5" height="5" rx="1" />
            <rect x="8" y="8" width="5" height="5" rx="1" />
          </svg>
        </button>
      </div>

      <button v-if="!loading" class="refresh-btn" @click="execute" title="Refresh">&#x21bb;</button>
      <button class="edit-btn" @click="$emit('edit')" title="Edit config">&#x270E;</button>
    </div>
    <div class="block-content">
      <!-- Loading state -->
      <div v-if="loading" class="loading">
        <div class="loading-spinner"></div>
        <span>{{ isChildrenMode ? 'Loading pages...' : 'Running query...' }}</span>
      </div>

      <!-- Error state -->
      <div v-else-if="error" class="error">
        <div v-if="config.query" class="query-display"><code>{{ config.query }}</code></div>
        <div class="error-message">{{ error }}</div>
        <button class="retry-btn" @click="execute">Retry</button>
      </div>

      <!-- Children mode: page list -->
      <div v-else-if="isChildrenMode && childPages.length > 0" class="children-list">
        <div class="result-meta">
          <span class="row-count">{{ childPages.length }} page{{ childPages.length !== 1 ? 's' : '' }}</span>
          <span v-if="propertyColumns.length > 0" class="property-count">
            {{ propertyColumns.length }} propert{{ propertyColumns.length !== 1 ? 'ies' : 'y' }}
          </span>
        </div>

        <!-- Table display -->
        <div v-if="activeDisplayMode === 'table'" class="table-wrapper">
          <table>
            <thead>
              <tr>
                <th class="sortable-th" @click="toggleSort('title')">
                  Title
                  <span v-if="sortColumn === 'title'" class="sort-indicator">
                    {{ sortDirection === 'asc' ? '&#x25B2;' : '&#x25BC;' }}
                  </span>
                </th>
                <th
                  v-for="col in propertyColumns"
                  :key="col"
                  class="sortable-th property-th"
                  @click="toggleSort('prop:' + col)"
                >
                  {{ col }}
                  <span v-if="sortColumn === 'prop:' + col" class="sort-indicator">
                    {{ sortDirection === 'asc' ? '&#x25B2;' : '&#x25BC;' }}
                  </span>
                </th>
                <th class="sortable-th" @click="toggleSort('updated_at')">
                  Updated
                  <span v-if="sortColumn === 'updated_at'" class="sort-indicator">
                    {{ sortDirection === 'asc' ? '&#x25B2;' : '&#x25BC;' }}
                  </span>
                </th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="page in sortedChildPages"
                :key="page.block_id"
                class="page-row"
                @click="$emit('navigatePage', page)"
              >
                <td>
                  <span class="page-icon">{{ getPageIcon(page) }}</span>
                  <span class="page-name">{{ page.title || page.path }}</span>
                </td>
                <td v-for="col in propertyColumns" :key="col" class="property-cell">
                  <span
                    class="property-value"
                    :class="getPropertyClass(page.properties?.[col])"
                    :title="formatPropertyValue(page.properties?.[col])"
                  >{{ formatPropertyValue(page.properties?.[col]) }}</span>
                </td>
                <td class="date-cell">{{ formatDate(page.updated_at) }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Gallery display -->
        <div v-else-if="activeDisplayMode === 'gallery'" class="gallery-grid">
          <div
            v-for="page in sortedChildPages"
            :key="page.block_id"
            class="gallery-card"
            @click="$emit('navigatePage', page)"
          >
            <div class="gallery-card-cover">
              <img
                v-if="getPageCover(page)"
                :src="getPageCover(page)!"
                alt=""
                class="gallery-card-image"
              />
              <div v-else class="gallery-card-placeholder">
                <span class="gallery-card-icon">{{ getPageIcon(page) }}</span>
              </div>
            </div>
            <div class="gallery-card-body">
              <div class="gallery-card-title">{{ page.title || page.path }}</div>
              <div v-if="galleryPropertyColumns.length > 0" class="gallery-card-props">
                <div
                  v-for="col in galleryPropertyColumns"
                  :key="col"
                  class="gallery-card-prop"
                >
                  <span class="gallery-prop-label">{{ col }}</span>
                  <span
                    class="gallery-prop-value"
                    :class="getPropertyClass(page.properties?.[col])"
                  >{{ formatPropertyValue(page.properties?.[col]) }}</span>
                </div>
              </div>
              <div class="gallery-card-date">{{ formatDate(page.updated_at) }}</div>
            </div>
          </div>
        </div>

        <!-- Card list (fallback) -->
        <div v-else class="children-cards">
          <div
            v-for="page in sortedChildPages"
            :key="page.block_id"
            class="page-card"
            @click="$emit('navigatePage', page)"
          >
            <span class="page-icon">&#x1F4C4;</span>
            <span class="page-name">{{ page.title || page.path }}</span>
          </div>
        </div>
      </div>

      <!-- Children mode: empty -->
      <div v-else-if="isChildrenMode && childPages.length === 0 && !loading" class="empty-children">
        <div class="block-note">
          <em>No pages yet. Create a subpage to get started.</em>
        </div>
      </div>

      <!-- Query results -->
      <div v-else-if="result" class="query-result">
        <div class="result-meta">
          <span class="row-count">{{ result.total }} row{{ result.total !== 1 ? 's' : '' }}</span>
          <span v-if="result.truncated" class="truncated-badge">truncated</span>
        </div>

        <!-- Table display (default) -->
        <div v-if="activeDisplayMode === 'table'" class="table-wrapper">
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
import { ref, computed, onMounted, watch } from "vue"
import { executeIntegrationEndpoint } from "../../services/integration"
import { blockService, type Block } from "../../services/codex"

interface DatabaseConfig {
  query?: string
  source?: string
  display?: string
  limit?: string | number
  properties?: string[]
  cover?: string
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
  workspaceId?: string
  notebookId?: string
  parentBlockId?: string
}

const props = defineProps<Props>()

const emit = defineEmits<{
  navigatePage: [block: Block]
  edit: []
  updateConfig: [config: Record<string, any>]
}>()

const loading = ref(false)
const error = ref<string | null>(null)
const result = ref<QueryResult | null>(null)
const childPages = ref<Block[]>([])
const sortColumn = ref<string | null>(null)
const sortDirection = ref<"asc" | "desc">("asc")
const activeDisplayMode = ref<string>(props.config.display || "table")

const isChildrenMode = computed(() => {
  const source = props.config.source
  return source === "children" || source === "pages" || (!props.config.query && !source)
})

const formattedJson = computed(() => {
  if (!result.value) return ""
  return JSON.stringify(result.value.rows, null, 2)
})

/** Collect all unique property keys from child pages */
const propertyColumns = computed(() => {
  const configured = props.config.properties
  if (configured && Array.isArray(configured) && configured.length > 0) {
    return configured
  }
  // Auto-discover from child page properties
  const keys = new Set<string>()
  for (const page of childPages.value) {
    if (page.properties) {
      for (const key of Object.keys(page.properties)) {
        // Skip internal/system properties
        if (!key.startsWith("_") && key !== "icon" && key !== "cover") {
          keys.add(key)
        }
      }
    }
  }
  return Array.from(keys).sort()
})

/** Show up to 3 property columns in gallery cards */
const galleryPropertyColumns = computed(() => {
  return propertyColumns.value.slice(0, 3)
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

const sortedChildPages = computed(() => {
  if (!sortColumn.value) return childPages.value
  const col = sortColumn.value
  const dir = sortDirection.value === "asc" ? 1 : -1
  return [...childPages.value].sort((a, b) => {
    let va: any, vb: any
    if (col.startsWith("prop:")) {
      const propKey = col.slice(5)
      va = a.properties?.[propKey]
      vb = b.properties?.[propKey]
    } else {
      va = (a as any)[col]
      vb = (b as any)[col]
    }
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

function formatDate(dateStr: string): string {
  if (!dateStr) return ""
  try {
    const d = new Date(dateStr)
    return d.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" })
  } catch {
    return dateStr
  }
}

function formatPropertyValue(value: any): string {
  if (value === null || value === undefined) return ""
  if (Array.isArray(value)) return value.join(", ")
  if (typeof value === "boolean") return value ? "Yes" : "No"
  if (typeof value === "object") return JSON.stringify(value)
  return String(value)
}

function getPropertyClass(value: any): string {
  if (value === null || value === undefined) return "prop-empty"
  if (typeof value === "boolean") return value ? "prop-true" : "prop-false"
  if (Array.isArray(value)) return "prop-array"
  if (typeof value === "number") return "prop-number"
  return "prop-text"
}

function getPageIcon(page: Block): string {
  return page.properties?.icon || "\u{1F4C4}"
}

function getPageCover(page: Block): string | null {
  const cover = page.properties?.cover
  if (!cover) return null
  // If it's a relative path, resolve it
  if (cover.startsWith("http://") || cover.startsWith("https://")) return cover
  if (props.workspaceId && props.notebookId) {
    return `/api/v1/workspaces/${props.workspaceId}/notebooks/${props.notebookId}/blocks/path/${encodeURIComponent(cover)}/content`
  }
  return null
}

async function fetchChildren() {
  if (!props.workspaceId || !props.notebookId || !props.parentBlockId) {
    childPages.value = []
    return
  }

  loading.value = true
  error.value = null

  try {
    const response = await blockService.getChildren(
      props.parentBlockId,
      props.notebookId,
      props.workspaceId,
    )
    childPages.value = (response.children || []).filter(
      (b: Block) => b.block_type === "page"
    )
  } catch (err) {
    error.value = err instanceof Error ? err.message : "Failed to load child pages"
  } finally {
    loading.value = false
  }
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

async function execute() {
  if (isChildrenMode.value) {
    await fetchChildren()
  } else {
    await runQuery()
  }
}

// Watch config.display to update active mode
watch(() => props.config.display, (newVal) => {
  if (newVal) activeDisplayMode.value = newVal
})

onMounted(() => {
  execute()
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
  border-color: var(--color-border-medium, #e0e0e0);
  background: var(--color-bg-primary, #fff);
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

/* View switcher */
.view-switcher {
  display: flex;
  gap: 2px;
  margin-left: auto;
  background: var(--color-bg-tertiary, #f3f4f6);
  border-radius: 6px;
  padding: 2px;
}

.view-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: none;
  background: transparent;
  border-radius: 4px;
  cursor: pointer;
  color: var(--color-text-secondary, #6b7280);
  transition: background-color 0.15s, color 0.15s;
}

.view-btn:hover {
  background: var(--color-bg-quaternary, #e5e7eb);
}

.view-btn.active {
  background: var(--color-bg-primary, #fff);
  color: var(--color-text-primary, #111827);
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.08);
}

.refresh-btn, .retry-btn, .edit-btn {
  background: none;
  border: 1px solid var(--color-border-medium, #d1d5db);
  border-radius: 4px;
  padding: 2px 8px;
  cursor: pointer;
  font-size: var(--text-sm, 0.875rem);
  color: var(--color-text-secondary, #6b7280);
}

.refresh-btn { margin-left: 0; }
.edit-btn { margin-left: 0; }

.refresh-btn:hover, .retry-btn:hover, .edit-btn:hover {
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

.property-count {
  background: var(--color-bg-tertiary, #f3f4f6);
  padding: 1px 6px;
  border-radius: 3px;
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
  max-height: 500px;
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

.property-th {
  font-style: italic;
  font-weight: 500;
}

.sort-indicator {
  font-size: 0.6rem;
  margin-left: 4px;
}

.empty-table, .empty-children {
  padding: 16px;
  text-align: center;
  color: var(--color-text-secondary, #6b7280);
}

/* Property cells */
.property-cell {
  font-size: var(--text-xs, 0.75rem);
}

.property-value {
  display: inline-block;
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.prop-empty {
  color: var(--color-text-placeholder, #d1d5db);
}

.prop-true {
  color: #059669;
  font-weight: 500;
}

.prop-false {
  color: var(--color-text-tertiary, #9ca3af);
}

.prop-number {
  font-family: monospace;
  color: #6366f1;
}

.prop-array {
  color: #8b5cf6;
}

/* Children mode styles */
.page-row {
  cursor: pointer;
}

.page-row:hover {
  background: var(--color-bg-hover, #f5f5f5);
}

.page-row td {
  padding: 8px 10px;
}

.page-icon {
  margin-right: 6px;
}

.page-name {
  font-weight: 500;
}

.date-cell {
  color: var(--color-text-secondary, #6b7280);
  font-size: var(--text-xs, 0.75rem);
}

.children-cards {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.page-card {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: 6px;
  cursor: pointer;
  transition: background-color 0.1s;
}

.page-card:hover {
  background: var(--color-bg-hover, #f5f5f5);
}

/* Gallery view */
.gallery-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 12px;
}

.gallery-card {
  border: 1px solid var(--color-border-light, #e5e7eb);
  border-radius: 8px;
  overflow: hidden;
  cursor: pointer;
  transition: box-shadow 0.15s, border-color 0.15s;
  background: var(--color-bg-primary, #fff);
}

.gallery-card:hover {
  border-color: var(--color-border-medium, #d1d5db);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.gallery-card-cover {
  width: 100%;
  height: 120px;
  overflow: hidden;
  background: var(--color-bg-tertiary, #f3f4f6);
}

.gallery-card-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.gallery-card-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, var(--color-bg-tertiary, #f3f4f6), var(--color-bg-secondary, #f9fafb));
}

.gallery-card-icon {
  font-size: 2.5rem;
  opacity: 0.5;
}

.gallery-card-body {
  padding: 10px 12px;
}

.gallery-card-title {
  font-weight: 600;
  font-size: var(--text-sm, 0.875rem);
  margin-bottom: 6px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--color-text-primary, #111827);
}

.gallery-card-props {
  display: flex;
  flex-direction: column;
  gap: 3px;
  margin-bottom: 6px;
}

.gallery-card-prop {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: var(--text-xs, 0.75rem);
}

.gallery-prop-label {
  color: var(--color-text-tertiary, #9ca3af);
  min-width: 50px;
  flex-shrink: 0;
}

.gallery-prop-value {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--color-text-secondary, #6b7280);
}

.gallery-card-date {
  font-size: 0.6875rem;
  color: var(--color-text-placeholder, #d1d5db);
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
