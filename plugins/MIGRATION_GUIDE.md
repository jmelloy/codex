# Plugin Dependency Management - Migration Guide

This guide helps existing plugin developers migrate to the new self-managed dependencies system.

## Overview

As of this update, Codex plugins can now manage their own build dependencies and versioning independently. This means each plugin can have its own `package.json` file with its own dependencies, completely isolated from other plugins.

## What Changed?

### Before
- All plugins shared a single `package.json` file at `plugins/package.json`
- All plugins used the same dependency versions
- Adding a new dependency affected all plugins
- Version conflicts were common

### After
- Each plugin can optionally have its own `package.json`
- Dependencies are installed in `<plugin-dir>/node_modules/`
- Complete isolation between plugins
- No version conflicts
- Backward compatible - plugins without `package.json` still work

## Do You Need to Migrate?

**You only need a plugin-specific `package.json` if:**
- Your plugin uses Vue components with additional npm dependencies
- You need a specific version of a dependency different from other plugins
- You want to use a specialized library (charts, dates, animations, etc.)

**You DON'T need to migrate if:**
- Your plugin only has YAML configuration and CSS (themes)
- Your plugin uses only Vue and standard browser APIs
- Your plugin works fine with shared dependencies

## Migration Steps

### Step 1: Assess Your Plugin

Check if your plugin has Vue components that need additional dependencies:

```bash
# Check for Vue components
ls plugins/your-plugin/components/*.vue

# Check your component imports
grep -r "import.*from" plugins/your-plugin/components/
```

If you see imports from packages other than `vue`, you need those as dependencies.

### Step 2: Create package.json

Create `plugins/your-plugin/package.json`:

```json
{
  "name": "@codex-plugin/your-plugin",
  "version": "1.0.0",
  "description": "Brief description of your plugin",
  "type": "module",
  "private": true,
  "dependencies": {
    "your-dependency": "^1.0.0"
  },
  "peerDependencies": {
    "vue": "^3.5.0"
  }
}
```

**Important:**
- Always include `"type": "module"`
- Always include `"private": true`
- List `vue` as a peer dependency (not a regular dependency)
- Use appropriate version ranges (see Best Practices below)

### Step 3: Install Dependencies

From the plugins directory:

```bash
cd plugins
npm run build -- --plugin=your-plugin
```

This will:
1. Install your plugin's dependencies
2. Build your component
3. Create `your-plugin/node_modules/` with isolated dependencies

### Step 4: Test Your Plugin

Build and verify:

```bash
# Build your plugin
make build-plugin PLUGIN=your-plugin

# Check the output
ls plugins/your-plugin/dist/
ls plugins/your-plugin/node_modules/
```

Verify the component works in the application.

### Step 5: Update Documentation

Add a note to your plugin's README.md about dependencies:

```markdown
## Dependencies

This plugin uses:
- `chart.js` - For creating interactive charts
- `date-fns` - For date formatting

Dependencies are automatically installed during the build process.
```

## Real-World Example: Chart Plugin

See `plugins/chart-example/` for a complete working example:

```
plugins/chart-example/
├── package.json          # Plugin-specific dependencies
├── node_modules/         # Isolated dependencies (gitignored)
├── components/
│   └── ChartBlock.vue    # Uses Chart.js
├── dist/                 # Built output (gitignored)
│   └── chart.js
├── manifest.yml          # Plugin manifest
└── README.md            # Documentation
```

### package.json Example

```json
{
  "name": "@codex-plugin/chart-example",
  "version": "1.0.0",
  "description": "Chart plugin demonstrating plugin-specific dependencies",
  "type": "module",
  "private": true,
  "dependencies": {
    "chart.js": "^4.4.1"
  },
  "peerDependencies": {
    "vue": "^3.5.0"
  }
}
```

### Vue Component Example

```vue
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Chart, registerables } from 'chart.js'

// Chart.js is available because it's in this plugin's package.json
Chart.register(...registerables)

// ... component code
</script>
```

## Best Practices

### 1. Version Ranges

Choose appropriate version ranges for stability:

```json
{
  "dependencies": {
    // Caret (^) - Allows minor and patch updates
    "chart.js": "^4.4.1",     // 4.4.1 <= version < 5.0.0
    
    // Tilde (~) - Allows only patch updates  
    "date-fns": "~3.0.0",     // 3.0.0 <= version < 3.1.0
    
    // Exact - No updates allowed
    "lodash": "4.17.21"       // Exactly 4.17.21
  }
}
```

**Recommendation:** Use caret (^) for most dependencies, unless you need strict version control.

### 2. Peer Dependencies

Always list these as peer dependencies (not regular dependencies):
- `vue` - Provided by the main application
- Any other core dependencies shared across plugins

```json
{
  "peerDependencies": {
    "vue": "^3.5.0"
  }
}
```

### 3. Keep Dependencies Minimal

Only add dependencies you actually use:

```json
// ❌ Bad - Includes unused dependencies
{
  "dependencies": {
    "chart.js": "^4.4.1",
    "lodash": "^4.17.21",
    "moment": "^2.29.4",
    "axios": "^1.6.0"
  }
}

// ✅ Good - Only what's needed
{
  "dependencies": {
    "chart.js": "^4.4.1"
  }
}
```

### 4. Document Dependencies

Add a comment or README section explaining each dependency:

```markdown
## Dependencies

- `chart.js` (^4.4.1) - Required for rendering interactive charts
  - Provides bar, line, pie, and doughnut chart types
  - Used in ChartBlock.vue component
```

### 5. Test Isolation

Verify your dependencies don't conflict:

```bash
# Build your plugin
npm run build -- --plugin=your-plugin

# Build another plugin with different versions
npm run build -- --plugin=other-plugin

# Both should build without conflicts
```

## Troubleshooting

### Issue: "Cannot find module 'some-package'"

**Solution:**
1. Make sure the package is in your `package.json`
2. Rebuild the plugin: `npm run build -- --plugin=your-plugin`
3. Check that `node_modules` exists in your plugin directory

### Issue: "Build fails with type errors"

**Solution:**
1. Install type definitions: `npm install --save-dev @types/your-package`
2. Add to `devDependencies` in your plugin's `package.json`

### Issue: "Vue import not working"

**Solution:**
1. Make sure `vue` is listed in `peerDependencies`, not `dependencies`
2. Don't install `vue` as a regular dependency - it comes from the parent

### Issue: "Plugin builds but doesn't work at runtime"

**Solution:**
1. Check that external dependencies are marked as `external` in build config
2. Verify the dependency is bundled correctly in `dist/*.js`
3. Check browser console for runtime errors

## Backward Compatibility

### Existing Plugins Continue to Work

Plugins without their own `package.json` automatically use shared dependencies:

```
plugins/
  old-plugin/              # No package.json
    components/
      OldComponent.vue     # Uses shared dependencies
```

This plugin continues to work exactly as before.

### Mixed Environment

You can have both types of plugins:

```
plugins/
  modern-plugin/           # Has package.json
    package.json           # Self-managed dependencies
    node_modules/
    components/
  
  legacy-plugin/           # No package.json
    components/            # Uses shared dependencies
```

Both work perfectly together.

## Common Migration Scenarios

### Scenario 1: Simple Component with No Extra Dependencies

**Before:**
```vue
<script setup lang="ts">
import { ref } from 'vue'
// Only uses Vue
</script>
```

**Action:** No migration needed! Your plugin works as-is.

---

### Scenario 2: Component Using External Library

**Before:**
```vue
<script setup lang="ts">
import { ref } from 'vue'
// Uses Chart.js but it's in shared package.json
import { Chart } from 'chart.js'
</script>
```

**After:** Create plugin-specific `package.json`

```json
{
  "name": "@codex-plugin/my-charts",
  "version": "1.0.0",
  "private": true,
  "type": "module",
  "dependencies": {
    "chart.js": "^4.4.1"
  },
  "peerDependencies": {
    "vue": "^3.5.0"
  }
}
```

---

### Scenario 3: Multiple Components, Same Dependencies

**Structure:**
```
plugins/my-plugin/
  package.json              # Shared by all components
  components/
    Chart1.vue             # Uses chart.js
    Chart2.vue             # Uses chart.js
    Chart3.vue             # Uses chart.js
```

**package.json:**
```json
{
  "name": "@codex-plugin/my-plugin",
  "private": true,
  "dependencies": {
    "chart.js": "^4.4.1"
  },
  "peerDependencies": {
    "vue": "^3.5.0"
  }
}
```

All components in the plugin share the same dependencies.

---

## Getting Help

### Build Issues
```bash
# Clean and rebuild
npm run clean
npm run build -- --plugin=your-plugin

# Check for errors
ls -la plugins/your-plugin/node_modules/
```

### Test Your Changes
```bash
# Run plugin tests
cd backend
pytest tests/test_plugins.py -v

# Build and verify
cd ../plugins
npm run build -- --plugin=your-plugin
```

### Questions?

- Check `plugins/README.md` for comprehensive guide
- Look at `plugins/chart-example/` for working example
- File an issue if you encounter problems

## Summary

✅ **Optional** - Only migrate if you need plugin-specific dependencies
✅ **Backward Compatible** - Existing plugins continue to work
✅ **Isolated** - Each plugin has its own dependencies
✅ **Simple** - Just add a `package.json` to your plugin directory
✅ **Tested** - Fully tested with 49+ passing tests

The new system provides flexibility while maintaining simplicity. Migrate when you need it, keep it simple when you don't.
