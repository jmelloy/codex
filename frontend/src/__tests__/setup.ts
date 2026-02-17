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

// Mock document.createElement to prevent theme stylesheet loading during tests
// This prevents ECONNREFUSED errors when theme store tries to load CSS files
const originalCreateElement = document.createElement.bind(document)
document.createElement = function (tagName: string, options?: ElementCreationOptions) {
  const element = originalCreateElement(tagName, options) as HTMLElement
  
  // If creating a link element, intercept href setting to prevent actual loading
  if (tagName.toLowerCase() === "link") {
    let _href = ""
    let _onerror: ((this: GlobalEventHandlers, ev: Event | string) => any) | null = null
    
    Object.defineProperty(element, "href", {
      get: () => _href,
      set: (value: string) => {
        _href = value
        // Don't actually load the stylesheet - just do nothing
        // This prevents the network request that causes ECONNREFUSED errors
      },
      configurable: true,
    })
    
    Object.defineProperty(element, "onerror", {
      get: () => _onerror,
      set: (handler: ((this: GlobalEventHandlers, ev: Event | string) => any) | null) => {
        _onerror = handler
        // Don't call the error handler since we're preventing the load
      },
      configurable: true,
    })
  }
  
  return element
}
