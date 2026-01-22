import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { viewPathResolver } from '../../services/viewPathResolver'
import { fileService, notebookService } from '../../services/codex'

// Mock the codex services
vi.mock('../../services/codex', () => ({
  fileService: {
    list: vi.fn(),
  },
  notebookService: {
    list: vi.fn(),
  },
}))

describe('View Path Resolver', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    viewPathResolver.clearCache()
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  describe('resolve', () => {
    it('should resolve a direct path match', async () => {
      const mockNotebooks = [{ id: 1, name: 'Project' }]
      const mockFiles = [
        { id: 10, path: 'views/kanban.cdx', filename: 'kanban.cdx' },
        { id: 11, path: 'docs/readme.md', filename: 'readme.md' },
      ]

      vi.mocked(notebookService.list).mockResolvedValue(mockNotebooks as any)
      vi.mocked(fileService.list).mockResolvedValue(mockFiles as any)

      const fileId = await viewPathResolver.resolve('views/kanban.cdx', 1)

      expect(fileId).toBe(10)
      expect(notebookService.list).toHaveBeenCalledWith(1)
      expect(fileService.list).toHaveBeenCalledWith(1, 1)
    })

    it('should resolve a relative path match', async () => {
      const mockNotebooks = [{ id: 1, name: 'Project' }]
      const mockFiles = [
        {
          id: 10,
          path: 'tasks/views/kanban.cdx',
          filename: 'kanban.cdx',
        },
      ]

      vi.mocked(notebookService.list).mockResolvedValue(mockNotebooks as any)
      vi.mocked(fileService.list).mockResolvedValue(mockFiles as any)

      const fileId = await viewPathResolver.resolve('views/kanban.cdx', 1)

      expect(fileId).toBe(10)
    })

    it('should resolve with leading slash', async () => {
      const mockNotebooks = [{ id: 1, name: 'Project' }]
      const mockFiles = [
        { id: 10, path: 'views/kanban.cdx', filename: 'kanban.cdx' },
      ]

      vi.mocked(notebookService.list).mockResolvedValue(mockNotebooks as any)
      vi.mocked(fileService.list).mockResolvedValue(mockFiles as any)

      const fileId = await viewPathResolver.resolve('/views/kanban.cdx', 1)

      expect(fileId).toBe(10)
    })

    it('should return null when file not found', async () => {
      const mockNotebooks = [{ id: 1, name: 'Project' }]
      const mockFiles = [
        { id: 10, path: 'views/gallery.cdx', filename: 'gallery.cdx' },
      ]

      vi.mocked(notebookService.list).mockResolvedValue(mockNotebooks as any)
      vi.mocked(fileService.list).mockResolvedValue(mockFiles as any)

      const fileId = await viewPathResolver.resolve('views/kanban.cdx', 1)

      expect(fileId).toBeNull()
    })

    it('should search across multiple notebooks', async () => {
      const mockNotebooks = [
        { id: 1, name: 'Project A' },
        { id: 2, name: 'Project B' },
      ]

      vi.mocked(notebookService.list).mockResolvedValue(mockNotebooks as any)
      vi.mocked(fileService.list)
        .mockResolvedValueOnce([
          { id: 10, path: 'views/gallery.cdx', filename: 'gallery.cdx' },
        ] as any)
        .mockResolvedValueOnce([
          { id: 20, path: 'views/kanban.cdx', filename: 'kanban.cdx' },
        ] as any)

      const fileId = await viewPathResolver.resolve('views/kanban.cdx', 1)

      expect(fileId).toBe(20)
      expect(fileService.list).toHaveBeenCalledTimes(2)
    })

    it('should return first match when multiple files match', async () => {
      const mockNotebooks = [
        { id: 1, name: 'Project A' },
        { id: 2, name: 'Project B' },
      ]

      vi.mocked(notebookService.list).mockResolvedValue(mockNotebooks as any)
      vi.mocked(fileService.list)
        .mockResolvedValueOnce([
          { id: 10, path: 'views/kanban.cdx', filename: 'kanban.cdx' },
        ] as any)
        .mockResolvedValueOnce([
          { id: 20, path: 'views/kanban.cdx', filename: 'kanban.cdx' },
        ] as any)

      const fileId = await viewPathResolver.resolve('views/kanban.cdx', 1)

      expect(fileId).toBe(10)
      expect(fileService.list).toHaveBeenCalledTimes(1) // Should stop after first match
    })

    it('should handle notebook search errors gracefully', async () => {
      const mockNotebooks = [
        { id: 1, name: 'Project A' },
        { id: 2, name: 'Project B' },
      ]

      const consoleWarnSpy = vi
        .spyOn(console, 'warn')
        .mockImplementation(() => {})

      vi.mocked(notebookService.list).mockResolvedValue(mockNotebooks as any)
      vi.mocked(fileService.list)
        .mockRejectedValueOnce(new Error('Notebook 1 error'))
        .mockResolvedValueOnce([
          { id: 20, path: 'views/kanban.cdx', filename: 'kanban.cdx' },
        ] as any)

      const fileId = await viewPathResolver.resolve('views/kanban.cdx', 1)

      expect(fileId).toBe(20)
      expect(consoleWarnSpy).toHaveBeenCalledWith(
        expect.stringContaining('Failed to search notebook'),
        expect.any(Error)
      )

      consoleWarnSpy.mockRestore()
    })

    it('should handle complete failure gracefully', async () => {
      const consoleErrorSpy = vi
        .spyOn(console, 'error')
        .mockImplementation(() => {})

      vi.mocked(notebookService.list).mockRejectedValue(
        new Error('Failed to list notebooks')
      )

      const fileId = await viewPathResolver.resolve('views/kanban.cdx', 1)

      expect(fileId).toBeNull()
      expect(consoleErrorSpy).toHaveBeenCalledWith(
        'Failed to resolve view path:',
        expect.any(Error)
      )

      consoleErrorSpy.mockRestore()
    })
  })

  describe('caching', () => {
    it('should cache resolved paths', async () => {
      const mockNotebooks = [{ id: 1, name: 'Project' }]
      const mockFiles = [
        { id: 10, path: 'views/kanban.cdx', filename: 'kanban.cdx' },
      ]

      vi.mocked(notebookService.list).mockResolvedValue(mockNotebooks as any)
      vi.mocked(fileService.list).mockResolvedValue(mockFiles as any)

      // First call
      const fileId1 = await viewPathResolver.resolve('views/kanban.cdx', 1)
      expect(fileId1).toBe(10)

      // Second call should use cache
      const fileId2 = await viewPathResolver.resolve('views/kanban.cdx', 1)
      expect(fileId2).toBe(10)

      // Should only call services once
      expect(notebookService.list).toHaveBeenCalledTimes(1)
      expect(fileService.list).toHaveBeenCalledTimes(1)
    })

    it('should expire cache after TTL', async () => {
      const mockNotebooks = [{ id: 1, name: 'Project' }]
      const mockFiles = [
        { id: 10, path: 'views/kanban.cdx', filename: 'kanban.cdx' },
      ]

      vi.mocked(notebookService.list).mockResolvedValue(mockNotebooks as any)
      vi.mocked(fileService.list).mockResolvedValue(mockFiles as any)

      // First call
      await viewPathResolver.resolve('views/kanban.cdx', 1)

      // Advance time beyond TTL (5 minutes)
      vi.advanceTimersByTime(6 * 60 * 1000)

      // Second call should not use cache
      await viewPathResolver.resolve('views/kanban.cdx', 1)

      // Should call services twice
      expect(notebookService.list).toHaveBeenCalledTimes(2)
      expect(fileService.list).toHaveBeenCalledTimes(2)
    })

    it('should cache per workspace', async () => {
      const mockNotebooks = [{ id: 1, name: 'Project' }]
      const mockFiles1 = [
        { id: 10, path: 'views/kanban.cdx', filename: 'kanban.cdx' },
      ]
      const mockFiles2 = [
        { id: 20, path: 'views/kanban.cdx', filename: 'kanban.cdx' },
      ]

      vi.mocked(notebookService.list).mockResolvedValue(mockNotebooks as any)
      vi.mocked(fileService.list)
        .mockResolvedValueOnce(mockFiles1 as any)
        .mockResolvedValueOnce(mockFiles2 as any)

      // Same path, different workspaces
      const fileId1 = await viewPathResolver.resolve('views/kanban.cdx', 1)
      const fileId2 = await viewPathResolver.resolve('views/kanban.cdx', 2)

      expect(fileId1).toBe(10)
      expect(fileId2).toBe(20)
      expect(notebookService.list).toHaveBeenCalledTimes(2)
    })
  })

  describe('clearCache', () => {
    it('should clear specific cache entry', async () => {
      const mockNotebooks = [{ id: 1, name: 'Project' }]
      const mockFiles = [
        { id: 10, path: 'views/kanban.cdx', filename: 'kanban.cdx' },
      ]

      vi.mocked(notebookService.list).mockResolvedValue(mockNotebooks as any)
      vi.mocked(fileService.list).mockResolvedValue(mockFiles as any)

      // Cache the entry
      await viewPathResolver.resolve('views/kanban.cdx', 1)

      // Clear specific entry
      viewPathResolver.clearCache('views/kanban.cdx', 1)

      // Next call should not use cache
      await viewPathResolver.resolve('views/kanban.cdx', 1)

      expect(notebookService.list).toHaveBeenCalledTimes(2)
    })

    it('should clear all cache entries', async () => {
      const mockNotebooks = [{ id: 1, name: 'Project' }]
      const mockFiles = [
        { id: 10, path: 'views/kanban.cdx', filename: 'kanban.cdx' },
        { id: 11, path: 'views/gallery.cdx', filename: 'gallery.cdx' },
      ]

      vi.mocked(notebookService.list).mockResolvedValue(mockNotebooks as any)
      vi.mocked(fileService.list).mockResolvedValue(mockFiles as any)

      // Cache multiple entries
      await viewPathResolver.resolve('views/kanban.cdx', 1)
      await viewPathResolver.resolve('views/gallery.cdx', 1)

      // Clear all cache
      viewPathResolver.clearCache()

      // Next calls should not use cache
      await viewPathResolver.resolve('views/kanban.cdx', 1)
      await viewPathResolver.resolve('views/gallery.cdx', 1)

      expect(notebookService.list).toHaveBeenCalledTimes(4)
    })
  })

  describe('matchesPath', () => {
    it('should match direct path', () => {
      const file = { path: 'views/kanban.cdx' } as any

      expect(viewPathResolver.matchesPath(file, 'views/kanban.cdx')).toBe(true)
    })

    it('should match relative path', () => {
      const file = { path: 'tasks/views/kanban.cdx' } as any

      expect(viewPathResolver.matchesPath(file, 'views/kanban.cdx')).toBe(true)
    })

    it('should match with leading slash', () => {
      const file = { path: 'views/kanban.cdx' } as any

      expect(viewPathResolver.matchesPath(file, '/views/kanban.cdx')).toBe(
        true
      )
    })

    it('should not match different paths', () => {
      const file = { path: 'views/gallery.cdx' } as any

      expect(viewPathResolver.matchesPath(file, 'views/kanban.cdx')).toBe(
        false
      )
    })

    it('should not match partial paths', () => {
      const file = { path: 'myviews/kanban.cdx' } as any

      expect(viewPathResolver.matchesPath(file, 'views/kanban.cdx')).toBe(
        false
      )
    })
  })

  describe('preload', () => {
    it('should preload multiple view paths', async () => {
      const mockNotebooks = [{ id: 1, name: 'Project' }]
      const mockFiles = [
        { id: 10, path: 'views/kanban.cdx', filename: 'kanban.cdx' },
        { id: 11, path: 'views/gallery.cdx', filename: 'gallery.cdx' },
        { id: 12, path: 'views/calendar.cdx', filename: 'calendar.cdx' },
      ]

      vi.mocked(notebookService.list).mockResolvedValue(mockNotebooks as any)
      vi.mocked(fileService.list).mockResolvedValue(mockFiles as any)

      await viewPathResolver.preload(
        ['views/kanban.cdx', 'views/gallery.cdx', 'views/calendar.cdx'],
        1
      )

      // All paths should be cached now
      await viewPathResolver.resolve('views/kanban.cdx', 1)
      await viewPathResolver.resolve('views/gallery.cdx', 1)
      await viewPathResolver.resolve('views/calendar.cdx', 1)

      // Should only call services during preload (3 times) and not again
      expect(notebookService.list).toHaveBeenCalledTimes(3)
    })

    it('should handle preload errors gracefully', async () => {
      vi.mocked(notebookService.list).mockRejectedValue(
        new Error('Network error')
      )

      const consoleErrorSpy = vi
        .spyOn(console, 'error')
        .mockImplementation(() => {})

      await expect(
        viewPathResolver.preload(['views/kanban.cdx'], 1)
      ).resolves.not.toThrow()

      consoleErrorSpy.mockRestore()
    })
  })
})
