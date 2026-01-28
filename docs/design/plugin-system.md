# Plugin System Design Document

**Version:** 1.0 | **Date:** 2026-01-28 | **Status:** Design Proposal | **Inspired by:** Obsidian Plugin System

## Overview

The Codex Plugin System provides a structured, extensible architecture for adding custom functionality to Codex. Inspired by Obsidian's plugin ecosystem, it supports three distinct plugin types that enable customization of views, themes, and external integrations.

## Goals

1. **Extensibility**: Allow third-party developers to extend Codex functionality
2. **Type Safety**: Well-defined plugin interfaces with validation
3. **Isolation**: Plugins operate in controlled environments with clear boundaries
4. **Discoverability**: Easy installation, configuration, and management
5. **Maintainability**: Clear separation of concerns between plugin types
6. **Backward Compatibility**: Version-aware plugin loading and migration

## Plugin Types

### Type 1: Custom Views & Templates
Custom view components with associated templates and examples.

### Type 2: Themes
Visual styling packages with CSS and configuration.

### Type 3: Integrations
External API connections and data transformations.

---

## Type 1: Custom Views & Templates

Custom views extend Codex's dynamic view system with new visualization and interaction patterns. These are the existing dynamic views (Kanban, TaskList, Gallery, etc.) packaged as reusable plugins.

### Structure

```
plugins/
  tasks/                          # Plugin directory
    plugin.yaml                   # Plugin manifest
    views/                        # Vue components
      KanbanView.vue
      TaskListView.vue
      TodoListView.vue
    templates/                    # Template definitions
      task-board.yaml
      task-list.yaml
      todo-item.yaml
    examples/                     # Example files
      project-tasks.cdx
      daily-todos.cdx
    README.md                     # Plugin documentation
    LICENSE                       # Plugin license
```

### Plugin Manifest (`plugin.yaml`)

```yaml
# Plugin Metadata
id: tasks
name: Task Management Plugin
version: 1.0.0
author: Codex Team
description: Kanban boards, task lists, and todo management views
license: MIT
repository: https://github.com/codex/plugins/tasks

# Plugin Type
type: view

# Codex Compatibility
codex_version: ">=1.0.0"
api_version: 1

# Custom Properties
# Define custom frontmatter properties this plugin uses
properties:
  - name: status
    type: string
    description: Task status
    enum:
      - backlog
      - todo
      - in-progress
      - review
      - done
    default: todo
    required: false

  - name: priority
    type: string
    description: Task priority level
    enum:
      - low
      - medium
      - high
      - critical
    default: medium
    required: false

  - name: due_date
    type: date
    description: Task due date
    required: false

  - name: assignee
    type: string
    description: Person assigned to task
    required: false

  - name: estimated_hours
    type: number
    description: Estimated hours to complete
    required: false

# View Types
# Each view type provided by this plugin
views:
  - id: kanban
    name: Kanban Board
    component: KanbanView.vue
    description: Visual board with draggable cards organized in columns
    icon: 📊
    config_schema:
      columns:
        type: array
        description: Column definitions
        items:
          type: object
          properties:
            id: { type: string }
            title: { type: string }
            filter: { type: object }
      card_fields:
        type: array
        description: Fields to display on cards
        items: { type: string }
      drag_drop:
        type: boolean
        description: Enable drag and drop
        default: true
      editable:
        type: boolean
        description: Allow inline editing
        default: true

  - id: task-list
    name: Task List
    component: TaskListView.vue
    description: Simple checklist view with task completion
    icon: ✅
    config_schema:
      compact:
        type: boolean
        description: Compact display mode
        default: false
      show_details:
        type: boolean
        description: Show task details
        default: true
      editable:
        type: boolean
        description: Allow checkbox toggling
        default: true
      sort_by:
        type: string
        enum: [priority, due_date, created_at]
        default: created_at

  - id: todo-list
    name: Simple Todo List
    component: TodoListView.vue
    description: Minimal todo list for quick tasks
    icon: ☑️
    config_schema:
      show_completed:
        type: boolean
        default: false

# Templates
# Template files that can be instantiated
templates:
  - id: task-board
    name: Task Board
    file: templates/task-board.yaml
    description: Kanban board for managing tasks
    icon: 📋
    default_name: task-board.cdx

  - id: task-list
    name: Task List
    file: templates/task-list.yaml
    description: Simple task checklist
    icon: ✅
    default_name: tasks.cdx

  - id: todo-item
    name: Todo Item
    file: templates/todo-item.yaml
    description: Individual todo task
    icon: ☑️
    default_name: todo.md
    file_extension: .md

# Example Files
examples:
  - name: Project Tasks
    file: examples/project-tasks.cdx
    description: Example kanban board for a project

  - name: Daily Todos
    file: examples/daily-todos.cdx
    description: Example daily task list

# Dependencies
dependencies:
  vue: "^3.0.0"
  codex-ui: "^1.0.0"

# Permissions
# What capabilities this plugin needs
permissions:
  - read_files
  - write_files
  - modify_metadata
```

### Vue Component Interface

Each view component must implement a standard interface:

```typescript
// KanbanView.vue
import { defineComponent, PropType } from 'vue'

interface ViewConfig {
  columns: Column[]
  card_fields: string[]
  drag_drop: boolean
  editable: boolean
}

interface ViewDefinition {
  id: string
  title: string
  description?: string
  query: QueryConfig
  config: ViewConfig
}

export default defineComponent({
  name: 'KanbanView',
  
  props: {
    // View definition from .cdx file
    definition: {
      type: Object as PropType<ViewDefinition>,
      required: true
    },
    
    // Files matching the query
    files: {
      type: Array as PropType<FileMetadata[]>,
      required: true
    },
    
    // Whether view is embedded (mini-view)
    embedded: {
      type: Boolean,
      default: false
    }
  },
  
  emits: [
    'file-click',      // User clicked a file
    'file-update',     // User updated file metadata
    'refresh',         // Request data refresh
  ],
  
  setup(props, { emit }) {
    // Component implementation
  }
})
```

### Template Files

Template files define the structure of files created from the plugin:

```yaml
# templates/task-board.yaml
id: task-board
name: Task Board
description: Kanban board for managing tasks
icon: 📊
file_extension: .cdx
default_name: task-board.cdx

content: |
  ---
  type: view
  view_type: kanban
  title: Task Board
  description: Kanban board for managing tasks
  query:
    file_types:
      - todo
  config:
    columns:
      - {"id": "backlog", "title": "Backlog", "filter": {"status": "backlog"}}
      - {"id": "todo", "title": "To Do", "filter": {"status": "todo"}}
      - {"id": "in-progress", "title": "In Progress", "filter": {"status": "in-progress"}}
      - {"id": "done", "title": "Done", "filter": {"status": "done"}}
    card_fields:
      - description
      - priority
      - due_date
    drag_drop: true
    editable: true
  ---

  # Task Board

  This is a dynamic Kanban board view that displays files with type: todo.
  Edit the frontmatter above to customize columns and filters.
```

### Example Files

Example files demonstrate plugin usage:

```markdown
<!-- examples/project-tasks.cdx -->
---
type: view
view_type: kanban
title: Project Sprint Tasks
description: Current sprint task board
query:
  tags:
    - sprint
    - current
  properties:
    status: [backlog, todo, in-progress, review, done]
config:
  columns:
    - id: backlog
      title: Backlog
      filter: { status: backlog }
    - id: todo
      title: To Do  
      filter: { status: todo }
    - id: in-progress
      title: In Progress
      filter: { status: in-progress }
    - id: review
      title: Review
      filter: { status: review }
    - id: done
      title: Done
      filter: { status: done }
  card_fields:
    - description
    - priority
    - assignee
    - due_date
  drag_drop: true
  editable: true
---

# Project Sprint Tasks

This board tracks tasks for the current sprint. Drag cards between columns to update status.

## Quick Actions

- **Add Task**: Create a new .md file with `type: todo` frontmatter
- **Filter**: Use the sidebar to filter by tags
- **Search**: Use Cmd+K to search tasks
```

---

## Type 2: Themes

Themes provide visual styling and customization for the Codex interface.

### Structure

```
plugins/
  themes/
    dark-mode/                    # Theme directory
      theme.yaml                  # Theme manifest
      styles/
        main.css                  # Main theme styles
        components.css            # Component overrides
        syntax.css                # Code syntax highlighting
      assets/
        background.svg            # Optional assets
      preview.png                 # Theme preview image
      README.md
```

### Theme Manifest (`theme.yaml`)

```yaml
# Theme Metadata
id: dark-mode
name: Dark Mode
version: 1.0.0
author: Codex Team
description: Professional dark theme with blue accents
license: MIT

# Theme Type
type: theme

# Codex Compatibility
codex_version: ">=1.0.0"

# Theme Configuration
theme:
  # Base theme to extend (optional)
  extends: default
  
  # Display name shown in UI
  display_name: Dark Mode
  
  # Theme category
  category: dark
  
  # Preview image
  preview: preview.png
  
  # Main stylesheet
  stylesheet: styles/main.css
  
  # Additional stylesheets (loaded in order)
  additional_styles:
    - styles/components.css
    - styles/syntax.css
  
  # CSS class applied to root element
  className: theme-dark-mode

# Color Palette
# Define semantic color tokens
colors:
  # Background colors
  bg-primary: "#1a1a1a"
  bg-secondary: "#2d2d2d"
  bg-tertiary: "#3a3a3a"
  bg-hover: "#404040"
  bg-active: "#4a4a4a"
  
  # Text colors
  text-primary: "#e0e0e0"
  text-secondary: "#b0b0b0"
  text-tertiary: "#808080"
  text-inverse: "#1a1a1a"
  
  # Border colors
  border-light: "#404040"
  border-medium: "#555555"
  border-dark: "#666666"
  
  # Accent colors
  accent-primary: "#4a9eff"
  accent-secondary: "#7b68ee"
  
  # Semantic colors
  success: "#10b981"
  error: "#ef4444"
  warning: "#f59e0b"
  info: "#3b82f6"

# Typography
typography:
  font-sans: "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
  font-serif: "'Georgia', 'Times New Roman', serif"
  font-mono: "'Monaco', 'Courier New', monospace"
  
  # Font sizes
  font-size-xs: "0.75rem"
  font-size-sm: "0.875rem"
  font-size-base: "1rem"
  font-size-lg: "1.125rem"
  font-size-xl: "1.25rem"
  font-size-2xl: "1.5rem"

# Spacing
spacing:
  xs: "0.25rem"
  sm: "0.5rem"
  md: "1rem"
  lg: "1.5rem"
  xl: "2rem"

# Border Radius
radius:
  sm: "0.25rem"
  md: "0.375rem"
  lg: "0.5rem"
  xl: "0.75rem"

# Shadows
shadows:
  sm: "0 1px 2px 0 rgba(0, 0, 0, 0.3)"
  md: "0 4px 6px -1px rgba(0, 0, 0, 0.3)"
  lg: "0 10px 15px -3px rgba(0, 0, 0, 0.3)"
  xl: "0 20px 25px -5px rgba(0, 0, 0, 0.3)"

# Custom Properties
# Arbitrary CSS custom properties
custom_properties:
  --notebook-texture: "url('./assets/background.svg')"
  --notebook-opacity: "0.05"
```

### Theme CSS Structure

```css
/* styles/main.css */

/* Import theme configuration as CSS variables */
:root.theme-dark-mode {
  /* Background colors */
  --color-bg-primary: #1a1a1a;
  --color-bg-secondary: #2d2d2d;
  --color-bg-tertiary: #3a3a3a;
  --color-bg-hover: #404040;
  --color-bg-active: #4a4a4a;
  
  /* Text colors */
  --color-text-primary: #e0e0e0;
  --color-text-secondary: #b0b0b0;
  --color-text-tertiary: #808080;
  --color-text-inverse: #1a1a1a;
  
  /* Border colors */
  --color-border-light: #404040;
  --color-border-medium: #555555;
  --color-border-dark: #666666;
  
  /* Accent colors */
  --color-accent-primary: #4a9eff;
  --color-accent-secondary: #7b68ee;
  
  /* Semantic colors */
  --color-success: #10b981;
  --color-error: #ef4444;
  --color-warning: #f59e0b;
  --color-info: #3b82f6;
  
  /* Typography */
  --font-sans: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  --font-mono: 'Monaco', 'Courier New', monospace;
  
  /* Custom properties */
  --notebook-texture: url('./assets/background.svg');
  --notebook-opacity: 0.05;
}

/* Component-specific overrides */
.theme-dark-mode .workspace-sidebar {
  background: var(--color-bg-secondary);
  border-right: 1px solid var(--color-border-light);
}

.theme-dark-mode .notebook-page {
  background: var(--color-bg-primary);
  color: var(--color-text-primary);
}

.theme-dark-mode .markdown-body {
  color: var(--color-text-primary);
}

.theme-dark-mode .markdown-body h1,
.theme-dark-mode .markdown-body h2,
.theme-dark-mode .markdown-body h3 {
  color: var(--color-text-primary);
  border-bottom-color: var(--color-border-light);
}

.theme-dark-mode .markdown-body code {
  background: var(--color-bg-tertiary);
  color: var(--color-accent-primary);
}

.theme-dark-mode .markdown-body pre {
  background: var(--color-bg-tertiary);
  border: 1px solid var(--color-border-light);
}

.theme-dark-mode .btn-primary {
  background: var(--color-accent-primary);
  color: var(--color-text-inverse);
}

.theme-dark-mode .btn-primary:hover {
  background: var(--color-accent-secondary);
}
```

### Syntax Highlighting

```css
/* styles/syntax.css */

/* Code syntax highlighting for dark theme */
.theme-dark-mode .hljs {
  background: var(--color-bg-tertiary);
  color: var(--color-text-primary);
}

.theme-dark-mode .hljs-keyword {
  color: #ff79c6;
}

.theme-dark-mode .hljs-string {
  color: #50fa7b;
}

.theme-dark-mode .hljs-function {
  color: #8be9fd;
}

.theme-dark-mode .hljs-number {
  color: #bd93f9;
}

.theme-dark-mode .hljs-comment {
  color: #6272a4;
  font-style: italic;
}
```

---

## Type 3: Integrations

Integrations connect Codex to external APIs and services, enabling data import, export, and real-time synchronization.

### Structure

```
plugins/
  integrations/
    weather-api/                  # Integration directory
      integration.yaml            # Integration manifest
      settings.vue                # Settings UI component
      blocks/                     # Block renderers
        WeatherBlock.vue
      transforms/                 # Data transformers
        weather.ts
      README.md
```

### Integration Manifest (`integration.yaml`)

```yaml
# Integration Metadata
id: weather-api
name: Weather API Integration
version: 1.0.0
author: Codex Team
description: Display current weather and forecasts from OpenWeatherMap
license: MIT

# Integration Type
type: integration

# Codex Compatibility
codex_version: ">=1.0.0"
api_version: 1

# Integration Configuration
integration:
  # API type
  api_type: rest
  
  # Base URL (can use variables)
  base_url: "https://api.openweathermap.org/data/2.5"
  
  # Authentication method
  auth_method: api_key
  
  # Rate limiting
  rate_limit:
    requests_per_minute: 60
    requests_per_day: 1000

# Configuration Properties
# These are stored per-workspace in the database
properties:
  - name: api_key
    type: string
    description: OpenWeatherMap API key
    required: true
    secure: true  # Encrypted in database
    ui:
      type: password
      label: API Key
      help: Get your API key from openweathermap.org
      
  - name: default_location
    type: string
    description: Default location for weather queries
    required: false
    default: "San Francisco, US"
    ui:
      type: text
      label: Default Location
      placeholder: "City, Country"
      
  - name: units
    type: string
    description: Temperature units
    required: false
    default: imperial
    enum:
      - metric
      - imperial
      - kelvin
    ui:
      type: select
      label: Temperature Units
      options:
        - { value: metric, label: Celsius }
        - { value: imperial, label: Fahrenheit }
        - { value: kelvin, label: Kelvin }
      
  - name: update_interval
    type: number
    description: Update interval in minutes
    required: false
    default: 30
    min: 5
    max: 1440
    ui:
      type: number
      label: Update Interval (minutes)
      
  - name: show_forecast
    type: boolean
    description: Show 5-day forecast
    required: false
    default: true
    ui:
      type: checkbox
      label: Show Forecast

# Settings Component
# Vue component for custom settings UI
settings_component: settings.vue

# Block Types
# Custom block renderers for embedding in markdown
blocks:
  - id: weather
    name: Weather Block
    component: blocks/WeatherBlock.vue
    description: Display current weather for a location
    icon: ☀️
    syntax: "```weather\nlocation: San Francisco\n```"
    config_schema:
      location:
        type: string
        description: Location to display weather for
        required: false
      units:
        type: string
        enum: [metric, imperial, kelvin]
        required: false
      show_forecast:
        type: boolean
        default: false

# API Endpoints
# Define available API operations
endpoints:
  - id: current_weather
    name: Get Current Weather
    method: GET
    path: "/weather"
    description: Get current weather for a location
    parameters:
      - name: q
        type: string
        description: City name
        required: true
      - name: appid
        type: string
        description: API key
        required: true
        from_config: api_key
      - name: units
        type: string
        description: Units of measurement
        required: false
        from_config: units
    response_schema:
      type: object
      properties:
        main:
          type: object
          properties:
            temp: { type: number }
            feels_like: { type: number }
            humidity: { type: number }
        weather:
          type: array
          items:
            type: object
            properties:
              description: { type: string }
              icon: { type: string }
              
  - id: forecast
    name: Get 5-Day Forecast
    method: GET
    path: "/forecast"
    description: Get 5-day weather forecast
    parameters:
      - name: q
        type: string
        description: City name
        required: true
      - name: appid
        type: string
        from_config: api_key
      - name: units
        type: string
        from_config: units

# Data Transformers
# Transform API responses for display
transformers:
  - id: weather_data
    input: current_weather
    output: weather_display
    transform: transforms/weather.ts

# Triggers
# When to fetch data
triggers:
  - type: on_block_render
    blocks: [weather]
  - type: on_interval
    interval: 30  # minutes
    condition: has_config
  - type: on_command
    command: refresh_weather

# Permissions
permissions:
  - network_request
  - store_config
  - render_blocks
```

### Settings Component

```vue
<!-- settings.vue -->
<template>
  <div class="integration-settings">
    <h3>Weather API Settings</h3>
    
    <form @submit.prevent="handleSave">
      <!-- API Key -->
      <div class="form-group">
        <label for="api_key">API Key *</label>
        <input
          id="api_key"
          v-model="config.api_key"
          type="password"
          placeholder="Enter your OpenWeatherMap API key"
          required
        />
        <small>Get your API key from <a href="https://openweathermap.org" target="_blank">openweathermap.org</a></small>
      </div>
      
      <!-- Default Location -->
      <div class="form-group">
        <label for="default_location">Default Location</label>
        <input
          id="default_location"
          v-model="config.default_location"
          type="text"
          placeholder="San Francisco, US"
        />
      </div>
      
      <!-- Units -->
      <div class="form-group">
        <label for="units">Temperature Units</label>
        <select id="units" v-model="config.units">
          <option value="metric">Celsius</option>
          <option value="imperial">Fahrenheit</option>
          <option value="kelvin">Kelvin</option>
        </select>
      </div>
      
      <!-- Update Interval -->
      <div class="form-group">
        <label for="update_interval">Update Interval (minutes)</label>
        <input
          id="update_interval"
          v-model.number="config.update_interval"
          type="number"
          min="5"
          max="1440"
        />
      </div>
      
      <!-- Show Forecast -->
      <div class="form-group">
        <label>
          <input
            v-model="config.show_forecast"
            type="checkbox"
          />
          Show 5-day forecast
        </label>
      </div>
      
      <!-- Test Connection -->
      <div class="form-actions">
        <button type="button" @click="handleTest" :disabled="testing">
          {{ testing ? 'Testing...' : 'Test Connection' }}
        </button>
        <button type="submit" :disabled="saving">
          {{ saving ? 'Saving...' : 'Save Settings' }}
        </button>
      </div>
      
      <div v-if="testResult" class="test-result" :class="testResult.success ? 'success' : 'error'">
        {{ testResult.message }}
      </div>
    </form>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { integrationService } from '../services/integration'

const config = ref({
  api_key: '',
  default_location: 'San Francisco, US',
  units: 'imperial',
  update_interval: 30,
  show_forecast: true
})

const saving = ref(false)
const testing = ref(false)
const testResult = ref<{ success: boolean; message: string } | null>(null)

onMounted(async () => {
  // Load existing configuration
  const existing = await integrationService.getConfig('weather-api')
  if (existing) {
    config.value = existing
  }
})

async function handleTest() {
  testing.value = true
  testResult.value = null
  
  try {
    const result = await integrationService.testConnection('weather-api', config.value)
    testResult.value = {
      success: result.success,
      message: result.message || 'Connection successful!'
    }
  } catch (error) {
    testResult.value = {
      success: false,
      message: error.message || 'Connection failed'
    }
  } finally {
    testing.value = false
  }
}

async function handleSave() {
  saving.value = true
  
  try {
    await integrationService.saveConfig('weather-api', config.value)
    testResult.value = {
      success: true,
      message: 'Settings saved successfully!'
    }
  } catch (error) {
    testResult.value = {
      success: false,
      message: error.message || 'Failed to save settings'
    }
  } finally {
    saving.value = false
  }
}
</script>
```

### Weather Block Component

```vue
<!-- blocks/WeatherBlock.vue -->
<template>
  <div class="weather-block" :class="{ loading: isLoading }">
    <div v-if="error" class="weather-error">
      <p>⚠️ {{ error }}</p>
    </div>
    
    <div v-else-if="weather" class="weather-content">
      <!-- Current Weather -->
      <div class="current-weather">
        <div class="weather-icon">
          <img :src="`http://openweathermap.org/img/wn/${weather.icon}@2x.png`" :alt="weather.description" />
        </div>
        <div class="weather-info">
          <div class="location">{{ location }}</div>
          <div class="temperature">{{ weather.temperature }}°</div>
          <div class="description">{{ weather.description }}</div>
        </div>
        <div class="weather-details">
          <div class="detail">
            <span class="label">Feels Like:</span>
            <span class="value">{{ weather.feels_like }}°</span>
          </div>
          <div class="detail">
            <span class="label">Humidity:</span>
            <span class="value">{{ weather.humidity }}%</span>
          </div>
          <div class="detail">
            <span class="label">Wind:</span>
            <span class="value">{{ weather.wind_speed }} {{ units === 'imperial' ? 'mph' : 'm/s' }}</span>
          </div>
        </div>
      </div>
      
      <!-- 5-Day Forecast -->
      <div v-if="showForecast && forecast" class="weather-forecast">
        <h4>5-Day Forecast</h4>
        <div class="forecast-days">
          <div v-for="day in forecast" :key="day.date" class="forecast-day">
            <div class="day-name">{{ day.day_name }}</div>
            <img :src="`http://openweathermap.org/img/wn/${day.icon}.png`" :alt="day.description" />
            <div class="day-temp">
              <span class="high">{{ day.temp_high }}°</span>
              <span class="low">{{ day.temp_low }}°</span>
            </div>
          </div>
        </div>
      </div>
      
      <div class="weather-footer">
        <small>Last updated: {{ lastUpdated }}</small>
        <button @click="refresh" class="refresh-btn">↻</button>
      </div>
    </div>
    
    <div v-else class="weather-loading">
      <p>Loading weather data...</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { integrationService } from '../services/integration'

const props = defineProps<{
  config: {
    location?: string
    units?: string
    show_forecast?: boolean
  }
}>()

const isLoading = ref(true)
const error = ref<string | null>(null)
const weather = ref<any>(null)
const forecast = ref<any[] | null>(null)
const lastUpdated = ref<string>('')

const location = computed(() => props.config.location || 'Default Location')
const units = computed(() => props.config.units || 'imperial')
const showForecast = computed(() => props.config.show_forecast !== false)

async function fetchWeather() {
  isLoading.value = true
  error.value = null
  
  try {
    const result = await integrationService.execute('weather-api', 'current_weather', {
      q: location.value
    })
    
    weather.value = {
      temperature: Math.round(result.main.temp),
      feels_like: Math.round(result.main.feels_like),
      humidity: result.main.humidity,
      wind_speed: Math.round(result.wind.speed),
      description: result.weather[0].description,
      icon: result.weather[0].icon
    }
    
    if (showForecast.value) {
      const forecastResult = await integrationService.execute('weather-api', 'forecast', {
        q: location.value
      })
      forecast.value = transformForecast(forecastResult)
    }
    
    lastUpdated.value = new Date().toLocaleTimeString()
  } catch (err) {
    error.value = err.message || 'Failed to fetch weather data'
  } finally {
    isLoading.value = false
  }
}

function transformForecast(data: any) {
  // Transform API response to daily forecast
  // Group by day and aggregate
  const dailyData = {}
  
  data.list.forEach(item => {
    const date = new Date(item.dt * 1000)
    const dayKey = date.toDateString()
    
    if (!dailyData[dayKey]) {
      dailyData[dayKey] = {
        date: dayKey,
        day_name: date.toLocaleDateString('en-US', { weekday: 'short' }),
        temps: [],
        icon: item.weather[0].icon,
        description: item.weather[0].description
      }
    }
    
    dailyData[dayKey].temps.push(item.main.temp)
  })
  
  return Object.values(dailyData).slice(0, 5).map(day => ({
    ...day,
    temp_high: Math.round(Math.max(...day.temps)),
    temp_low: Math.round(Math.min(...day.temps))
  }))
}

function refresh() {
  fetchWeather()
}

onMounted(() => {
  fetchWeather()
})
</script>

<style scoped>
.weather-block {
  padding: 1rem;
  border: 1px solid var(--color-border-light);
  border-radius: 0.5rem;
  background: var(--color-bg-primary);
}

.current-weather {
  display: flex;
  gap: 1rem;
  align-items: center;
}

.weather-icon img {
  width: 80px;
  height: 80px;
}

.temperature {
  font-size: 2.5rem;
  font-weight: bold;
}

.forecast-days {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 1rem;
  margin-top: 1rem;
}

.forecast-day {
  text-align: center;
  padding: 0.5rem;
  border: 1px solid var(--color-border-light);
  border-radius: 0.25rem;
}

.weather-footer {
  margin-top: 1rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.875rem;
  color: var(--color-text-secondary);
}

.refresh-btn {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 1.25rem;
}
</style>
```

### Additional Integration Examples

#### Open Graph Unfurling

```yaml
# integrations/opengraph/integration.yaml
id: opengraph-unfurl
name: Open Graph Link Unfurling
version: 1.0.0
type: integration

integration:
  api_type: rest
  auth_method: none

blocks:
  - id: link-preview
    name: Link Preview
    component: blocks/LinkPreviewBlock.vue
    description: Rich preview of any URL with Open Graph metadata
    auto_detect: true  # Automatically render for URLs
    url_patterns:
      - "https?://.*"
    config_schema:
      url:
        type: string
        required: true

endpoints:
  - id: fetch_metadata
    method: GET
    description: Fetch Open Graph metadata for a URL
    parameters:
      - name: url
        type: string
        required: true
```

#### GitHub Integration

```yaml
# integrations/github/integration.yaml
id: github
name: GitHub Integration
version: 1.0.0
type: integration

integration:
  api_type: rest
  base_url: "https://api.github.com"
  auth_method: token

properties:
  - name: access_token
    type: string
    description: GitHub personal access token
    required: true
    secure: true
    
  - name: default_org
    type: string
    description: Default GitHub organization

blocks:
  - id: github-issue
    name: GitHub Issue
    component: blocks/GithubIssueBlock.vue
    url_patterns:
      - "https://github.com/.*/issues/.*"
    config_schema:
      url:
        type: string
        required: true
        
  - id: github-pr
    name: GitHub Pull Request
    component: blocks/GithubPRBlock.vue
    url_patterns:
      - "https://github.com/.*/pull/.*"
      
  - id: github-repo
    name: GitHub Repository
    component: blocks/GithubRepoBlock.vue
    url_patterns:
      - "https://github.com/[^/]+/[^/]+"

endpoints:
  - id: get_issue
    method: GET
    path: "/repos/{owner}/{repo}/issues/{issue_number}"
    
  - id: get_pr
    method: GET
    path: "/repos/{owner}/{repo}/pulls/{pull_number}"
    
  - id: get_repo
    method: GET
    path: "/repos/{owner}/{repo}"
```

#### GraphQL Playground

```yaml
# integrations/graphql/integration.yaml
id: graphql-playground
name: GraphQL Playground
version: 1.0.0
type: integration

integration:
  api_type: graphql

blocks:
  - id: graphql-query
    name: GraphQL Query
    component: blocks/GraphQLBlock.vue
    description: Execute GraphQL queries and display results
    syntax: "```graphql\nendpoint: https://api.example.com/graphql\nquery: |\n  { users { id name } }\n```"
    config_schema:
      endpoint:
        type: string
        required: true
      query:
        type: string
        required: true
      variables:
        type: object
        required: false
      headers:
        type: object
        required: false
```

---

## Plugin Management

### Database Schema

Extend the system database to store plugin data:

```sql
-- Plugin registry
CREATE TABLE plugins (
    id INTEGER PRIMARY KEY,
    plugin_id TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    version TEXT NOT NULL,
    type TEXT NOT NULL,  -- 'view', 'theme', 'integration'
    enabled BOOLEAN DEFAULT 1,
    installed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    metadata JSON  -- Full plugin manifest
);

-- Plugin configurations per workspace
CREATE TABLE plugin_configs (
    id INTEGER PRIMARY KEY,
    workspace_id INTEGER NOT NULL,
    plugin_id TEXT NOT NULL,
    config JSON,  -- Plugin-specific configuration
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (workspace_id) REFERENCES workspaces(id),
    FOREIGN KEY (plugin_id) REFERENCES plugins(plugin_id),
    UNIQUE(workspace_id, plugin_id)
);

-- Secure plugin secrets (encrypted)
CREATE TABLE plugin_secrets (
    id INTEGER PRIMARY KEY,
    workspace_id INTEGER NOT NULL,
    plugin_id TEXT NOT NULL,
    key TEXT NOT NULL,
    encrypted_value TEXT NOT NULL,  -- AES encrypted
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (workspace_id) REFERENCES workspaces(id),
    FOREIGN KEY (plugin_id) REFERENCES plugins(plugin_id),
    UNIQUE(workspace_id, plugin_id, key)
);

-- Plugin API request logs (for rate limiting and debugging)
CREATE TABLE plugin_api_logs (
    id INTEGER PRIMARY KEY,
    workspace_id INTEGER NOT NULL,
    plugin_id TEXT NOT NULL,
    endpoint_id TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    status_code INTEGER,
    error TEXT,
    FOREIGN KEY (workspace_id) REFERENCES workspaces(id),
    FOREIGN KEY (plugin_id) REFERENCES plugins(plugin_id)
);

CREATE INDEX idx_plugin_api_logs_timestamp ON plugin_api_logs(timestamp);
CREATE INDEX idx_plugin_api_logs_workspace_plugin ON plugin_api_logs(workspace_id, plugin_id);
```

### API Endpoints

```
POST   /api/v1/plugins/install         - Install a plugin
DELETE /api/v1/plugins/{id}/uninstall  - Uninstall a plugin
GET    /api/v1/plugins                 - List installed plugins
GET    /api/v1/plugins/{id}            - Get plugin details
PUT    /api/v1/plugins/{id}/enable     - Enable plugin
PUT    /api/v1/plugins/{id}/disable    - Disable plugin

# Plugin configurations
GET    /api/v1/plugins/{id}/config     - Get plugin configuration
PUT    /api/v1/plugins/{id}/config     - Update plugin configuration
POST   /api/v1/plugins/{id}/test       - Test plugin connection

# Plugin execution (for integrations)
POST   /api/v1/plugins/{id}/execute    - Execute integration endpoint
GET    /api/v1/plugins/{id}/blocks     - List available blocks
```

### Plugin Loader

```python
# backend/codex/plugins/loader.py
from pathlib import Path
from typing import Dict, List
import yaml

class PluginLoader:
    """Load and manage plugins."""
    
    def __init__(self, plugins_dir: Path):
        self.plugins_dir = plugins_dir
        self.plugins: Dict[str, Plugin] = {}
        
    def discover_plugins(self) -> List[str]:
        """Discover all available plugins."""
        plugins = []
        
        for plugin_type in ['views', 'themes', 'integrations']:
            type_dir = self.plugins_dir / plugin_type
            if not type_dir.exists():
                continue
                
            for plugin_dir in type_dir.iterdir():
                if not plugin_dir.is_dir():
                    continue
                    
                manifest_path = plugin_dir / self._get_manifest_name(plugin_type)
                if manifest_path.exists():
                    plugins.append(str(plugin_dir))
                    
        return plugins
    
    def load_plugin(self, plugin_path: str) -> Plugin:
        """Load a plugin from a directory."""
        plugin_dir = Path(plugin_path)
        
        # Determine plugin type and load manifest
        manifest_files = {
            'plugin.yaml': 'view',
            'theme.yaml': 'theme',
            'integration.yaml': 'integration'
        }
        
        plugin_type = None
        manifest_data = None
        
        for manifest_file, ptype in manifest_files.items():
            manifest_path = plugin_dir / manifest_file
            if manifest_path.exists():
                with open(manifest_path) as f:
                    manifest_data = yaml.safe_load(f)
                plugin_type = ptype
                break
        
        if not manifest_data:
            raise ValueError(f"No valid manifest found in {plugin_dir}")
        
        # Validate manifest
        self._validate_manifest(manifest_data, plugin_type)
        
        # Create plugin instance
        if plugin_type == 'view':
            return ViewPlugin(plugin_dir, manifest_data)
        elif plugin_type == 'theme':
            return ThemePlugin(plugin_dir, manifest_data)
        elif plugin_type == 'integration':
            return IntegrationPlugin(plugin_dir, manifest_data)
        else:
            raise ValueError(f"Unknown plugin type: {plugin_type}")
    
    def _validate_manifest(self, manifest: dict, plugin_type: str):
        """Validate plugin manifest."""
        required_fields = ['id', 'name', 'version', 'type']
        
        for field in required_fields:
            if field not in manifest:
                raise ValueError(f"Missing required field: {field}")
        
        if manifest['type'] != plugin_type:
            raise ValueError(f"Plugin type mismatch: {manifest['type']} != {plugin_type}")
    
    def _get_manifest_name(self, plugin_type: str) -> str:
        """Get manifest filename for plugin type."""
        return {
            'views': 'plugin.yaml',
            'themes': 'theme.yaml',
            'integrations': 'integration.yaml'
        }[plugin_type]
```

---

## Plugin Installation

### Installation Methods

1. **Built-in Plugins**: Pre-installed with Codex
2. **Plugin Directory**: Copy plugin folder to `~/.codex/plugins/`
3. **Git Repository**: Clone from Git URL
4. **Plugin Marketplace**: Future - centralized plugin repository

### Installation Flow

```
1. User initiates plugin installation
   ↓
2. Download/copy plugin files
   ↓
3. Validate plugin manifest
   ↓
4. Check Codex version compatibility
   ↓
5. Install dependencies (if any)
   ↓
6. Register plugin in database
   ↓
7. Enable plugin (if auto-enable)
   ↓
8. Show configuration UI (if needed)
```

### Security Considerations

1. **Code Signing**: Verify plugin authenticity
2. **Sandboxing**: Limit plugin access to filesystem and network
3. **Permissions**: Explicit permission grants for sensitive operations
4. **Secret Storage**: Encrypt API keys and tokens
5. **Rate Limiting**: Prevent API abuse
6. **Input Validation**: Sanitize user inputs in plugin configurations

---

## Implementation Roadmap

### Phase 1: Foundation (v1.0)

- [ ] Plugin database schema
- [ ] Plugin loader and registry
- [ ] Basic plugin management API
- [ ] Plugin installation UI
- [ ] Convert existing views to plugin format

### Phase 2: View Plugins (v1.1)

- [ ] View plugin specification
- [ ] Template system
- [ ] Example plugin: Tasks
- [ ] Example plugin: Gallery
- [ ] Plugin marketplace UI (browse/install)

### Phase 3: Theme Plugins (v1.2)

- [ ] Theme plugin specification
- [ ] CSS injection system
- [ ] Theme preview and switching
- [ ] Example theme: Dark Mode
- [ ] Example theme: Solarized

### Phase 4: Integration Plugins (v1.3)

- [ ] Integration plugin specification
- [ ] API client framework
- [ ] Settings UI framework
- [ ] Block renderer system
- [ ] Example integration: Weather API
- [ ] Example integration: Open Graph unfurling

### Phase 5: Advanced Features (v2.0)

- [ ] Plugin dependencies
- [ ] Plugin hooks and events
- [ ] Plugin communication
- [ ] Plugin marketplace
- [ ] Auto-update system
- [ ] Plugin analytics

---

## References

### Inspiration

- **Obsidian**: Plugin architecture, theme system
- **VS Code**: Extension marketplace, activation events
- **WordPress**: Plugin hooks, settings API
- **Figma**: Plugin sandboxing, permissions

### Related Documents

- [Dynamic Views Design](/docs/design/dynamic-views.md)
- [Markdown Extensions](/docs/MARKDOWN_EXTENSIONS.md)
- [API Documentation](/docs/api.md) (to be created)

### External Resources

- [Obsidian Plugin Developer Docs](https://docs.obsidian.md/Plugins/)
- [VS Code Extension API](https://code.visualstudio.com/api)
- [Open Graph Protocol](https://ogp.me/)
- [GraphQL Specification](https://graphql.org/learn/)

---

## Appendix

### Plugin Directory Structure Example

```
~/.codex/
  plugins/
    views/
      tasks/
        plugin.yaml
        views/
          KanbanView.vue
          TaskListView.vue
        templates/
          task-board.yaml
        examples/
          project-tasks.cdx
        README.md
      calendar/
        plugin.yaml
        views/
          CalendarView.vue
        templates/
          calendar.yaml
        
    themes/
      dark-mode/
        theme.yaml
        styles/
          main.css
        preview.png
      solarized/
        theme.yaml
        styles/
          main.css
        
    integrations/
      weather-api/
        integration.yaml
        settings.vue
        blocks/
          WeatherBlock.vue
        transforms/
          weather.ts
      github/
        integration.yaml
        settings.vue
        blocks/
          GithubIssueBlock.vue
          GithubPRBlock.vue
          GithubRepoBlock.vue
```

### Plugin Manifest JSON Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Codex Plugin Manifest",
  "type": "object",
  "required": ["id", "name", "version", "type"],
  "properties": {
    "id": {
      "type": "string",
      "pattern": "^[a-z0-9-]+$",
      "description": "Unique plugin identifier"
    },
    "name": {
      "type": "string",
      "description": "Human-readable plugin name"
    },
    "version": {
      "type": "string",
      "pattern": "^\\d+\\.\\d+\\.\\d+$",
      "description": "Semantic version"
    },
    "type": {
      "type": "string",
      "enum": ["view", "theme", "integration"],
      "description": "Plugin type"
    },
    "codex_version": {
      "type": "string",
      "description": "Compatible Codex version range"
    },
    "api_version": {
      "type": "integer",
      "description": "Plugin API version"
    }
  }
}
```

---

**Document Status**: Draft for Review  
**Next Steps**: Review with team, gather feedback, begin Phase 1 implementation  
**Questions/Feedback**: Create an issue or discussion in the repository
