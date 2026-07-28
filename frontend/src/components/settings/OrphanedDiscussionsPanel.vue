<template>
  <div class="panel-wrapper">
    <div class="panel-header">
      <div>
        <h1 class="panel-title">Orphaned Discussions</h1>
        <p class="panel-subtitle">{{ workspaceName }}</p>
      </div>
      <div v-if="!forbidden" class="header-tabs">
        <button class="tab-btn" :class="{ active: activeTab === 'threads' }" @click="activeTab = 'threads'">
          Threads
        </button>
        <button class="tab-btn" :class="{ active: activeTab === 'audit' }" @click="switchToAuditTab">
          Audit Log
        </button>
      </div>
    </div>

    <div class="panel-content">
      <div v-if="loading" class="loading-state">Loading orphaned discussions...</div>
      <div v-else-if="forbidden" class="empty-state">
        You need admin access to this workspace to review orphaned discussions.
      </div>

      <div v-else-if="activeTab === 'threads'" class="config-section">
        <h3 class="section-heading">Orphaned discussions</h3>
        <p class="section-description">
          Discussion threads whose anchor block was deleted, or whose original comment was removed
          while replies remain. Restore, archive, or permanently delete them below.
        </p>

        <p v-if="error" class="error-state">{{ error }}</p>

        <div class="filters-row">
          <select v-model="authorFilter">
            <option :value="undefined">All authors</option>
            <option v-for="p in principals" :key="p.id" :value="p.id">{{ p.username }}</option>
          </select>
          <input v-model="startDateFilter" type="date" title="Created after" />
          <input v-model="endDateFilter" type="date" title="Created before" />
          <label class="include-archived-label">
            <input v-model="includeArchived" type="checkbox" />
            Include archived
          </label>
          <button class="apply-btn" @click="loadThreads">Apply filters</button>
        </div>

        <div v-if="threads.length === 0" class="empty-state">No orphaned discussions found.</div>

        <template v-else>
          <div v-if="selectedIds.size > 0" class="bulk-actions-row">
            <span>{{ selectedIds.size }} selected</span>
            <button @click="handleBulkAction('archive')">Archive</button>
            <button @click="openRestoreModal(null)">Restore to block&hellip;</button>
            <button class="danger-btn" @click="handleBulkAction('delete')">Delete permanently</button>
          </div>

          <div class="threads-list">
            <div v-for="thread in threads" :key="thread.thread_id" class="thread-row">
              <input
                type="checkbox"
                :checked="selectedIds.has(thread.thread_id)"
                @change="toggleSelected(thread.thread_id)"
              />
              <div class="thread-details">
                <div class="thread-meta">
                  <span class="reason-badge" :class="thread.reason">{{ reasonLabel(thread.reason) }}</span>
                  <span class="notebook-name">{{ thread.notebook_name }}</span>
                  <span v-if="thread.archived_at" class="archived-badge">Archived</span>
                </div>
                <p class="thread-body">{{ thread.root.body }}</p>
                <div class="thread-footer">
                  <span>by {{ thread.root.author_username || "unknown" }}</span>
                  <span>&middot; {{ thread.reply_count }} repl{{ thread.reply_count === 1 ? "y" : "ies" }}</span>
                  <span>&middot; last activity {{ formatDate(thread.last_activity_at) }}</span>
                </div>
              </div>
              <div class="thread-actions">
                <button @click="openRestoreModal(thread)">Restore</button>
                <button v-if="!thread.archived_at" @click="handleArchive(thread)">Archive</button>
                <button class="danger-btn" @click="handleDelete(thread)">Delete</button>
              </div>
            </div>
          </div>
        </template>
      </div>

      <div v-else class="config-section">
        <h3 class="section-heading">Audit log</h3>
        <p class="section-description">Admin actions taken on orphaned discussions, most recent first.</p>
        <div v-if="auditLog.length === 0" class="empty-state">No audit entries yet.</div>
        <div v-else class="audit-list">
          <div v-for="entry in auditLog" :key="entry.id" class="audit-row">
            <span class="audit-kind">{{ auditKindLabel(entry.kind) }}</span>
            <span class="audit-actor">{{ entry.actor_username || "system" }}</span>
            <span class="audit-time">{{ formatDate(entry.created_at) }}</span>
          </div>
        </div>
      </div>
    </div>

    <Modal
      v-model="showRestoreModal"
      title="Restore discussion"
      confirm-text="Restore"
      @confirm="confirmRestore"
      @cancel="resetRestoreModal"
    >
      <p v-if="restoreRequiresBlockId">
        Enter the block ID this thread (or these threads) should be re-anchored to.
      </p>
      <p v-else>This clears the original comment's deletion, restoring the thread as-is.</p>
      <FormGroup v-if="restoreRequiresBlockId" label="New block ID">
        <input v-model="restoreBlockId" type="text" placeholder="01H..." />
      </FormGroup>
      <p v-if="restoreError" class="invite-error">{{ restoreError }}</p>
    </Modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from "vue"
import { useWorkspaceStore } from "../../stores/workspace"
import {
  orphanedDiscussionsService,
  type OrphanedThread,
  type AuditLogEntry,
  type BulkAction,
} from "../../services/orphanedDiscussions"
import { principalService, type Principal } from "../../services/comments"
import Modal from "../Modal.vue"
import FormGroup from "../FormGroup.vue"

const props = defineProps<{
  workspaceId: number
}>()

const workspaceStore = useWorkspaceStore()

const workspace = computed(() => workspaceStore.workspaces.find((w) => w.id === props.workspaceId))
const workspaceName = computed(() => workspace.value?.name || "Workspace")
const workspaceIdentifier = computed(() => workspace.value?.slug || String(props.workspaceId))

const activeTab = ref<"threads" | "audit">("threads")
const loading = ref(false)
const forbidden = ref(false)
const error = ref<string | null>(null)

const threads = ref<OrphanedThread[]>([])
const auditLog = ref<AuditLogEntry[]>([])
const principals = ref<Principal[]>([])
const selectedIds = ref<Set<number>>(new Set())

const authorFilter = ref<number | undefined>(undefined)
const startDateFilter = ref<string>("")
const endDateFilter = ref<string>("")
const includeArchived = ref(false)

const showRestoreModal = ref(false)
const restoreTarget = ref<OrphanedThread | null>(null)
const restoreBlockId = ref("")
const restoreError = ref<string | null>(null)
const isBulkRestore = ref(false)

const restoreRequiresBlockId = computed(() => {
  if (isBulkRestore.value) return true
  return restoreTarget.value?.reason === "block_deleted"
})

function reasonLabel(reason: string) {
  return reason === "block_deleted" ? "Block deleted" : "Comment deleted"
}

function auditKindLabel(kind: string) {
  return kind.replace("comment.orphan_", "").replace("_", " ")
}

function formatDate(value: string) {
  return new Date(value).toLocaleString()
}

async function loadThreads() {
  if (!workspaceIdentifier.value) return
  loading.value = true
  error.value = null
  forbidden.value = false
  try {
    threads.value = await orphanedDiscussionsService.list(workspaceIdentifier.value, {
      author_id: authorFilter.value,
      start_date: startDateFilter.value || undefined,
      end_date: endDateFilter.value || undefined,
      include_archived: includeArchived.value,
    })
    selectedIds.value = new Set()
  } catch (e: any) {
    if (e.response?.status === 403 || e.response?.status === 404) {
      forbidden.value = true
    } else {
      error.value = e.response?.data?.detail || "Failed to load orphaned discussions"
    }
  } finally {
    loading.value = false
  }
}

async function loadAuditLog() {
  if (!workspaceIdentifier.value) return
  try {
    auditLog.value = await orphanedDiscussionsService.auditLog(workspaceIdentifier.value)
  } catch (e: any) {
    error.value = e.response?.data?.detail || "Failed to load audit log"
  }
}

function switchToAuditTab() {
  activeTab.value = "audit"
  loadAuditLog()
}

async function loadPrincipals() {
  if (!workspaceIdentifier.value) return
  try {
    principals.value = await principalService.list(workspaceIdentifier.value)
  } catch {
    // Non-critical: the author filter just stays empty.
  }
}

function toggleSelected(threadId: number) {
  const next = new Set(selectedIds.value)
  if (next.has(threadId)) {
    next.delete(threadId)
  } else {
    next.add(threadId)
  }
  selectedIds.value = next
}

async function handleArchive(thread: OrphanedThread) {
  error.value = null
  try {
    const updated = await orphanedDiscussionsService.archive(workspaceIdentifier.value, thread.thread_id)
    if (includeArchived.value) {
      const idx = threads.value.findIndex((t) => t.thread_id === thread.thread_id)
      if (idx !== -1) threads.value[idx] = updated
    } else {
      threads.value = threads.value.filter((t) => t.thread_id !== thread.thread_id)
    }
  } catch (e: any) {
    error.value = e.response?.data?.detail || "Failed to archive discussion"
  }
}

async function handleDelete(thread: OrphanedThread) {
  if (!confirm("Permanently delete this discussion thread? This cannot be undone.")) return
  error.value = null
  try {
    await orphanedDiscussionsService.delete(workspaceIdentifier.value, thread.thread_id)
    threads.value = threads.value.filter((t) => t.thread_id !== thread.thread_id)
  } catch (e: any) {
    error.value = e.response?.data?.detail || "Failed to delete discussion"
  }
}

async function handleBulkAction(action: BulkAction) {
  if (action === "delete" && !confirm(`Permanently delete ${selectedIds.value.size} discussion thread(s)?`)) return
  error.value = null
  try {
    await orphanedDiscussionsService.bulkAction(workspaceIdentifier.value, Array.from(selectedIds.value), action)
    await loadThreads()
  } catch (e: any) {
    error.value = e.response?.data?.detail || `Failed to ${action} selected discussions`
  }
}

function openRestoreModal(thread: OrphanedThread | null) {
  restoreTarget.value = thread
  isBulkRestore.value = thread === null
  restoreBlockId.value = ""
  restoreError.value = null
  showRestoreModal.value = true
}

function resetRestoreModal() {
  restoreTarget.value = null
  isBulkRestore.value = false
  restoreBlockId.value = ""
  restoreError.value = null
}

async function confirmRestore() {
  if (restoreRequiresBlockId.value && !restoreBlockId.value.trim()) {
    restoreError.value = "Enter a block ID"
    return
  }
  restoreError.value = null
  try {
    if (isBulkRestore.value) {
      await orphanedDiscussionsService.bulkAction(
        workspaceIdentifier.value,
        Array.from(selectedIds.value),
        "restore",
        restoreBlockId.value.trim(),
      )
      await loadThreads()
    } else if (restoreTarget.value) {
      await orphanedDiscussionsService.restore(
        workspaceIdentifier.value,
        restoreTarget.value.thread_id,
        restoreBlockId.value.trim() || undefined,
      )
      threads.value = threads.value.filter((t) => t.thread_id !== restoreTarget.value!.thread_id)
    }
    showRestoreModal.value = false
    resetRestoreModal()
  } catch (e: any) {
    restoreError.value = e.response?.data?.detail || "Failed to restore discussion"
  }
}

watch(() => props.workspaceId, loadThreads)
onMounted(async () => {
  await loadThreads()
  await loadPrincipals()
})
</script>

<style src="./settings-panel.css"></style>
<style scoped>
.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.header-tabs {
  display: flex;
  gap: 0.5rem;
}

.tab-btn {
  padding: 0.5rem 1rem;
  border: 1px solid var(--color-border-medium);
  border-radius: 6px;
  background: var(--color-bg-primary);
  color: var(--color-text-secondary);
  cursor: pointer;
  font-size: 0.875rem;
}

.tab-btn.active {
  background: var(--notebook-accent);
  color: white;
  border-color: var(--notebook-accent);
}

.filters-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 1.5rem;
}

.filters-row select,
.filters-row input[type="date"] {
  padding: 0.375rem 0.625rem;
  border: 1px solid var(--color-border-medium);
  border-radius: 6px;
  background: var(--color-bg-primary);
  color: var(--color-text-primary);
  font-size: 0.875rem;
}

.include-archived-label {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  font-size: 0.875rem;
  color: var(--color-text-secondary);
}

.apply-btn {
  padding: 0.375rem 0.875rem;
  border: 1px solid var(--notebook-accent);
  border-radius: 6px;
  background: none;
  color: var(--notebook-accent);
  cursor: pointer;
  font-size: 0.875rem;
}

.bulk-actions-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 1rem;
  margin-bottom: 1rem;
  background: var(--color-bg-tertiary);
  border-radius: 6px;
  font-size: 0.875rem;
}

.bulk-actions-row button {
  padding: 0.375rem 0.75rem;
  border: 1px solid var(--color-border-medium);
  border-radius: 6px;
  background: var(--color-bg-primary);
  cursor: pointer;
  font-size: 0.8125rem;
}

.threads-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.thread-row {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  padding: 1rem 1.25rem;
  background: var(--color-bg-primary);
  border: 1px solid var(--color-border-light);
  border-radius: 6px;
}

.thread-details {
  flex: 1;
  min-width: 0;
}

.thread-meta {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.375rem;
}

.reason-badge {
  font-size: 0.75rem;
  font-weight: 600;
  padding: 0.125rem 0.5rem;
  border-radius: 10px;
  background: var(--color-bg-tertiary);
  color: var(--color-text-secondary);
}

.reason-badge.block_deleted {
  background: #fef2f2;
  color: #991b1b;
}

.reason-badge.root_deleted {
  background: #fff7ed;
  color: #9a3412;
}

.notebook-name {
  font-size: 0.8125rem;
  color: var(--color-text-tertiary);
}

.archived-badge {
  font-size: 0.75rem;
  padding: 0.125rem 0.5rem;
  border-radius: 10px;
  background: var(--color-bg-tertiary);
  color: var(--color-text-tertiary);
}

.thread-body {
  margin: 0 0 0.375rem;
  color: var(--color-text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.thread-footer {
  display: flex;
  gap: 0.375rem;
  font-size: 0.8125rem;
  color: var(--color-text-tertiary);
}

.thread-actions {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

.thread-actions button {
  padding: 0.25rem 0.625rem;
  border: 1px solid var(--color-border-medium);
  border-radius: 6px;
  background: none;
  cursor: pointer;
  font-size: 0.8125rem;
  white-space: nowrap;
}

.danger-btn {
  color: #991b1b;
}

.danger-btn:hover {
  background: #fef2f2;
}

.audit-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.audit-row {
  display: flex;
  gap: 1rem;
  padding: 0.625rem 1rem;
  background: var(--color-bg-primary);
  border: 1px solid var(--color-border-light);
  border-radius: 6px;
  font-size: 0.875rem;
}

.audit-kind {
  font-weight: 600;
  text-transform: capitalize;
  color: var(--color-text-primary);
}

.audit-actor {
  color: var(--color-text-secondary);
}

.audit-time {
  margin-left: auto;
  color: var(--color-text-tertiary);
}

.invite-error {
  margin-top: 0.5rem;
  color: #991b1b;
  font-size: 0.875rem;
}
</style>
