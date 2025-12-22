// Test setup file for Vitest
import { config } from '@vue/test-utils'

// Configure Vue Test Utils globally
config.global.stubs = {
  // Add any global stubs needed
}

// Mock window.matchMedia for tests that use it
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {}, // deprecated
    removeListener: () => {}, // deprecated
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => true,
  }),
})
