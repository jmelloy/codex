import { describe, it, expect, beforeEach, vi } from "vitest"
import { setActivePinia, createPinia } from "pinia"
import { useIntegrationStore } from "../../stores/integration"
import * as integrationService from "../../services/integration"

vi.mock("../../services/integration", () => ({
  listIntegrations: vi.fn(),
  setIntegrationEnabled: vi.fn(),
}))

const mockIntegration = {
  id: "test-integration",
  name: "Test Integration",
  description: "A test integration",
  version: "1.0.0",
  author: "Test Author",
  api_type: "rest",
  enabled: true,
}

describe("Integration Store", () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it("initializes with correct default values", () => {
    const store = useIntegrationStore()
    expect(store.integrations).toEqual([])
    expect(store.integrationsLoaded).toBe(false)
    expect(store.integrationsLoadError).toBe(false)
  })

  it("loads integrations successfully and skips reload if already loaded", async () => {
    const store = useIntegrationStore()
    vi.mocked(integrationService.listIntegrations).mockResolvedValue([mockIntegration])

    await store.loadIntegrations(1, 1)
    expect(integrationService.listIntegrations).toHaveBeenCalledWith(1, 1)
    expect(store.integrations).toEqual([mockIntegration])
    expect(store.integrationsLoaded).toBe(true)
    expect(store.integrationsLoadError).toBe(false)

    // Second load should not call the service again
    await store.loadIntegrations(1, 1)
    expect(integrationService.listIntegrations).toHaveBeenCalledTimes(1)
  })

  it("handles load error and allows retry", async () => {
    const store = useIntegrationStore()

    // First attempt fails
    vi.mocked(integrationService.listIntegrations).mockRejectedValueOnce(new Error("Network error"))
    await store.loadIntegrations(1, 1)
    expect(store.integrationsLoadError).toBe(true)
    expect(store.integrationsLoaded).toBe(false)

    // Second attempt succeeds
    vi.mocked(integrationService.listIntegrations).mockResolvedValue([mockIntegration])
    await store.loadIntegrations(1, 1)
    expect(store.integrations).toEqual([mockIntegration])
    expect(store.integrationsLoaded).toBe(true)
    expect(store.integrationsLoadError).toBe(false)
    expect(integrationService.listIntegrations).toHaveBeenCalledTimes(2)
  })

  it("passes workspace_id and notebook_id when loading", async () => {
    const store = useIntegrationStore()
    vi.mocked(integrationService.listIntegrations).mockResolvedValue([mockIntegration])
    await store.loadIntegrations(123, 456)
    expect(integrationService.listIntegrations).toHaveBeenCalledWith(123, 456)
  })

  it("provides available integrations computed and resets state", () => {
    const store = useIntegrationStore()
    store.integrations = [mockIntegration]
    expect(store.availableIntegrations).toEqual([mockIntegration])

    store.integrationsLoaded = true
    store.reset()
    expect(store.integrations).toEqual([])
    expect(store.integrationsLoaded).toBe(false)
  })

  it("toggles integration enabled state", async () => {
    const store = useIntegrationStore()
    store.integrations = [{ ...mockIntegration }]

    const updated = { ...mockIntegration, enabled: false }
    vi.mocked(integrationService.setIntegrationEnabled).mockResolvedValue(updated)

    await store.toggleIntegrationEnabled("test-integration", 1, 1, false)
    expect(integrationService.setIntegrationEnabled).toHaveBeenCalledWith("test-integration", 1, 1, false)
    expect(store.integrations[0].enabled).toBe(false)
  })

  it("handles toggle error without changing state", async () => {
    const store = useIntegrationStore()
    store.integrations = [{ ...mockIntegration }]

    vi.mocked(integrationService.setIntegrationEnabled).mockRejectedValue(new Error("API error"))

    await expect(
      store.toggleIntegrationEnabled("test-integration", 1, 1, false)
    ).rejects.toThrow("API error")
    expect(store.integrations[0].enabled).toBe(true)
  })
})
