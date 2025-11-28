import type { Notebook, Page, Entry, Artifact } from '@/types'

const API_BASE = '/api'

async function fetchJSON<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${url}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers
    }
  })

  if (!response.ok) {
    throw new Error(`API Error: ${response.status} ${response.statusText}`)
  }

  return response.json()
}

export const notebooksApi = {
  list: (workspacePath: string) =>
    fetchJSON<Notebook[]>(`/notebooks?workspace_path=${encodeURIComponent(workspacePath)}`),

  get: (workspacePath: string, notebookId: string) =>
    fetchJSON<Notebook>(`/notebooks/${notebookId}?workspace_path=${encodeURIComponent(workspacePath)}`),

  create: (workspacePath: string, data: { title: string; description?: string; tags?: string[] }) =>
    fetchJSON<Notebook>('/notebooks', {
      method: 'POST',
      body: JSON.stringify({ workspace_path: workspacePath, ...data })
    })
}

export const pagesApi = {
  list: (workspacePath: string, notebookId: string) =>
    fetchJSON<Page[]>(`/notebooks/${notebookId}/pages?workspace_path=${encodeURIComponent(workspacePath)}`),

  get: (workspacePath: string, pageId: string) =>
    fetchJSON<Page>(`/pages/${pageId}?workspace_path=${encodeURIComponent(workspacePath)}`),

  create: (workspacePath: string, notebookId: string, data: { title: string; date?: string; narrative?: Record<string, string> }) =>
    fetchJSON<Page>(`/notebooks/${notebookId}/pages`, {
      method: 'POST',
      body: JSON.stringify({ workspace_path: workspacePath, ...data })
    })
}

export const entriesApi = {
  list: (workspacePath: string, pageId: string) =>
    fetchJSON<Entry[]>(`/pages/${pageId}/entries?workspace_path=${encodeURIComponent(workspacePath)}`),

  get: (workspacePath: string, entryId: string) =>
    fetchJSON<Entry>(`/entries/${entryId}?workspace_path=${encodeURIComponent(workspacePath)}`),

  create: (workspacePath: string, pageId: string, data: { entry_type: string; title: string; inputs: Record<string, unknown>; tags?: string[] }) =>
    fetchJSON<Entry>(`/pages/${pageId}/entries`, {
      method: 'POST',
      body: JSON.stringify({ workspace_path: workspacePath, ...data })
    }),

  execute: (workspacePath: string, entryId: string) =>
    fetchJSON<Entry>(`/entries/${entryId}/execute`, {
      method: 'POST',
      body: JSON.stringify({ workspace_path: workspacePath })
    }),

  getLineage: (workspacePath: string, entryId: string, depth = 3) =>
    fetchJSON<{ ancestors: Entry[]; descendants: Entry[]; entry: Entry }>(
      `/entries/${entryId}/lineage?workspace_path=${encodeURIComponent(workspacePath)}&depth=${depth}`
    )
}

export const artifactsApi = {
  getUrl: (workspacePath: string, artifactHash: string, thumbnail = false) =>
    `${API_BASE}/artifacts/${artifactHash}?workspace_path=${encodeURIComponent(workspacePath)}${thumbnail ? '&thumbnail=true' : ''}`
}

export const searchApi = {
  search: (workspacePath: string, params: { query?: string; entry_type?: string; tags?: string[] }) =>
    fetchJSON<{ results: Entry[]; count: number }>('/search', {
      method: 'POST',
      body: JSON.stringify({ workspace_path: workspacePath, ...params })
    })
}
