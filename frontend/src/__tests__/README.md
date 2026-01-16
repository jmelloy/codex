# Frontend Tests

This directory contains comprehensive test suites for the Codex frontend application.

## Test Statistics

- **Total Test Files**: 12
- **Total Tests**: 125 (increased from 12 baseline tests)
- **Overall Coverage**: 73.37% statements, 78.6% branches, 64.28% functions, 74.01% lines

## Test Structure

The tests are organized by type:

### Components (`components/`)
- **App.test.ts** - Main app component tests (2 tests)
- **FormGroup.test.ts** - Form group wrapper component tests (7 tests)
- **Modal.test.ts** - Modal dialog component tests (15 tests)
- **MarkdownEditor.test.ts** - Rich markdown editor tests (20 tests)
- **MarkdownViewer.test.ts** - Markdown rendering tests (6 tests)
- **FilePropertiesPanel.test.ts** - File properties panel tests (26 tests)

### Services (`services/`)
- **api.test.ts** - API client configuration tests (4 tests)

### Stores (`stores/`)
- **auth.test.ts** - Authentication store tests (11 tests)

### Utilities (`utils/`)
- **date.test.ts** - Date formatting utility tests (5 tests)
- **validation.test.ts** - Form validation utility tests (13 tests)

### Views (`views/`)
- **LoginView.test.ts** - Login page tests (8 tests)
- **RegisterView.test.ts** - Registration page tests (8 tests)

### Coverage by Module

| Module | Statements | Branches | Functions | Lines |
|--------|-----------|----------|-----------|-------|
| Components | 78.08% | 79.72% | 64.28% | 80.19% |
| Services | 20% | 33.33% | 0% | 20% |
| Stores | 100% | 100% | 100% | 100% |
| Utils | 100% | 100% | 100% | 100% |
| Views | 55.17% | 73.33% | 80% | 53.57% |

## Test Framework

- **Vitest**: Fast unit test framework for Vite projects
- **Vue Test Utils**: Official testing utility library for Vue.js
- **Happy-DOM**: Lightweight DOM implementation for testing
- **@vitest/coverage-v8**: Code coverage reporting

## Running Tests

```bash
# Run all tests once
npm test -- --run

# Run tests in watch mode
npm test

# Run tests with UI
npm run test:ui

# Generate coverage report
npm run coverage
```

## Test Conventions

1. **File naming**: Test files use `.test.ts` suffix
2. **Structure**: Tests follow Arrange-Act-Assert pattern
3. **Mocking**: External dependencies (API calls, stores) are mocked using `vi.mock()`
4. **Isolation**: Each test runs in isolation with fresh state via `beforeEach` hooks
5. **Async handling**: Async operations use `async/await` with proper awaiting

## Writing Tests

### Component Tests

```typescript
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import MyComponent from '../MyComponent.vue'

describe('MyComponent', () => {
  it('renders properly', () => {
    const wrapper = mount(MyComponent, { 
      props: { msg: 'Hello' } 
    })
    expect(wrapper.text()).toContain('Hello')
  })
})
```

### Service Tests

```typescript
import { describe, it, expect } from 'vitest'
import { myService } from '../../services/myService'

describe('myService', () => {
  it('should perform operation', () => {
    const result = myService.doSomething()
    expect(result).toBe(expectedValue)
  })
})
```

## Configuration

Test configuration is in `vite.config.ts` under the `test` section.
