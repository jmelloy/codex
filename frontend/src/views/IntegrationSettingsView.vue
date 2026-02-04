<template>
  <div class="integration-settings">
    <div class="settings-header">
      <h2>Integration Plugins</h2>
      <p>Connect Codex to external services and APIs</p>
    </div>

    <div v-if="loading" class="loading-state">
      <p>Loading integrations...</p>
    </div>

    <div v-else-if="error" class="error-state">
      <p>{{ error }}</p>
      <button @click="loadIntegrations">Retry</button>
    </div>

    <div v-else class="integrations-list">
      <div v-if="integrations.length === 0" class="empty-state">
        <p>No integration plugins available.</p>
      </div>

      <div
        v-for="integration in integrations"
        :key="integration.id"
        class="integration-card"
      >
        <div class="integration-header">
          <h3 @click="selectIntegration(integration.id)">{{ integration.name }}</h3>
          <span class="version">v{{ integration.version }}</span>
        </div>
        
        <p class="description" @click="selectIntegration(integration.id)">{{ integration.description }}</p>
        
        <div class="integration-meta" @click="selectIntegration(integration.id)">
          <span class="meta-item">
            <strong>Type:</strong> {{ integration.api_type }}
          </span>
          <span v-if="integration.auth_method" class="meta-item">
            <strong>Auth:</strong> {{ integration.auth_method }}
          </span>
          <span class="meta-item">
            <strong>Author:</strong> {{ integration.author }}
          </span>
        </div>

        <div class="integration-footer">
          <span :class="['status-badge', integration.enabled ? 'enabled' : 'disabled']">
            {{ integration.enabled ? 'Enabled' : 'Disabled' }}
          </span>
          <label class="toggle-switch">
            <input
              type="checkbox"
              :checked="integration.enabled"
              @change="toggleEnabled(integration.id, $event)"
              :disabled="!hasWorkspace || toggling === integration.id"
            />
            <span class="slider"></span>
          </label>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useIntegrationStore } from '../stores/integration'
import { useWorkspaceStore } from '../stores/workspace'

const router = useRouter()
const integrationStore = useIntegrationStore()
const workspaceStore = useWorkspaceStore()

const integrations = computed(() => integrationStore.availableIntegrations)
const loading = computed(() => !integrationStore.integrationsLoaded)
const error = computed(() => integrationStore.integrationsLoadError ? 'Failed to load integrations' : null)
const hasWorkspace = computed(() => workspaceStore.currentWorkspace !== null)
const toggling = ref<string | null>(null)

async function loadIntegrations() {
  const workspaceId = workspaceStore.currentWorkspace?.id
  if (!workspaceId) {
    console.error('No workspace selected')
    return
  }

  // Get notebook ID - use current notebook or first available notebook
  let notebookId: number | undefined
  
  if (workspaceStore.currentNotebook) {
    notebookId = workspaceStore.currentNotebook.id
  } else if (workspaceStore.notebooks.length > 0) {
    // Use first notebook if none is currently selected
    notebookId = workspaceStore.notebooks[0].id
  }
  
  if (!notebookId) {
    console.warn('No notebook available - integration settings require a notebook context')
    return
  }

  await integrationStore.loadIntegrations(workspaceId, notebookId)
}

function selectIntegration(integrationId: string) {
  router.push({ name: 'integration-config', params: { integrationId } })
}

async function toggleEnabled(integrationId: string, event: Event) {
  const target = event.target as HTMLInputElement
  const enabled = target.checked
  
  if (!workspaceStore.currentWorkspace) {
    console.error('No workspace selected')
    return
  }
  
  // Get notebook ID - use current notebook or first available notebook
  let notebookId: number | undefined
  
  if (workspaceStore.currentNotebook) {
    notebookId = workspaceStore.currentNotebook.id
  } else if (workspaceStore.notebooks.length > 0) {
    notebookId = workspaceStore.notebooks[0].id
  }
  
  if (!notebookId) {
    console.error('No notebook available')
    target.checked = !enabled
    return
  }
  
  toggling.value = integrationId
  
  try {
    await integrationStore.toggleIntegrationEnabled(
      integrationId,
      workspaceStore.currentWorkspace.id,
      notebookId,
      enabled
    )
  } catch (error) {
    console.error('Failed to toggle integration:', error)
    // Revert the checkbox state
    target.checked = !enabled
  } finally {
    toggling.value = null
  }
}

onMounted(() => {
  // Trigger load if not already loaded
  if (!integrationStore.integrationsLoaded) {
    loadIntegrations()
  }
})
</script>

<style scoped>
.integration-settings {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
}

.settings-header {
  margin-bottom: 2rem;
}

.settings-header h2 {
  font-size: 2rem;
  font-weight: 600;
  margin-bottom: 0.5rem;
}

.settings-header p {
  color: #666;
  font-size: 1rem;
}

.loading-state,
.error-state,
.empty-state {
  text-align: center;
  padding: 3rem;
  color: #666;
}

.error-state button {
  margin-top: 1rem;
  padding: 0.5rem 1rem;
  background: #007bff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.error-state button:hover {
  background: #0056b3;
}

.integrations-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: 1.5rem;
}

.integration-card {
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 1.5rem;
  transition: all 0.2s ease;
  background: white;
}

.integration-card:hover {
  border-color: #007bff;
  box-shadow: 0 4px 12px rgba(0, 123, 255, 0.1);
}

.integration-header {
  display: flex;
  justify-content: space-between;
  align-items: start;
  margin-bottom: 0.75rem;
}

.integration-header h3 {
  font-size: 1.25rem;
  font-weight: 600;
  margin: 0;
  color: #333;
  cursor: pointer;
}

.integration-header h3:hover {
  color: #007bff;
}

.version {
  font-size: 0.875rem;
  color: #666;
  background: #f0f0f0;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
}

.description {
  color: #555;
  line-height: 1.5;
  margin-bottom: 1rem;
  min-height: 3rem;
  cursor: pointer;
}

.integration-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  margin-bottom: 1rem;
  font-size: 0.875rem;
  cursor: pointer;
}

.meta-item {
  color: #666;
}

.meta-item strong {
  color: #333;
}

.integration-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 1rem;
}

.status-badge {
  padding: 0.25rem 0.75rem;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
}

.status-badge.enabled {
  background: #d4edda;
  color: #155724;
}

.status-badge.disabled {
  background: #f8d7da;
  color: #721c24;
}

/* Toggle switch styles */
.toggle-switch {
  position: relative;
  display: inline-block;
  width: 48px;
  height: 24px;
  cursor: pointer;
}

.toggle-switch input {
  opacity: 0;
  width: 0;
  height: 0;
}

.slider {
  position: absolute;
  cursor: pointer;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: #ccc;
  transition: 0.3s;
  border-radius: 24px;
}

.slider:before {
  position: absolute;
  content: "";
  height: 18px;
  width: 18px;
  left: 3px;
  bottom: 3px;
  background-color: white;
  transition: 0.3s;
  border-radius: 50%;
}

.toggle-switch input:checked + .slider {
  background-color: #28a745;
}

.toggle-switch input:checked + .slider:before {
  transform: translateX(24px);
}

.toggle-switch input:disabled + .slider {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
