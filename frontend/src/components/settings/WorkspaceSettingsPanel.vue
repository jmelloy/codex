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
        <div v-else-if="pluginsLoadError" class="error-state">
          Failed to load plugins. Check that the backend is running and plugins are configured.
        </div>
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
import type { PluginData, PluginConfiguration } from '../../services/plugins'

const props = defineProps<{
  workspaceId: number
}>()

const workspaceStore = useWorkspaceStore()
const pluginsList = ref<PluginData[]>([])
const pluginConfigurations = ref<PluginConfiguration[]>([])
const pluginsLoading = ref(false)
const pluginsLoadError = ref(false)
const operationMessage = ref('')

const FALLBACK_ENABLED_STATE = true

const workspaceName = computed(() => {
  const ws = workspaceStore.workspaces.find(w => w.id === props.workspaceId)
  return ws?.name || 'Workspace'
})

async function loadPluginData() {
  pluginsLoading.value = true
  pluginsLoadError.value = false
  try {
    const [allPluginsResponse, configsResponse] = await Promise.all([
      api.get<PluginData[]>('/api/v1/plugins'),
      api.get<PluginConfiguration[]>(`/api/v1/workspaces/${props.workspaceId}/plugins`)
    ])

    pluginsList.value = allPluginsResponse.data ?? []
    pluginConfigurations.value = configsResponse.data ?? []
  } catch (err) {
    console.error('Plugin loading error:', err)
    pluginsLoadError.value = true
    pluginsList.value = []
    pluginConfigurations.value = []
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

<style src="./settings-panel.css"></style>
