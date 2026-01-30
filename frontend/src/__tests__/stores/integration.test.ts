import { describe, it, expect, beforeEach, vi } from "vitest"
import { setActivePinia, createPinia } from "pinia"
import { useIntegrationStore } from "../../stores/integration"
import * as integrationService from "../../services/integration"

// Mock the integration service
vi.mock("../../services/integration", () => ({
  listIntegrations: vi.fn(),
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

    await store.loadIntegrations()

    expect(integrationService.listIntegrations).toHaveBeenCalled()
    expect(store.integrations).toEqual(mockIntegrations)
    expect(store.integrationsLoaded).toBe(true)
    expect(store.integrationsLoadError).toBe(false)
  })

  it("handles load error gracefully", async () => {
    const store = useIntegrationStore()

    vi.mocked(integrationService.listIntegrations).mockRejectedValue(
      new Error("Network error")
    )

    await store.loadIntegrations()

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
    await store.loadIntegrations()
    expect(integrationService.listIntegrations).toHaveBeenCalledTimes(1)

    // Second load should not call the service again
    await store.loadIntegrations()
    expect(integrationService.listIntegrations).toHaveBeenCalledTimes(1)
  })

  it("reloads after error", async () => {
    const store = useIntegrationStore()

    // First attempt fails
    vi.mocked(integrationService.listIntegrations).mockRejectedValueOnce(
      new Error("Network error")
    )
    await store.loadIntegrations()
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
    await store.loadIntegrations()

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
})
