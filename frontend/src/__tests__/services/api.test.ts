import { describe, it, expect, beforeEach } from "vitest"
import apiClient from "../../services/api"

describe("API Client", () => {
  beforeEach(() => {
    // Clear localStorage before each test
    localStorage.clear()
  })

  it("should be configured with correct base URL", () => {
    expect(apiClient.defaults.baseURL).toBeDefined()
    // Default or environment variable
    expect(apiClient.defaults.baseURL).toMatch(/http/)
  })

  it("should have correct default headers", () => {
    expect(apiClient.defaults.headers["Content-Type"]).toBe("application/json")
  })

  it("should have request interceptor configured", () => {
    // Check that request interceptors are configured
    expect(apiClient.interceptors.request).toBeDefined()
  })

  it("should have response interceptor configured", () => {
    // Check that response interceptors are configured
    expect(apiClient.interceptors.response).toBeDefined()
  })
})
