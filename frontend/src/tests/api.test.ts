import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { notebooksApi, pagesApi, entriesApi } from '@/api'

// Mock fetch globally
const mockFetch = vi.fn()
global.fetch = mockFetch

// Mock localStorage
const mockLocalStorage = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
}
global.localStorage = mockLocalStorage as any

describe('API Client', () => {
  beforeEach(() => {
    mockFetch.mockClear()
    mockLocalStorage.getItem.mockClear()
    mockLocalStorage.getItem.mockReturnValue('mock-jwt-token')
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('notebooksApi', () => {
    it('lists notebooks without workspace path', async () => {
      const mockNotebooks = [
        { id: '1', title: 'Notebook 1', description: 'Test', tags: [] },
      ]
      
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockNotebooks,
      })

      const result = await notebooksApi.list()

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/notebooks',
        expect.objectContaining({
          headers: expect.objectContaining({
            'Content-Type': 'application/json',
            'Authorization': 'Bearer mock-jwt-token',
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

      const result = await notebooksApi.get('1')

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/notebooks/1',
        expect.objectContaining({
          headers: expect.objectContaining({
            'Authorization': 'Bearer mock-jwt-token',
          }),
        })
      )
      expect(result).toEqual(mockNotebook)
    })

    it('creates a notebook without workspace path', async () => {
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

      const result = await notebooksApi.create({
        title: 'New Notebook',
        description: 'Test description',
        tags: ['test'],
      })

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/notebooks',
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({
            'Authorization': 'Bearer mock-jwt-token',
          }),
          body: JSON.stringify({
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

      await expect(notebooksApi.list()).rejects.toThrow(
        'API Error: 404 Not Found'
      )
    })

    it('redirects to login on 401 response', async () => {
      const originalHref = window.location.href
      delete (window as any).location
      window.location = { href: '' } as any

      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 401,
      })

      await expect(notebooksApi.list()).rejects.toThrow('Unauthorized')
      expect(window.location.href).toBe('/login')
      expect(mockLocalStorage.removeItem).toHaveBeenCalledWith('auth_token')
      expect(mockLocalStorage.removeItem).toHaveBeenCalledWith('user')

      window.location.href = originalHref
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

      const result = await pagesApi.list('nb1')

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/notebooks/nb1/pages',
        expect.objectContaining({
          headers: expect.objectContaining({
            'Authorization': 'Bearer mock-jwt-token',
          }),
        })
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

      const result = await pagesApi.create('nb1', {
        title: 'New Page',
        date: '2024-01-01',
      })

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/pages',
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({
            'Authorization': 'Bearer mock-jwt-token',
          }),
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

      const result = await pagesApi.update('1', {
        title: 'Updated Page',
      })

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/pages/1',
        expect.objectContaining({
          method: 'PATCH',
          headers: expect.objectContaining({
            'Authorization': 'Bearer mock-jwt-token',
          }),
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

      const result = await entriesApi.list('p1')

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/pages/p1/entries',
        expect.objectContaining({
          headers: expect.objectContaining({
            'Authorization': 'Bearer mock-jwt-token',
          }),
        })
      )
      expect(result).toEqual(mockEntries)
    })

    it('gets a single entry', async () => {
      const mockEntry = { id: '1', title: 'Entry 1', page_id: 'p1' }
      
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockEntry,
      })

      const result = await entriesApi.get('1')

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/entries/1',
        expect.objectContaining({
          headers: expect.objectContaining({
            'Authorization': 'Bearer mock-jwt-token',
          }),
        })
      )
      expect(result).toEqual(mockEntry)
    })
  })
})
