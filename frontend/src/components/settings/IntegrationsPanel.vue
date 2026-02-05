<template>
  <div class="panel-wrapper">
    <div class="panel-header">
      <h1 class="panel-title">Integration Plugins</h1>
      <p class="panel-subtitle">Connect to external services</p>
    </div>

    <div class="panel-content">
      <div v-if="integrationsLoading" class="loading-state">Loading integrations...</div>
      <div v-else-if="integrationsList.length === 0" class="empty-state">
        No integration plugins available
      </div>
      <div v-else class="integrations-grid">
        <div 
          v-for="integration in integrationsList" 
          :key="integration.id"
          @click="openIntegrationConfig(integration.id)"
          class="integration-card">
          <div class="integration-header-row">
            <h3 class="integration-title">{{ integration.name }}</h3>
            <span class="integration-version">v{{ integration.version }}</span>
          </div>
          <p class="integration-description">{{ integration.description }}</p>
          <div class="integration-meta-row">
            <span class="meta-chip">{{ integration.api_type }}</span>
            <span v-if="integration.auth_method" class="meta-chip">{{ integration.auth_method }}</span>
            <span class="meta-chip">{{ integration.author }}</span>
          </div>
          <div class="integration-status-row">
            <span :class="['status-indicator', integration.enabled ? 'status-on' : 'status-off']">
              {{ integration.enabled ? 'Enabled' : 'Disabled' }}
            </span>
            <label class="toggle-switch-label" @click.stop>
              <input
                type="checkbox"
                :checked="integration.enabled"
                @change="toggleIntegration(integration.id, $event)"
                class="toggle-checkbox"
              />
              <span class="toggle-slider"></span>
            </label>
          </div>
        </div>
      </div>

      <!-- Integration Config Modal (simplified inline) -->
      <div v-if="selectedIntegrationId" class="config-overlay" @click="closeIntegrationConfig">
        <div class="config-panel" @click.stop>
          <div class="config-panel-header">
            <h2>Configure Integration</h2>
            <button @click="closeIntegrationConfig" class="config-close-btn">&times;</button>
          </div>
          <div class="config-panel-content">
            <p>Integration configuration interface would go here for: {{ selectedIntegrationId }}</p>
            <p class="info-note">This would show the full IntegrationConfigView content</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useIntegrationStore } from '../../stores/integration'
import { useWorkspaceStore } from '../../stores/workspace'

const integrationStore = useIntegrationStore()
const workspaceStore = useWorkspaceStore()

const selectedIntegrationId = ref<string | null>(null)

const integrationsList = computed(() => integrationStore.availableIntegrations)
const integrationsLoading = computed(() => !integrationStore.integrationsLoaded)

function openIntegrationConfig(integrationId: string) {
  selectedIntegrationId.value = integrationId
}

function closeIntegrationConfig() {
  selectedIntegrationId.value = null
}

async function toggleIntegration(integrationId: string, event: Event) {
  const checkbox = event.target as HTMLInputElement
  const newState = checkbox.checked
  
  const workspaceId = workspaceStore.currentWorkspace?.id
  const notebookId = workspaceStore.currentNotebook?.id || workspaceStore.notebooks[0]?.id
  
  if (!workspaceId || !notebookId) {
    checkbox.checked = !newState
    return
  }
  
  try {
    await integrationStore.toggleIntegrationEnabled(
      integrationId,
      workspaceId,
      notebookId,
      newState
    )
  } catch (err) {
    console.error('Integration toggle error:', err)
    checkbox.checked = !newState
  }
}

onMounted(async () => {
  if (!integrationStore.integrationsLoaded) {
    const workspaceId = workspaceStore.currentWorkspace?.id
    const notebookId = workspaceStore.currentNotebook?.id || workspaceStore.notebooks[0]?.id
    
    if (workspaceId && notebookId) {
      await integrationStore.loadIntegrations(workspaceId, notebookId)
    }
  }
})
</script>

<style scoped>
.panel-wrapper {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.panel-header {
  padding: 2rem 2.5rem;
  border-bottom: 1px solid var(--color-border-light);
}

.panel-title {
  margin: 0 0 0.5rem;
  font-size: 2rem;
  font-weight: 700;
  color: var(--color-text-primary);
}

.panel-subtitle {
  margin: 0;
  color: var(--color-text-secondary);
  font-size: 1rem;
}

.panel-content {
  flex: 1;
  overflow-y: auto;
  padding: 2rem 2.5rem;
  position: relative;
}

.loading-state,
.empty-state {
  padding: 3rem;
  text-align: center;
  color: var(--color-text-tertiary);
  font-style: italic;
}

.integrations-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 1.5rem;
}

.integration-card {
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border-medium);
  border-radius: 8px;
  padding: 1.5rem;
  cursor: pointer;
  transition: all 0.2s;
}

.integration-card:hover {
  border-color: var(--notebook-accent);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

.integration-header-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 0.75rem;
}

.integration-title {
  margin: 0;
  font-size: 1.1875rem;
  font-weight: 600;
  color: var(--color-text-primary);
}

.integration-version {
  font-size: 0.8125rem;
  padding: 0.25rem 0.625rem;
  background: var(--color-bg-tertiary);
  color: var(--color-text-secondary);
  border-radius: 10px;
}

.integration-description {
  margin: 0 0 1rem;
  color: var(--color-text-secondary);
  line-height: 1.5;
  font-size: 0.9375rem;
  min-height: 2.8rem;
}

.integration-meta-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.meta-chip {
  font-size: 0.75rem;
  padding: 0.25rem 0.5rem;
  background: var(--color-bg-primary);
  border: 1px solid var(--color-border-light);
  border-radius: 4px;
  color: var(--color-text-tertiary);
}

.integration-status-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 1rem;
  border-top: 1px solid var(--color-border-light);
}

.status-indicator {
  font-size: 0.75rem;
  font-weight: 600;
  padding: 0.25rem 0.75rem;
  border-radius: 12px;
  text-transform: uppercase;
}

.status-on {
  background: #d4edda;
  color: #155724;
}

.status-off {
  background: #f8d7da;
  color: #721c24;
}

.toggle-switch-label {
  position: relative;
  display: inline-block;
  width: 50px;
  height: 26px;
  cursor: pointer;
}

.toggle-checkbox {
  opacity: 0;
  width: 0;
  height: 0;
}

.toggle-slider {
  position: absolute;
  inset: 0;
  background-color: #ccc;
  border-radius: 26px;
  transition: 0.25s;
}

.toggle-slider::before {
  content: "";
  position: absolute;
  height: 20px;
  width: 20px;
  left: 3px;
  bottom: 3px;
  background-color: white;
  border-radius: 50%;
  transition: 0.25s;
}

.toggle-checkbox:checked + .toggle-slider {
  background-color: var(--notebook-accent);
}

.toggle-checkbox:checked + .toggle-slider::before {
  transform: translateX(24px);
}

.config-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10000;
}

.config-panel {
  background: var(--color-bg-primary);
  border-radius: 8px;
  max-width: 600px;
  width: 90%;
  max-height: 80vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.config-panel-header {
  padding: 1.5rem;
  border-bottom: 1px solid var(--color-border-medium);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.config-panel-header h2 {
  margin: 0;
  font-size: 1.25rem;
  color: var(--color-text-primary);
}

.config-close-btn {
  background: none;
  border: none;
  font-size: 2rem;
  cursor: pointer;
  color: var(--color-text-secondary);
  padding: 0;
  width: 32px;
  height: 32px;
}

.config-panel-content {
  padding: 2rem;
  overflow-y: auto;
}

.info-note {
  color: var(--color-text-tertiary);
  font-style: italic;
  font-size: 0.9375rem;
}
</style>
