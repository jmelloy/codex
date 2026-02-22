import { describe, it, expect, beforeEach, vi, type Mock } from "vitest"
import apiClient from "../../services/api"
import {
  listIntegrations,
  getIntegration,
  getIntegrationConfig,
  updateIntegrationConfig,
  testIntegrationConnection,
  getIntegrationBlocks,
  executeIntegrationEndpoint,
  setIntegrationEnabled,
} from "../../services/integration"

vi.mock("../../services/api", () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
  },
}))

const mockGet = apiClient.get as Mock
const mockPost = apiClient.post as Mock
const mockPut = apiClient.put as Mock

const mockIntegration = {
  id: "weather-api",
  name: "Weather API",
  description: "Weather data integration",
  version: "1.0.0",
  author: "Test Author",
  api_type: "rest",
  base_url: "https://api.weather.com",
  auth_method: "api_key",
  enabled: true,
}

describe("Integration Service", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe("listIntegrations", () => {
    it("lists integrations for a workspace/notebook", async () => {
      mockGet.mockResolvedValue({ data: [mockIntegration] })

      const result = await listIntegrations(1, 2)

      expect(result).toEqual([mockIntegration])
      expect(mockGet).toHaveBeenCalledWith("/api/v1/workspaces/1/notebooks/2/integrations")
    })

    it("accepts string ids", async () => {
      mockGet.mockResolvedValue({ data: [] })

      await listIntegrations("ws-1", "nb-2")

      expect(mockGet).toHaveBeenCalledWith("/api/v1/workspaces/ws-1/notebooks/nb-2/integrations")
    })
  })

  describe("getIntegration", () => {
    it("gets integration details", async () => {
      const details = { ...mockIntegration, properties: [], blocks: [], endpoints: [] }
      mockGet.mockResolvedValue({ data: details })

      const result = await getIntegration("weather-api")

      expect(result).toEqual(details)
      expect(mockGet).toHaveBeenCalledWith("/api/v1/plugins/integrations/weather-api")
    })
  })

  describe("getIntegrationConfig", () => {
    it("gets config for a workspace/notebook", async () => {
      const config = { plugin_id: "weather-api", config: { api_key: "***" } }
      mockGet.mockResolvedValue({ data: config })

      const result = await getIntegrationConfig("weather-api", 1, 2)

      expect(result).toEqual(config)
      expect(mockGet).toHaveBeenCalledWith(
        "/api/v1/workspaces/1/notebooks/2/integrations/weather-api/config"
      )
    })
  })

  describe("updateIntegrationConfig", () => {
    it("updates config for a workspace/notebook", async () => {
      const updated = { plugin_id: "weather-api", config: { api_key: "new-key" } }
      mockPut.mockResolvedValue({ data: updated })

      const result = await updateIntegrationConfig("weather-api", 1, 2, { api_key: "new-key" })

      expect(result).toEqual(updated)
      expect(mockPut).toHaveBeenCalledWith(
        "/api/v1/workspaces/1/notebooks/2/integrations/weather-api/config",
        { config: { api_key: "new-key" } }
      )
    })
  })

  describe("testIntegrationConnection", () => {
    it("tests connection successfully", async () => {
      const testResult = { success: true, message: "Connected", details: { latency: 50 } }
      mockPost.mockResolvedValue({ data: testResult })

      const result = await testIntegrationConnection("weather-api", { api_key: "test-key" })

      expect(result).toEqual(testResult)
      expect(mockPost).toHaveBeenCalledWith("/api/v1/plugins/integrations/weather-api/test", {
        config: { api_key: "test-key" },
      })
    })
  })

  describe("getIntegrationBlocks", () => {
    it("gets available blocks", async () => {
      const blocks = [{ id: "current-weather", name: "Current Weather" }]
      mockGet.mockResolvedValue({ data: blocks })

      const result = await getIntegrationBlocks("weather-api")

      expect(result).toEqual(blocks)
      expect(mockGet).toHaveBeenCalledWith("/api/v1/plugins/integrations/weather-api/blocks")
    })
  })

  describe("executeIntegrationEndpoint", () => {
    it("executes an endpoint with parameters", async () => {
      const response = { temperature: 72, unit: "F" }
      mockPost.mockResolvedValue({ data: response })

      const result = await executeIntegrationEndpoint("weather-api", 1, 2, "get-current", {
        city: "NYC",
      })

      expect(result).toEqual(response)
      expect(mockPost).toHaveBeenCalledWith(
        "/api/v1/workspaces/1/notebooks/2/integrations/weather-api/execute",
        { endpoint_id: "get-current", parameters: { city: "NYC" } }
      )
    })

    it("executes an endpoint without parameters", async () => {
      mockPost.mockResolvedValue({ data: {} })

      await executeIntegrationEndpoint("weather-api", 1, 2, "health-check")

      expect(mockPost).toHaveBeenCalledWith(
        "/api/v1/workspaces/1/notebooks/2/integrations/weather-api/execute",
        { endpoint_id: "health-check", parameters: {} }
      )
    })
  })

  describe("setIntegrationEnabled", () => {
    it("enables an integration", async () => {
      const enabled = { ...mockIntegration, enabled: true }
      mockPut.mockResolvedValue({ data: enabled })

      const result = await setIntegrationEnabled("weather-api", 1, 2, true)

      expect(result).toEqual(enabled)
      expect(mockPut).toHaveBeenCalledWith(
        "/api/v1/workspaces/1/notebooks/2/integrations/weather-api/enable",
        { enabled: true }
      )
    })

    it("disables an integration", async () => {
      const disabled = { ...mockIntegration, enabled: false }
      mockPut.mockResolvedValue({ data: disabled })

      const result = await setIntegrationEnabled("weather-api", 1, 2, false)

      expect(result).toEqual(disabled)
      expect(mockPut).toHaveBeenCalledWith(
        "/api/v1/workspaces/1/notebooks/2/integrations/weather-api/enable",
        { enabled: false }
      )
    })
  })
})
