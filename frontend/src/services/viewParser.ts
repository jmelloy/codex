/**
 * View parser service for parsing .cdx dynamic view definitions
 */

import * as yaml from "js-yaml"
import { viewPluginService } from "./viewPluginService"

export interface ViewQuery {
  // Scope
  notebook_ids?: number[]
  paths?: string[]

  // Filtering
  tags?: string[]
  tags_any?: string[]
  content_types?: string[] // MIME types

  // Property filtering
  properties?: Record<string, any>
  properties_exists?: string[]

  // Date filtering
  created_after?: string
  created_before?: string
  modified_after?: string
  modified_before?: string

  // Date properties
  date_property?: string
  date_after?: string
  date_before?: string

  // Content filtering
  content_search?: string

  // Sorting & pagination
  sort?: string
  limit?: number
  offset?: number

  // Aggregation
  group_by?: string
}

export interface KanbanColumn {
  id: string
  title: string
  filter?: Record<string, any>
}

export interface KanbanConfig {
  columns: KanbanColumn[]
  card_fields?: string[]
  drag_drop?: boolean
  editable?: boolean
}

export interface GalleryConfig {
  layout?: "grid" | "masonry"
  columns?: number
  thumbnail_size?: number
  show_metadata?: boolean
  lightbox?: boolean
}

export interface RollupConfig {
  group_by: string
  group_format?: "day" | "week" | "month"
  show_stats?: boolean
  sections?: Array<{
    title: string
    filter?: Record<string, any>
  }>
}

export interface DashboardRow {
  type: "row"
  components: Array<{
    type: "mini-view"
    span: number
    view: string
  }>
}

export interface TaskListConfig {
  compact?: boolean
  show_details?: boolean
  max_items?: number
  editable?: boolean
}

export interface CorkboardConfig {
  group_by?: string
  card_style?: "notecard" | "sticky"
  layout?: "freeform" | "swimlanes"
  draggable?: boolean
  editable?: boolean
  card_fields?: string[]
}

export type ViewConfig =
  | KanbanConfig
  | GalleryConfig
  | RollupConfig
  | TaskListConfig
  | CorkboardConfig
  | Record<string, any>

export interface ViewDefinition {
  type: "view"
  view_type: string
  title: string
  description?: string
  query?: ViewQuery
  config?: ViewConfig
  layout?: DashboardRow[]
  content?: string // Markdown content after frontmatter
}

/**
 * Parse a .cdx file content into a ViewDefinition
 */
export function parseViewDefinition(content: string): ViewDefinition {
  // Extract frontmatter and content
  const frontmatterMatch = content.match(/^---\n([\s\S]*?)\n---\n?([\s\S]*)$/)

  if (!frontmatterMatch) {
    throw new Error("Invalid view definition: missing frontmatter")
  }

  const [, frontmatterText, markdownContent] = frontmatterMatch

  // Parse YAML frontmatter
  let data: any
  try {
    data = yaml.load(frontmatterText as string) as any
  } catch (error) {
    throw new Error(`Failed to parse YAML frontmatter: ${error}`)
  }

  // Validate required fields
  if (data.type !== "view") {
    throw new Error('Not a valid view definition: type must be "view"')
  }

  if (!data.view_type) {
    throw new Error("Not a valid view definition: view_type is required")
  }

  // Process template variables in query
  const query = data.query ? processQueryTemplates(data.query) : undefined

  return {
    type: data.type,
    view_type: data.view_type,
    title: data.title || "Untitled View",
    description: data.description,
    query,
    config: data.config || {},
    layout: data.layout,
    content: markdownContent?.trim() || undefined,
  }
}

/**
 * Process template variables in query
 * Supports: {{ today }}, {{ startOfWeek }}, {{ endOfWeek }}, etc.
 */
function processQueryTemplates(query: ViewQuery): ViewQuery {
  const templateValues = getTemplateValues()

  const processValue = (value: any): any => {
    if (typeof value === "string") {
      // Replace template variables
      return value.replace(/\{\{\s*(\w+)\s*\}\}/g, (match, key) => {
        return templateValues[key] || match
      })
    } else if (Array.isArray(value)) {
      return value.map(processValue)
    } else if (typeof value === "object" && value !== null) {
      const result: any = {}
      for (const [k, v] of Object.entries(value)) {
        result[k] = processValue(v)
      }
      return result
    }
    return value
  }

  return processValue(query)
}

/**
 * Get template variable values
 */
function getTemplateValues(): Record<string, string> {
  const now = new Date()

  // Get start of week (Sunday)
  const startOfWeek = new Date(now)
  startOfWeek.setDate(now.getDate() - now.getDay())
  startOfWeek.setHours(0, 0, 0, 0)

  // Get end of week (Saturday)
  const endOfWeek = new Date(startOfWeek)
  endOfWeek.setDate(startOfWeek.getDate() + 6)
  endOfWeek.setHours(23, 59, 59, 999)

  // Get start of month
  const startOfMonth = new Date(now.getFullYear(), now.getMonth(), 1)

  // Get end of month
  const endOfMonth = new Date(now.getFullYear(), now.getMonth() + 1, 0)
  endOfMonth.setHours(23, 59, 59, 999)

  // Get today start/end
  const todayStart = new Date(now)
  todayStart.setHours(0, 0, 0, 0)

  const todayEnd = new Date(now)
  todayEnd.setHours(23, 59, 59, 999)

  return {
    today: now.toISOString(),
    todayStart: todayStart.toISOString(),
    todayEnd: todayEnd.toISOString(),
    startOfWeek: startOfWeek.toISOString(),
    endOfWeek: endOfWeek.toISOString(),
    startOfMonth: startOfMonth.toISOString(),
    endOfMonth: endOfMonth.toISOString(),
    now: now.toISOString(),
  }
}

/**
 * Validate a view definition
 */
export function validateViewDefinition(viewDef: ViewDefinition): {
  valid: boolean
  errors: string[]
} {
  const errors: string[] = []

  // Check required fields
  if (viewDef.type !== "view") {
    errors.push('View definition must have type="view"')
  }

  if (!viewDef.view_type) {
    errors.push("View definition must have view_type")
  }

  // Check valid view types from plugin system
  const validViewTypes = viewPluginService.getValidViewTypes()
  if (validViewTypes.length === 0) {
    // Fallback to hardcoded list if plugin service not initialized
    const fallbackViewTypes = [
      "kanban",
      "gallery",
      "rollup",
      "dashboard",
      "corkboard",
      "calendar",
      "task-list",
    ]
    if (viewDef.view_type && !fallbackViewTypes.includes(viewDef.view_type)) {
      errors.push(`view_type must be one of: ${fallbackViewTypes.join(", ")}`)
    }
  } else {
    if (viewDef.view_type && !validViewTypes.includes(viewDef.view_type)) {
      errors.push(`view_type must be one of: ${validViewTypes.join(", ")}`)
    }
  }

  // View-specific validation
  if (viewDef.view_type === "kanban" && viewDef.config) {
    const config = viewDef.config as KanbanConfig
    if (!config.columns || !Array.isArray(config.columns)) {
      errors.push("Kanban view requires columns array in config")
    }
  }

  if (viewDef.view_type === "dashboard" && !viewDef.layout) {
    errors.push("Dashboard view requires layout field")
  }

  return {
    valid: errors.length === 0,
    errors,
  }
}
