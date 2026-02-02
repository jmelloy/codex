/**
 * Shared types for Codex view plugins
 * These types are used by view components and match the frontend service types.
 */

// File metadata from the Codex API
export interface FileMetadata {
  id: number
  notebook_id: number
  path: string
  filename: string
  content_type: string // MIME type (e.g., text/markdown, image/jpeg)
  size: number
  title?: string
  description?: string
  properties?: Record<string, any> // Unified properties from frontmatter
  created_at: string
  updated_at: string
}

// Query result from the query service
export interface QueryResult {
  files: FileMetadata[]
  groups?: Record<string, FileMetadata[]>
  total: number
  limit: number
  offset: number
}

// View definition parsed from .cdx files
export interface ViewDefinition {
  type: "view"
  view_type: string
  title: string
  description?: string
  query?: ViewQuery
  config?: ViewConfig
  layout?: DashboardRow[]
  content?: string
}

export interface ViewQuery {
  notebook_ids?: number[]
  paths?: string[]
  tags?: string[]
  tags_any?: string[]
  content_types?: string[]
  properties?: Record<string, any>
  properties_exists?: string[]
  created_after?: string
  created_before?: string
  modified_after?: string
  modified_before?: string
  date_property?: string
  date_after?: string
  date_before?: string
  content_search?: string
  sort?: string
  limit?: number
  offset?: number
  group_by?: string
}

// Config types for different view types
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

export interface DashboardRow {
  type: "row"
  components: Array<{
    type: "mini-view"
    span: number
    view: string
  }>
}

export type ViewConfig =
  | KanbanConfig
  | GalleryConfig
  | RollupConfig
  | TaskListConfig
  | CorkboardConfig
  | Record<string, any>
