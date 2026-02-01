# Chart Example Plugin

This plugin demonstrates how plugins can manage their own build dependencies and versioning.

## Features

- Uses Chart.js (4.4.1) as a plugin-specific dependency
- Demonstrates isolated dependency management
- Shows how plugins can use specialized libraries without affecting other plugins

## Dependencies

This plugin has its own `package.json` that specifies:
- `chart.js` - Charting library for creating interactive charts

## Usage

Embed a chart in your markdown:

```chart
type: bar
data:
  labels: [Q1, Q2, Q3, Q4]
  datasets:
    - label: Revenue
      data: [10, 20, 30, 40]
```

## Building

The build system will automatically install this plugin's dependencies before building:

```bash
# Build this plugin specifically
make build-plugin PLUGIN=chart-example

# Or build all plugins
npm run build
```

## How It Works

1. The build system detects the plugin has its own `package.json`
2. Dependencies are installed in `chart-example/node_modules/`
3. The build uses these local dependencies
4. No interference with other plugins' dependencies
