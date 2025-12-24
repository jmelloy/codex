# Frontend Tests

This directory contains tests for the Codex frontend application.

## Test Framework

- **Vitest**: Fast unit test framework for Vite projects
- **Vue Test Utils**: Official testing utility library for Vue.js
- **Happy-DOM**: Lightweight DOM implementation for testing

## Running Tests

```bash
# Run tests once
npm test -- --run

# Run tests in watch mode
npm test

# Run tests with UI
npm run test:ui

# Generate coverage report
npm run coverage
```

## Test Structure

- `__tests__/`: Main test directory
  - `components/`: Component tests
  - `services/`: Service and utility tests
  - Other feature-specific test files

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
