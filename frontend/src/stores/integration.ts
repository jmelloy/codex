import { defineStore } from "pinia"
import { ref, computed } from "vue"
import { listIntegrations, type Integration } from "../services/integration"

export const useIntegrationStore = defineStore("integration", () => {
  const integrations = ref<Integration[]>([])
  const integrationsLoaded = ref(false)
  const integrationsLoadError = ref(false)

  const availableIntegrations = computed(() => integrations.value)

  async function loadIntegrations() {
    // Only load once unless there was an error
    if (integrationsLoaded.value && !integrationsLoadError.value) return

    try {
      integrations.value = await listIntegrations()
      integrationsLoaded.value = true
      integrationsLoadError.value = false
    } catch (error) {
      console.error("Failed to load integrations from API:", error)
      integrations.value = []
      integrationsLoadError.value = true
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
    reset,
  }
})
