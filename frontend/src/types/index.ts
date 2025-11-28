export interface Notebook {
  id: string
  title: string
  description: string
  created_at: string
  updated_at: string
  tags: string[]
  settings: Record<string, unknown>
}

export interface Page {
  id: string
  notebook_id: string
  title: string
  date: string | null
  created_at: string
  updated_at: string
  narrative: {
    goals?: string
    hypothesis?: string
    observations?: string
    conclusions?: string
    next_steps?: string
  }
  tags: string[]
}

export interface Entry {
  id: string
  page_id: string
  entry_type: string
  title: string
  created_at: string
  status: 'created' | 'running' | 'completed' | 'failed'
  parent_id: string | null
  inputs: Record<string, unknown>
  outputs: Record<string, unknown>
  execution: {
    started_at?: string
    completed_at?: string
    duration_seconds?: number
    status?: string
    error?: string
  }
  metrics: Record<string, unknown>
  metadata: {
    tags?: string[]
    notes?: string
    rating?: number | null
    archived?: boolean
  }
}

export interface Artifact {
  id: string
  entry_id: string
  type: string
  hash: string
  size_bytes: number
  path: string
  thumbnail_path?: string
  metadata: Record<string, unknown>
}
