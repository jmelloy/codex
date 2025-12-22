# Frontend Tests

This directory contains the test suite for the Codex frontend application.

## Test Framework

- **Vitest**: Fast unit test framework built on top of Vite
- **@vue/test-utils**: Official testing utility library for Vue 3
- **jsdom**: JavaScript implementation of web standards for Node.js

## Running Tests

```bash
# Run tests once
npm test

# Run tests in watch mode
npm test -- --watch

# Run tests with UI
npm run test:ui

# Run tests with coverage
npm run test:coverage
```

## Test Structure

### Unit Tests

- **`stores.notebooks.test.ts`**: Tests for the Pinia store managing notebook state
  - State initialization
  - CRUD operations (create, read, update)
  - Error handling
  - Computed properties

- **`api.test.ts`**: Tests for the API client layer
  - HTTP request formation
  - Query parameter encoding
  - Response handling
  - Error handling

### Component Tests

- **`components.Sidebar.test.ts`**: Tests for the Sidebar component
  - Rendering of UI elements
  - Directory expansion/collapse
  - File navigation
  - Icon selection based on file types
  - Active state detection

### View Tests

- **`views.NotebooksView.test.ts`**: Tests for the Notebooks list view
  - Loading, error, and empty states
  - Notebook grid rendering
  - Modal interactions (create notebook)
  - Form validation
  - Navigation after creation
  - Tag parsing

## Test Coverage

Current test coverage includes:

- ✅ Pinia store logic (notebooks store)
- ✅ API client functions
- ✅ Component rendering and interactions (Sidebar)
- ✅ View component behavior (NotebooksView)

## Writing New Tests

### Basic Test Structure

```typescript
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import YourComponent from '@/components/YourComponent.vue'

describe('YourComponent', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('renders correctly', () => {
    const wrapper = mount(YourComponent)
    expect(wrapper.text()).toContain('Expected text')
  })
})
```

### Mocking APIs

```typescript
vi.mock('@/api', () => ({
  someApi: {
    method: vi.fn().mockResolvedValue({ data: 'mock data' }),
  },
}))
```

### Testing with Router

```typescript
import { createRouter, createMemoryHistory } from 'vue-router'

const router = createRouter({
  history: createMemoryHistory(),
  routes: [/* your routes */],
})

const wrapper = mount(YourComponent, {
  global: {
    plugins: [router],
  },
})
```

## Best Practices

1. **Isolation**: Each test should be independent and not rely on others
2. **Setup/Teardown**: Use `beforeEach`/`afterEach` to set up clean state
3. **Descriptive Names**: Test names should clearly describe what they test
4. **Arrange-Act-Assert**: Structure tests with clear setup, action, and verification
5. **Mock External Dependencies**: Mock API calls, routers, and external services
6. **Test User Interactions**: Test how users interact with components, not implementation details

## Configuration

Test configuration is in:
- `vite.config.ts`: Main Vitest configuration
- `src/tests/setup.ts`: Global test setup and mocks

## Continuous Integration

Tests run automatically on:
- Pull requests
- Pushes to main/develop branches

All tests must pass before code can be merged.
