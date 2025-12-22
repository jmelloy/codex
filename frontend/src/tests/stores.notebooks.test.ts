import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useNotebooksStore } from '@/stores/notebooks'
import type { Notebook } from '@/types'
import * as api from '@/api'

// Mock the API module
vi.mock('@/api', () => ({
  notebooksApi: {
    list: vi.fn(),
    get: vi.fn(),
    create: vi.fn(),
  },
}))

describe('useNotebooksStore', () => {
  beforeEach(() => {
    // Create a fresh pinia instance for each test
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('initializes with empty state', () => {
    const store = useNotebooksStore()
    
    expect(store.notebooks.size).toBe(0)
    expect(store.notebooksList).toEqual([])
    expect(store.loading).toBe(false)
    expect(store.error).toBe(null)
  })



  it('loads notebooks successfully', async () => {
    const mockNotebooks: Notebook[] = [
      { 
        id: '1', 
        title: 'Notebook 1', 
        description: 'Test notebook 1', 
        tags: [],
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
        settings: {},
      },
      { 
        id: '2', 
        title: 'Notebook 2', 
        description: 'Test notebook 2', 
        tags: [],
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
        settings: {},
      },
    ]
    
    vi.mocked(api.notebooksApi.list).mockResolvedValue(mockNotebooks)
    
    const store = useNotebooksStore()
    await store.loadNotebooks()
    
    expect(store.loading).toBe(false)
    expect(store.error).toBe(null)
    expect(store.notebooks.size).toBe(2)
    expect(store.notebooksList).toEqual(mockNotebooks)
    expect(api.notebooksApi.list).toHaveBeenCalledWith()
  })

  it('handles load notebooks error', async () => {
    const errorMessage = 'Network error'
    vi.mocked(api.notebooksApi.list).mockRejectedValue(new Error(errorMessage))
    
    const store = useNotebooksStore()
    await store.loadNotebooks()
    
    expect(store.loading).toBe(false)
    expect(store.error).toBe(errorMessage)
    expect(store.notebooks.size).toBe(0)
  })

  it('loads a single notebook successfully', async () => {
    const mockNotebook: Notebook = { 
      id: '1', 
      title: 'Notebook 1', 
      description: 'Test notebook', 
      tags: ['test'],
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
      settings: {},
    }
    
    vi.mocked(api.notebooksApi.get).mockResolvedValue(mockNotebook)
    
    const store = useNotebooksStore()
    const result = await store.loadNotebook('1')
    
    expect(result).toEqual(mockNotebook)
    expect(store.notebooks.get('1')).toEqual(mockNotebook)
    expect(api.notebooksApi.get).toHaveBeenCalledWith('1')
  })

  it('handles load notebook error', async () => {
    const errorMessage = 'Not found'
    vi.mocked(api.notebooksApi.get).mockRejectedValue(new Error(errorMessage))
    
    const store = useNotebooksStore()
    const result = await store.loadNotebook('1')
    
    expect(result).toBe(null)
    expect(store.error).toBe(errorMessage)
  })

  it('creates a notebook successfully', async () => {
    const mockNotebook: Notebook = { 
      id: '1', 
      title: 'New Notebook', 
      description: 'Test description', 
      tags: ['test'],
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
      settings: {},
    }
    
    vi.mocked(api.notebooksApi.create).mockResolvedValue(mockNotebook)
    
    const store = useNotebooksStore()
    const result = await store.createNotebook('New Notebook', 'Test description', ['test'])
    
    expect(result).toEqual(mockNotebook)
    expect(store.notebooks.get('1')).toEqual(mockNotebook)
    expect(api.notebooksApi.create).toHaveBeenCalledWith({
      title: 'New Notebook',
      description: 'Test description',
      tags: ['test'],
    })
  })

  it('handles create notebook error', async () => {
    const errorMessage = 'Creation failed'
    vi.mocked(api.notebooksApi.create).mockRejectedValue(new Error(errorMessage))
    
    const store = useNotebooksStore()
    const result = await store.createNotebook('New Notebook')
    
    expect(result).toBe(null)
    expect(store.error).toBe(errorMessage)
  })

  it('computed notebooksList returns array of notebooks', () => {
    const store = useNotebooksStore()
    
    const notebook1: Notebook = { 
      id: '1', 
      title: 'Notebook 1', 
      description: 'Desc 1', 
      tags: [],
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
      settings: {},
    }
    const notebook2: Notebook = { 
      id: '2', 
      title: 'Notebook 2', 
      description: 'Desc 2', 
      tags: [],
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
      settings: {},
    }
    
    store.notebooks.set('1', notebook1)
    store.notebooks.set('2', notebook2)
    
    const list = store.notebooksList
    expect(list).toHaveLength(2)
    expect(list.map(nb => nb.id)).toEqual(['1', '2'])
  })
})
