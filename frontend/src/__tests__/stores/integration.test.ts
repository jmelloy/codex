import { describe, it, expect, beforeEach, vi } from "vitest"
import { setActivePinia, createPinia } from "pinia"
import { useIntegrationStore } from "../../stores/integration"
import * as integrationService from "../../services/integration"

// Mock the integration service
vi.mock("../../services/integration", () => ({
  listIntegrations: vi.fn(),
  setIntegrationEnabled: vi.fn(),
}))

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

  it("loads integrations successfully", async () => {
    const store = useIntegrationStore()
    const mockIntegrations = [
      {
        id: "test-integration",
        name: "Test Integration",
        description: "A test integration",
        version: "1.0.0",
        author: "Test Author",
        api_type: "rest",
        enabled: true,
      },
    ]

    vi.mocked(integrationService.listIntegrations).mockResolvedValue(mockIntegrations)

    await store.loadIntegrations(1, 1)

    expect(integrationService.listIntegrations).toHaveBeenCalledWith(1, 1)
    expect(store.integrations).toEqual(mockIntegrations)
    expect(store.integrationsLoaded).toBe(true)
    expect(store.integrationsLoadError).toBe(false)
  })

  it("handles load error gracefully", async () => {
    const store = useIntegrationStore()

    vi.mocked(integrationService.listIntegrations).mockRejectedValue(
      new Error("Network error")
    )

    await store.loadIntegrations(1, 1)

    expect(store.integrations).toEqual([])
    expect(store.integrationsLoaded).toBe(false)
    expect(store.integrationsLoadError).toBe(true)
  })

  it("does not reload if already loaded", async () => {
    const store = useIntegrationStore()
    const mockIntegrations = [
      {
        id: "test-integration",
        name: "Test Integration",
        description: "A test integration",
        version: "1.0.0",
        author: "Test Author",
        api_type: "rest",
        enabled: true,
      },
    ]

    vi.mocked(integrationService.listIntegrations).mockResolvedValue(mockIntegrations)

    // First load
    await store.loadIntegrations(1, 1)
    expect(integrationService.listIntegrations).toHaveBeenCalledTimes(1)

    // Second load should not call the service again
    await store.loadIntegrations(1, 1)
    expect(integrationService.listIntegrations).toHaveBeenCalledTimes(1)
  })

  it("reloads after error", async () => {
    const store = useIntegrationStore()

    // First attempt fails
    vi.mocked(integrationService.listIntegrations).mockRejectedValueOnce(
      new Error("Network error")
    )
    await store.loadIntegrations(1, 1)
    expect(store.integrationsLoadError).toBe(true)

    // Second attempt succeeds
    const mockIntegrations = [
      {
        id: "test-integration",
        name: "Test Integration",
        description: "A test integration",
        version: "1.0.0",
        author: "Test Author",
        api_type: "rest",
        enabled: true,
      },
    ]
    vi.mocked(integrationService.listIntegrations).mockResolvedValue(mockIntegrations)
    await store.loadIntegrations(1, 1)

    expect(integrationService.listIntegrations).toHaveBeenCalledTimes(2)
    expect(store.integrations).toEqual(mockIntegrations)
    expect(store.integrationsLoaded).toBe(true)
    expect(store.integrationsLoadError).toBe(false)
  })

  it("provides available integrations computed", () => {
    const store = useIntegrationStore()
    const mockIntegrations = [
      {
        id: "test-integration",
        name: "Test Integration",
        description: "A test integration",
        version: "1.0.0",
        author: "Test Author",
        api_type: "rest",
        enabled: true,
      },
    ]

    store.integrations = mockIntegrations

    expect(store.availableIntegrations).toEqual(mockIntegrations)
  })

  it("resets state correctly", () => {
    const store = useIntegrationStore()

    // Set some state
    store.integrations = [
      {
        id: "test-integration",
        name: "Test Integration",
        description: "A test integration",
        version: "1.0.0",
        author: "Test Author",
        api_type: "rest",
        enabled: true,
      },
    ]
    store.integrationsLoaded = true
    store.integrationsLoadError = false

    // Reset
    store.reset()

    expect(store.integrations).toEqual([])
    expect(store.integrationsLoaded).toBe(false)
    expect(store.integrationsLoadError).toBe(false)
  })

  it("toggles integration enabled state successfully", async () => {
    const store = useIntegrationStore()
    const mockIntegration = {
      id: "test-integration",
      name: "Test Integration",
      description: "A test integration",
      version: "1.0.0",
      author: "Test Author",
      api_type: "rest",
      enabled: true,
    }
    
    // Set initial state
    store.integrations = [mockIntegration]
    
    // Mock the API call
    const updatedIntegration = { ...mockIntegration, enabled: false }
    vi.mocked(integrationService.setIntegrationEnabled).mockResolvedValue(updatedIntegration)
    
    // Toggle to disabled
    await store.toggleIntegrationEnabled("test-integration", 1, 1, false)
    
    expect(integrationService.setIntegrationEnabled).toHaveBeenCalledWith("test-integration", 1, 1, false)
    expect(store.integrations[0].enabled).toBe(false)
  })

  it("handles toggle error and throws", async () => {
    const store = useIntegrationStore()
    const mockIntegration = {
      id: "test-integration",
      name: "Test Integration",
      description: "A test integration",
      version: "1.0.0",
      author: "Test Author",
      api_type: "rest",
      enabled: true,
    }
    
    store.integrations = [mockIntegration]
    
    // Mock error
    vi.mocked(integrationService.setIntegrationEnabled).mockRejectedValue(
      new Error("API error")
    )
    
    // Should throw error
    await expect(
      store.toggleIntegrationEnabled("test-integration", 1, 1, false)
    ).rejects.toThrow("API error")
    
    // State should remain unchanged
    expect(store.integrations[0].enabled).toBe(true)
  })

  it("passes workspace_id and notebook_id when loading integrations", async () => {
    const store = useIntegrationStore()
    const mockIntegrations = [
      {
        id: "test-integration",
        name: "Test Integration",
        description: "A test integration",
        version: "1.0.0",
        author: "Test Author",
        api_type: "rest",
        enabled: true,
      },
    ]

    vi.mocked(integrationService.listIntegrations).mockResolvedValue(mockIntegrations)

    await store.loadIntegrations(123, 456)

    expect(integrationService.listIntegrations).toHaveBeenCalledWith(123, 456)
    expect(store.integrations).toEqual(mockIntegrations)
  })
})
