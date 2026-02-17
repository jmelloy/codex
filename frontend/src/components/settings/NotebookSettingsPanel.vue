<template>
  <div class="panel-wrapper">
    <div class="panel-header">
      <h1 class="panel-title">Notebook Configuration</h1>
      <p class="panel-subtitle">{{ notebookName }}</p>
    </div>

    <div class="panel-content">
      <section class="config-section">
        <h3 class="section-heading">Plugin Overrides</h3>
        <p class="section-description">
          Override workspace plugin settings specifically for this notebook
        </p>

        <div v-if="pluginsLoading" class="loading-state">Loading...</div>
        <div v-else-if="pluginsLoadError" class="error-state">
          Failed to load plugins. Check that the backend is running and plugins are configured.
        </div>
        <div v-else-if="pluginsList.length === 0" class="empty-state">No plugins configured</div>
        <div v-else class="plugins-list">
          <div v-for="plugin in pluginsList" :key="plugin.id" class="plugin-row">
            <div class="plugin-details">
              <div class="plugin-name-row">
                <span class="plugin-name">{{ plugin.name }}</span>
                <span class="plugin-version-badge">v{{ plugin.version }}</span>
                <span class="plugin-type-badge">{{ plugin.type }}</span>
                <span v-if="hasOverride(plugin.id)" class="override-badge">Override Active</span>
              </div>
              <p class="plugin-description">{{ plugin.manifest?.description || 'No description' }}</p>
              <div class="workspace-setting-info">
                Workspace default: {{ getWorkspaceDefault(plugin.id) ? 'Enabled' : 'Disabled' }}
              </div>
            </div>
            <div class="plugin-controls">
              <label class="toggle-switch-label">
                <input
                  type="checkbox"
                  :checked="getNotebookPluginState(plugin.id)"
                  @change="handleToggle(plugin.id, $event)"
                  class="toggle-checkbox"
                />
                <span class="toggle-slider"></span>
              </label>
              <span class="plugin-status-text">
                {{ getNotebookPluginState(plugin.id) ? 'Enabled' : 'Disabled' }}
              </span>
              <button 
                v-if="hasOverride(plugin.id)"
                @click="removeOverride(plugin.id)"
                class="clear-override-btn">
                Clear Override
              </button>
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
import type { PluginData, PluginConfiguration } from '../../services/plugins'

const props = defineProps<{
  workspaceId: number
  notebookId: number
}>()

const workspaceStore = useWorkspaceStore()
const pluginsList = ref<PluginData[]>([])
const workspaceConfigs = ref<PluginConfiguration[]>([])
const notebookConfigs = ref<PluginConfiguration[]>([])
const pluginsLoading = ref(false)
const pluginsLoadError = ref(false)
const operationMessage = ref('')

const FALLBACK_ENABLED_STATE = true

const notebookName = computed(() => {
  const nb = workspaceStore.notebooks.find(n => n.id === props.notebookId)
  return nb?.name || 'Notebook'
})

async function loadAllData() {
  pluginsLoading.value = true
  pluginsLoadError.value = false
  try {
    const [allPluginsResponse, wsConfigsResponse, nbConfigsResponse] = await Promise.all([
      api.get<PluginData[]>('/api/v1/plugins'),
      api.get<PluginConfiguration[]>(`/api/v1/workspaces/${props.workspaceId}/plugins`),
      api.get<PluginConfiguration[]>(`/api/v1/notebooks/${props.notebookId}/plugins`)
    ])

    pluginsList.value = allPluginsResponse.data ?? []
    workspaceConfigs.value = wsConfigsResponse.data ?? []
    notebookConfigs.value = nbConfigsResponse.data ?? []
  } catch (err) {
    console.error('Data loading error:', err)
    pluginsLoadError.value = true
    pluginsList.value = []
    workspaceConfigs.value = []
    notebookConfigs.value = []
  } finally {
    pluginsLoading.value = false
  }
}

function getWorkspaceDefault(pluginId: string): boolean {
  const config = workspaceConfigs.value.find(c => c.plugin_id === pluginId)
  return config ? config.enabled : FALLBACK_ENABLED_STATE
}

function hasOverride(pluginId: string): boolean {
  return notebookConfigs.value.some(c => c.plugin_id === pluginId)
}

function getNotebookPluginState(pluginId: string): boolean {
  const nbConfig = notebookConfigs.value.find(c => c.plugin_id === pluginId)
  if (nbConfig) {
    return nbConfig.enabled
  }
  return getWorkspaceDefault(pluginId)
}

async function handleToggle(pluginId: string, event: Event) {
  const checkbox = event.target as HTMLInputElement
  const newState = checkbox.checked
  
  try {
    await api.put(
      `/api/v1/notebooks/${props.notebookId}/plugins/${pluginId}`,
      { enabled: newState }
    )
    
    const existingConfig = notebookConfigs.value.find(c => c.plugin_id === pluginId)
    if (existingConfig) {
      existingConfig.enabled = newState
    } else {
      notebookConfigs.value.push({
        plugin_id: pluginId,
        enabled: newState,
        config: {}
      })
    }
    
    operationMessage.value = `Plugin ${newState ? 'enabled' : 'disabled'} for notebook`
    setTimeout(() => {
      operationMessage.value = ''
    }, 2500)
  } catch (err) {
    console.error('Toggle error:', err)
    checkbox.checked = !newState
  }
}

async function removeOverride(pluginId: string) {
  try {
    await api.delete(`/api/v1/notebooks/${props.notebookId}/plugins/${pluginId}`)
    
    notebookConfigs.value = notebookConfigs.value.filter(c => c.plugin_id !== pluginId)
    
    operationMessage.value = 'Override removed, using workspace default'
    setTimeout(() => {
      operationMessage.value = ''
    }, 2500)
  } catch (err) {
    console.error('Override removal error:', err)
  }
}

onMounted(() => {
  loadAllData()
})
</script>

<style src="./settings-panel.css"></style>
<style scoped>
/* Notebook-specific styles */
.override-badge {
  font-size: 0.75rem;
  padding: 0.1875rem 0.5rem;
  border-radius: 10px;
  background: #fef3c7;
  color: #92400e;
  font-weight: 600;
}

.plugin-description {
  margin-bottom: 0.5rem;
}

.workspace-setting-info {
  font-size: 0.8125rem;
  color: var(--color-text-tertiary);
  font-style: italic;
}

.clear-override-btn {
  font-size: 0.8125rem;
  padding: 0.25rem 0.625rem;
  background: none;
  border: 1px solid var(--color-border-medium);
  border-radius: 4px;
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: all 0.2s;
}

.clear-override-btn:hover {
  background: var(--color-bg-tertiary);
  border-color: var(--color-border-dark);
  color: var(--color-text-primary);
}
</style>
