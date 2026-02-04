<template>
  <div class="p-8">
    <div class="max-w-4xl mx-auto">
      <h2 class="text-3xl font-bold mb-6 text-text-primary">Workspace Preferences</h2>

      <!-- Workspace Selector -->
      <div
        class="rounded-lg shadow-md p-6 mb-6 border border-border-medium bg-bg-primary/80 backdrop-blur-sm"
      >
        <h3 class="text-xl font-semibold mb-4 text-text-primary">Select Workspace</h3>
        <select
          v-model="selectedWorkspaceId"
          @change="loadWorkspacePlugins"
          class="w-full px-3 py-2 border border-border-medium rounded-md bg-bg-primary text-text-primary"
        >
          <option :value="null">Select a workspace...</option>
          <option
            v-for="workspace in workspaces"
            :key="workspace.id"
            :value="workspace.id"
          >
            {{ workspace.name }}
          </option>
        </select>
      </div>

      <!-- Plugin Management Section -->
      <div
        v-if="selectedWorkspaceId"
        class="rounded-lg shadow-md p-6 border border-border-medium bg-bg-primary/80 backdrop-blur-sm"
      >
        <h3 class="text-xl font-semibold mb-4 text-text-primary">Plugins</h3>
        <p class="mb-6 text-text-secondary">
          Manage plugins for this workspace. Plugins can be enabled/disabled and configured here.
          Notebooks can override these settings.
        </p>

        <div v-if="loadingPlugins" class="text-text-secondary">
          Loading plugins...
        </div>

        <div v-else-if="allPlugins.length === 0" class="text-text-secondary">
          No plugins available.
        </div>

        <div v-else class="space-y-4">
          <div
            v-for="plugin in allPlugins"
            :key="plugin.id"
            class="p-4 rounded-lg border border-border-medium hover:border-primary/50 transition-all"
          >
            <div class="flex items-start justify-between">
              <div class="flex-1">
                <div class="flex items-center gap-3 mb-2">
                  <h4 class="font-semibold text-text-primary">{{ plugin.name }}</h4>
                  <span class="text-xs text-text-secondary bg-bg-secondary px-2 py-0.5 rounded">
                    v{{ plugin.version }}
                  </span>
                  <span class="text-xs text-text-secondary bg-bg-secondary px-2 py-0.5 rounded">
                    {{ plugin.type }}
                  </span>
                </div>
                <p class="text-sm text-text-secondary mb-3">
                  {{ plugin.manifest?.description || 'No description' }}
                </p>
              </div>
              <div class="flex items-center gap-2">
                <label class="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    :checked="isPluginEnabled(plugin.id)"
                    @change="togglePlugin(plugin.id, $event)"
                    class="sr-only peer"
                  />
                  <div
                    class="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary/20 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary"
                  ></div>
                  <span class="ml-3 text-sm font-medium text-text-primary">
                    {{ isPluginEnabled(plugin.id) ? 'Enabled' : 'Disabled' }}
                  </span>
                </label>
              </div>
            </div>
          </div>
        </div>

        <div
          v-if="saveMessage"
          class="mt-4 p-3 bg-success-bg border border-success-border rounded-md text-success text-sm font-medium"
        >
          ✓ {{ saveMessage }}
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from "vue"
import { useWorkspaceStore } from "../stores/workspace"
import api from "../services/api"

const workspaceStore = useWorkspaceStore()

interface Plugin {
  id: string
  name: string
  version: string
  type: string
  enabled: boolean
  manifest: any
}

interface PluginConfig {
  plugin_id: string
  enabled: boolean
  config: any
}

const workspaces = computed(() => workspaceStore.workspaces)
const selectedWorkspaceId = ref<number | null>(null)
const allPlugins = ref<Plugin[]>([])
const pluginConfigs = ref<PluginConfig[]>([])
const loadingPlugins = ref(false)
const saveMessage = ref("")

// Default plugin enabled state - matches backend DEFAULT_PLUGIN_ENABLED
const DEFAULT_PLUGIN_ENABLED = true

onMounted(async () => {
  await workspaceStore.loadWorkspaces()
  
  // Select first workspace if available
  if (workspaces.value.length > 0 && workspaces.value[0]?.id) {
    selectedWorkspaceId.value = workspaces.value[0].id
    await loadWorkspacePlugins()
  }
})

async function loadWorkspacePlugins() {
  if (!selectedWorkspaceId.value) return
  
  loadingPlugins.value = true
  try {
    // Load all plugins
    const pluginsResponse = await api.get<Plugin[]>('/api/v1/plugins')
    allPlugins.value = pluginsResponse.data

    // Load workspace-specific configs
    const configsResponse = await api.get<PluginConfig[]>(
      `/api/v1/workspaces/${selectedWorkspaceId.value}/plugins`
    )
    pluginConfigs.value = configsResponse.data
  } catch (error) {
    console.error('Failed to load plugins:', error)
  } finally {
    loadingPlugins.value = false
  }
}

function isPluginEnabled(pluginId: string): boolean {
  const config = pluginConfigs.value.find(c => c.plugin_id === pluginId)
  return config ? config.enabled : DEFAULT_PLUGIN_ENABLED
}

async function togglePlugin(pluginId: string, event: Event) {
  if (!selectedWorkspaceId.value) return
  
  const target = event.target as HTMLInputElement
  const enabled = target.checked
  
  try {
    await api.put(
      `/api/v1/workspaces/${selectedWorkspaceId.value}/plugins/${pluginId}`,
      { enabled }
    )
    
    // Update local state
    const existingConfig = pluginConfigs.value.find(c => c.plugin_id === pluginId)
    if (existingConfig) {
      existingConfig.enabled = enabled
    } else {
      pluginConfigs.value.push({
        plugin_id: pluginId,
        enabled,
        config: {}
      })
    }
    
    saveMessage.value = `Plugin ${enabled ? 'enabled' : 'disabled'} successfully`
    setTimeout(() => {
      saveMessage.value = ""
    }, 3000)
  } catch (error) {
    console.error('Failed to toggle plugin:', error)
    // Revert the checkbox state
    target.checked = !enabled
  }
}
</script>

<style scoped>
/* Additional styling if needed */
</style>
