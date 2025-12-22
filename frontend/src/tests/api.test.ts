import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { notebooksApi, pagesApi, entriesApi } from '@/api'

// Mock fetch globally
const mockFetch = vi.fn()
global.fetch = mockFetch

describe('API Client', () => {
  beforeEach(() => {
    mockFetch.mockClear()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('notebooksApi', () => {
    it('lists notebooks with workspace path', async () => {
      const mockNotebooks = [
        { id: '1', title: 'Notebook 1', description: 'Test', tags: [] },
      ]
      
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockNotebooks,
      })

      const result = await notebooksApi.list('/test/workspace')

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/notebooks?workspace_path=%2Ftest%2Fworkspace',
        expect.objectContaining({
          headers: expect.objectContaining({
            'Content-Type': 'application/json',
          }),
        })
      )
      expect(result).toEqual(mockNotebooks)
    })

    it('gets a single notebook', async () => {
      const mockNotebook = { id: '1', title: 'Notebook 1', description: 'Test', tags: [] }
      
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockNotebook,
      })

      const result = await notebooksApi.get('/workspace', '1')

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/notebooks/1?workspace_path=%2Fworkspace',
        expect.any(Object)
      )
      expect(result).toEqual(mockNotebook)
    })

    it('creates a notebook', async () => {
      const mockNotebook = { 
        id: '1', 
        title: 'New Notebook', 
        description: 'Test description', 
        tags: ['test'] 
      }
      
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockNotebook,
      })

      const result = await notebooksApi.create('/workspace', {
        title: 'New Notebook',
        description: 'Test description',
        tags: ['test'],
      })

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/notebooks',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({
            workspace_path: '/workspace',
            title: 'New Notebook',
            description: 'Test description',
            tags: ['test'],
          }),
        })
      )
      expect(result).toEqual(mockNotebook)
    })

    it('throws error on failed request', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        statusText: 'Not Found',
      })

      await expect(notebooksApi.list('/workspace')).rejects.toThrow(
        'API Error: 404 Not Found'
      )
    })
  })

  describe('pagesApi', () => {
    it('lists pages for a notebook', async () => {
      const mockPages = [
        { id: '1', title: 'Page 1', notebook_id: 'nb1' },
      ]
      
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockPages,
      })

      const result = await pagesApi.list('/workspace', 'nb1')

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/notebooks/nb1/pages?workspace_path=%2Fworkspace',
        expect.any(Object)
      )
      expect(result).toEqual(mockPages)
    })

    it('creates a page', async () => {
      const mockPage = { 
        id: '1', 
        title: 'New Page', 
        notebook_id: 'nb1',
        date: '2024-01-01' 
      }
      
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockPage,
      })

      const result = await pagesApi.create('/workspace', 'nb1', {
        title: 'New Page',
        date: '2024-01-01',
      })

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/pages',
        expect.objectContaining({
          method: 'POST',
          body: expect.stringContaining('New Page'),
        })
      )
      expect(result).toEqual(mockPage)
    })

    it('updates a page', async () => {
      const mockPage = { 
        id: '1', 
        title: 'Updated Page', 
        notebook_id: 'nb1' 
      }
      
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockPage,
      })

      const result = await pagesApi.update('/workspace', '1', {
        title: 'Updated Page',
      })

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/pages/1',
        expect.objectContaining({
          method: 'PATCH',
        })
      )
      expect(result).toEqual(mockPage)
    })
  })

  describe('entriesApi', () => {
    it('lists entries for a page', async () => {
      const mockEntries = [
        { id: '1', title: 'Entry 1', page_id: 'p1' },
      ]
      
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockEntries,
      })

      const result = await entriesApi.list('/workspace', 'p1')

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/pages/p1/entries?workspace_path=%2Fworkspace',
        expect.any(Object)
      )
      expect(result).toEqual(mockEntries)
    })

    it('gets a single entry', async () => {
      const mockEntry = { id: '1', title: 'Entry 1', page_id: 'p1' }
      
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockEntry,
      })

      const result = await entriesApi.get('/workspace', '1')

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/entries/1?workspace_path=%2Fworkspace',
        expect.any(Object)
      )
      expect(result).toEqual(mockEntry)
    })
  })
})
