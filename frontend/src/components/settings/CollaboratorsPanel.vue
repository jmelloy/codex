<template>
  <div class="panel-wrapper">
    <div class="panel-header">
      <div>
        <h1 class="panel-title">Sharing</h1>
        <p class="panel-subtitle">{{ workspaceName }}</p>
      </div>
      <button v-if="!forbidden" @click="openInviteModal" class="create-btn">+ Invite</button>
    </div>

    <div class="panel-content">
      <div v-if="loading" class="loading-state">Loading collaborators...</div>
      <div v-else-if="forbidden" class="empty-state">
        You need admin access to this workspace to manage collaborators.
      </div>
      <div v-else class="config-section">
        <h3 class="section-heading">Collaborators</h3>
        <p class="section-description">People with access to this workspace.</p>

        <p v-if="error" class="error-state">{{ error }}</p>

        <div class="collaborators-list">
          <div v-for="collaborator in collaborators" :key="collaborator.user_id" class="collaborator-row">
            <div class="collaborator-details">
              <span class="collaborator-name">{{ collaborator.username }}</span>
              <span class="collaborator-email">{{ collaborator.email }}</span>
            </div>
            <div class="collaborator-controls">
              <span v-if="collaborator.is_owner" class="owner-badge">Owner</span>
              <template v-else>
                <select
                  class="level-select"
                  :value="collaborator.permission_level"
                  @change="handleLevelChange(collaborator, ($event.target as HTMLSelectElement).value)"
                >
                  <option v-for="level in PERMISSION_LEVELS" :key="level" :value="level">
                    {{ level }}
                  </option>
                </select>
                <button class="remove-btn" @click="handleRemove(collaborator)">Remove</button>
              </template>
            </div>
          </div>
        </div>
      </div>
    </div>

    <Modal
      v-model="showInviteModal"
      title="Invite collaborator"
      confirm-text="Invite"
      @confirm="handleInvite"
      @cancel="resetInviteForm"
    >
      <FormGroup label="Username or email">
        <input v-model="inviteValue" type="text" placeholder="jane or jane@example.com" />
      </FormGroup>
      <FormGroup label="Permission level">
        <select v-model="inviteLevel">
          <option v-for="level in PERMISSION_LEVELS" :key="level" :value="level">{{ level }}</option>
        </select>
      </FormGroup>
      <p v-if="inviteError" class="invite-error">{{ inviteError }}</p>
    </Modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from "vue"
import { useWorkspaceStore } from "../../stores/workspace"
import { collaboratorService, type Collaborator, type PermissionLevel } from "../../services/collaborators"
import Modal from "../Modal.vue"
import FormGroup from "../FormGroup.vue"

const PERMISSION_LEVELS: PermissionLevel[] = ["read", "comment", "write", "admin"]

const props = defineProps<{
  workspaceId: number
}>()

const workspaceStore = useWorkspaceStore()

const workspace = computed(() => workspaceStore.workspaces.find((w) => w.id === props.workspaceId))
const workspaceName = computed(() => workspace.value?.name || "Workspace")
const workspaceIdentifier = computed(() => workspace.value?.slug || String(props.workspaceId))

const collaborators = ref<Collaborator[]>([])
const loading = ref(false)
const forbidden = ref(false)
const error = ref<string | null>(null)

const showInviteModal = ref(false)
const inviteValue = ref("")
const inviteLevel = ref<PermissionLevel>("read")
const inviteError = ref<string | null>(null)

async function loadCollaborators() {
  if (!workspaceIdentifier.value) return
  loading.value = true
  error.value = null
  forbidden.value = false
  try {
    collaborators.value = await collaboratorService.list(workspaceIdentifier.value)
  } catch (e: any) {
    if (e.response?.status === 403 || e.response?.status === 404) {
      forbidden.value = true
    } else {
      error.value = e.response?.data?.detail || "Failed to load collaborators"
    }
  } finally {
    loading.value = false
  }
}

async function handleLevelChange(collaborator: Collaborator, level: string) {
  error.value = null
  try {
    const updated = await collaboratorService.updateLevel(
      workspaceIdentifier.value,
      collaborator.user_id,
      level as PermissionLevel,
    )
    const idx = collaborators.value.findIndex((c) => c.user_id === collaborator.user_id)
    if (idx !== -1) collaborators.value[idx] = updated
  } catch (e: any) {
    error.value = e.response?.data?.detail || "Failed to update permission level"
  }
}

async function handleRemove(collaborator: Collaborator) {
  error.value = null
  try {
    await collaboratorService.revoke(workspaceIdentifier.value, collaborator.user_id)
    collaborators.value = collaborators.value.filter((c) => c.user_id !== collaborator.user_id)
  } catch (e: any) {
    error.value = e.response?.data?.detail || "Failed to remove collaborator"
  }
}

function openInviteModal() {
  resetInviteForm()
  showInviteModal.value = true
}

function resetInviteForm() {
  inviteValue.value = ""
  inviteLevel.value = "read"
  inviteError.value = null
}

async function handleInvite() {
  if (!inviteValue.value.trim()) {
    inviteError.value = "Enter a username or email"
    return
  }
  inviteError.value = null
  try {
    const created = await collaboratorService.invite(
      workspaceIdentifier.value,
      inviteValue.value.trim(),
      inviteLevel.value,
    )
    collaborators.value.push(created)
    showInviteModal.value = false
    resetInviteForm()
  } catch (e: any) {
    inviteError.value = e.response?.data?.detail || "Failed to invite collaborator"
  }
}

watch(() => props.workspaceId, loadCollaborators)
onMounted(loadCollaborators)
</script>

<style src="./settings-panel.css"></style>
<style scoped>
.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.create-btn {
  padding: 0.5rem 1.25rem;
  background: var(--notebook-accent);
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s;
  white-space: nowrap;
}

.create-btn:hover {
  background: color-mix(in srgb, var(--notebook-accent) 85%, black);
}

.collaborators-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.collaborator-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.25rem;
  background: var(--color-bg-primary);
  border: 1px solid var(--color-border-light);
  border-radius: 6px;
}

.collaborator-details {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
}

.collaborator-name {
  font-weight: 600;
  color: var(--color-text-primary);
}

.collaborator-email {
  font-size: 0.875rem;
  color: var(--color-text-secondary);
}

.collaborator-controls {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.owner-badge {
  font-size: 0.75rem;
  font-weight: 600;
  padding: 0.25rem 0.625rem;
  border-radius: 10px;
  background: var(--color-bg-tertiary);
  color: var(--color-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.level-select {
  padding: 0.375rem 0.625rem;
  border: 1px solid var(--color-border-medium);
  border-radius: 6px;
  background: var(--color-bg-primary);
  color: var(--color-text-primary);
  font-size: 0.875rem;
}

.remove-btn {
  padding: 0.375rem 0.75rem;
  border: 1px solid var(--color-border-medium);
  border-radius: 6px;
  background: none;
  color: #991b1b;
  font-size: 0.875rem;
  cursor: pointer;
  transition: background 0.2s;
}

.remove-btn:hover {
  background: #fef2f2;
}

.invite-error {
  margin-top: 0.5rem;
  color: #991b1b;
  font-size: 0.875rem;
}
</style>
