// Test setup file for Vitest
// Provides localStorage mock for happy-dom environment

const localStorageMock = {
  store: {} as Record<string, string>,
  getItem(key: string) {
    return this.store[key] || null
  },
  setItem(key: string, value: string) {
    this.store[key] = value
  },
  removeItem(key: string) {
    delete this.store[key]
  },
  clear() {
    this.store = {}
  },
  get length() {
    return Object.keys(this.store).length
  },
  key(index: number) {
    return Object.keys(this.store)[index] || null
  },
}

Object.defineProperty(globalThis, "localStorage", {
  value: localStorageMock,
  writable: true,
})

// Mock fetch for plugin manifest requests to avoid connection errors in tests
const originalFetch = globalThis.fetch
globalThis.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
  const url = typeof input === "string" ? input : input instanceof URL ? input.href : input.url

  // Mock the plugins manifest request to return an empty plugins list
  if (url.includes("/plugins/plugins.json")) {
    return new Response(
      JSON.stringify({
        version: "1.0.0",
        buildTime: new Date().toISOString(),
        plugins: [],
      }),
      {
        status: 200,
        headers: { "Content-Type": "application/json" },
      },
    )
  }

  // For all other requests, use the original fetch
  return originalFetch(input, init)
}
