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
