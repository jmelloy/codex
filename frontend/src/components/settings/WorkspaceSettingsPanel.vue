<template>
  <div class="panel-wrapper">
    <div class="panel-header">
      <h1 class="panel-title">Workspace Configuration</h1>
      <p class="panel-subtitle">{{ workspaceName }}</p>
    </div>

    <div class="panel-content">
      <section class="config-section">
        <h3 class="section-heading">Plugin Management</h3>
        <p class="section-description">
          Enable or disable plugins for this workspace
        </p>

        <div v-if="pluginsLoading" class="loading-state">Loading plugins...</div>
        <div v-else-if="pluginsList.length === 0" class="empty-state">No plugins available</div>
        <div v-else class="plugins-list">
          <div v-for="plugin in pluginsList" :key="plugin.id" class="plugin-row">
            <div class="plugin-details">
              <div class="plugin-name-row">
                <span class="plugin-name">{{ plugin.name }}</span>
                <span class="plugin-version-badge">v{{ plugin.version }}</span>
                <span class="plugin-type-badge">{{ plugin.type }}</span>
              </div>
              <p class="plugin-description">{{ plugin.manifest?.description || 'No description' }}</p>
            </div>
            <div class="plugin-controls">
              <label class="toggle-switch-label">
                <input
                  type="checkbox"
                  :checked="getPluginState(plugin.id)"
                  @change="handlePluginToggle(plugin.id, $event)"
                  class="toggle-checkbox"
                />
                <span class="toggle-slider"></span>
              </label>
              <span class="plugin-status-text">
                {{ getPluginState(plugin.id) ? 'Enabled' : 'Disabled' }}
              </span>
            </div>
          </div>
        </div>

        <div v-if="operationMessage" class="operation-notification">
          {{ operationMessage }}
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useWorkspaceStore } from '../../stores/workspace'
import api from '../../services/api'

interface PluginData {
  id: string
  name: string
  version: string
  type: string
  enabled: boolean
  manifest: any
}

interface PluginConfiguration {
  plugin_id: string
  enabled: boolean
  config: any
}

const props = defineProps<{
  workspaceId: number
}>()

const workspaceStore = useWorkspaceStore()
const pluginsList = ref<PluginData[]>([])
const pluginConfigurations = ref<PluginConfiguration[]>([])
const pluginsLoading = ref(false)
const operationMessage = ref('')

const FALLBACK_ENABLED_STATE = true

const workspaceName = computed(() => {
  const ws = workspaceStore.workspaces.find(w => w.id === props.workspaceId)
  return ws?.name || 'Workspace'
})

async function loadPluginData() {
  pluginsLoading.value = true
  try {
    const [allPluginsResponse, configsResponse] = await Promise.all([
      api.get<PluginData[]>('/api/v1/plugins'),
      api.get<PluginConfiguration[]>(`/api/v1/workspaces/${props.workspaceId}/plugins`)
    ])
    
    pluginsList.value = allPluginsResponse.data
    pluginConfigurations.value = configsResponse.data
  } catch (err) {
    console.error('Plugin loading error:', err)
  } finally {
    pluginsLoading.value = false
  }
}

function getPluginState(pluginId: string): boolean {
  const config = pluginConfigurations.value.find(c => c.plugin_id === pluginId)
  return config ? config.enabled : FALLBACK_ENABLED_STATE
}

async function handlePluginToggle(pluginId: string, event: Event) {
  const checkbox = event.target as HTMLInputElement
  const newState = checkbox.checked
  
  try {
    await api.put(
      `/api/v1/workspaces/${props.workspaceId}/plugins/${pluginId}`,
      { enabled: newState }
    )
    
    const existingConfig = pluginConfigurations.value.find(c => c.plugin_id === pluginId)
    if (existingConfig) {
      existingConfig.enabled = newState
    } else {
      pluginConfigurations.value.push({
        plugin_id: pluginId,
        enabled: newState,
        config: {}
      })
    }
    
    operationMessage.value = `Plugin ${newState ? 'enabled' : 'disabled'}`
    setTimeout(() => {
      operationMessage.value = ''
    }, 2500)
  } catch (err) {
    console.error('Plugin toggle error:', err)
    checkbox.checked = !newState
  }
}

onMounted(() => {
  loadPluginData()
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
}

.config-section {
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border-medium);
  border-radius: 8px;
  padding: 2rem;
}

.section-heading {
  margin: 0 0 0.75rem;
  font-size: 1.375rem;
  font-weight: 600;
  color: var(--color-text-primary);
}

.section-description {
  margin: 0 0 1.75rem;
  color: var(--color-text-secondary);
  line-height: 1.5;
}

.loading-state,
.empty-state {
  padding: 2rem;
  text-align: center;
  color: var(--color-text-tertiary);
  font-style: italic;
}

.plugins-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.plugin-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 1.25rem;
  background: var(--color-bg-primary);
  border: 1px solid var(--color-border-light);
  border-radius: 6px;
  transition: border-color 0.2s;
}

.plugin-row:hover {
  border-color: var(--color-border-medium);
}

.plugin-details {
  flex: 1;
}

.plugin-name-row {
  display: flex;
  align-items: center;
  gap: 0.625rem;
  margin-bottom: 0.5rem;
}

.plugin-name {
  font-weight: 600;
  font-size: 1.0625rem;
  color: var(--color-text-primary);
}

.plugin-version-badge,
.plugin-type-badge {
  font-size: 0.75rem;
  padding: 0.1875rem 0.5rem;
  border-radius: 10px;
  background: var(--color-bg-tertiary);
  color: var(--color-text-secondary);
}

.plugin-description {
  margin: 0;
  font-size: 0.9375rem;
  color: var(--color-text-secondary);
  line-height: 1.4;
}

.plugin-controls {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 0.5rem;
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

.plugin-status-text {
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--color-text-secondary);
}

.operation-notification {
  margin-top: 1.25rem;
  padding: 0.875rem 1.125rem;
  background: #d4edda;
  border: 1px solid #c3e6cb;
  border-radius: 6px;
  color: #155724;
  font-weight: 500;
}
</style>
