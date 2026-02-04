import { defineStore } from "pinia"
import { ref, computed } from "vue"
import { listIntegrations, setIntegrationEnabled, type Integration } from "../services/integration"

export const useIntegrationStore = defineStore("integration", () => {
  const integrations = ref<Integration[]>([])
  const integrationsLoaded = ref(false)
  const integrationsLoadError = ref(false)

  const availableIntegrations = computed(() => integrations.value)

  async function loadIntegrations(workspaceId: number | string, notebookId: number | string) {
    // Only load once unless there was an error
    if (integrationsLoaded.value && !integrationsLoadError.value) return

    try {
      integrations.value = await listIntegrations(workspaceId, notebookId)
      integrationsLoaded.value = true
      integrationsLoadError.value = false
    } catch (error) {
      console.error("Failed to load integrations from API:", error)
      integrations.value = []
      integrationsLoadError.value = true
    }
  }

  async function toggleIntegrationEnabled(
    integrationId: string,
    workspaceId: number | string,
    notebookId: number | string,
    enabled: boolean
  ) {
    try {
      const updatedIntegration = await setIntegrationEnabled(
        integrationId,
        workspaceId,
        notebookId,
        enabled
      )
      
      // Update the integration in the local state
      const index = integrations.value.findIndex(i => i.id === integrationId)
      if (index !== -1) {
        integrations.value[index] = updatedIntegration
      }
      
      return updatedIntegration
    } catch (error) {
      console.error("Failed to toggle integration enabled state:", error)
      throw error
    }
  }

  function reset() {
    integrations.value = []
    integrationsLoaded.value = false
    integrationsLoadError.value = false
  }

  return {
    integrations,
    availableIntegrations,
    integrationsLoaded,
    integrationsLoadError,
    loadIntegrations,
    toggleIntegrationEnabled,
    reset,
  }
})
