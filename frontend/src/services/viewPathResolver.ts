/**
 * Service for resolving view paths to file IDs
 */

import { fileService, notebookService } from "./codex"
import type { FileMetadata } from "./codex"

interface ResolverCache {
  [key: string]: {
    fileId: number
    timestamp: number
  }
}

const cache: ResolverCache = {}
const CACHE_TTL = 5 * 60 * 1000 // 5 minutes

export const viewPathResolver = {
  /**
   * Resolve a view path to a file ID
   * @param viewPath - Path to the view file (e.g., "tasks/today.cdx")
   * @param workspaceSlug - Workspace slug
   * @returns File ID or null if not found
   */
  async resolve(viewPath: string, workspaceSlug: string): Promise<number | null> {
    const cacheKey = `${workspaceSlug}:${viewPath}`

    // Check cache
    const cached = cache[cacheKey]
    if (cached && Date.now() - cached.timestamp < CACHE_TTL) {
      return cached.fileId
    }

    try {
      // Get all notebooks in workspace
      const notebooks = await notebookService.list(workspaceSlug)

      // Search through notebooks for the file
      for (const notebook of notebooks) {
        try {
          const notebookSlug = notebook.slug || notebook.path
          const files = await fileService.list(workspaceSlug, notebookSlug)

          // Look for file matching the path
          const matchingFile = files.find((file) => {
            return this.matchesPath(file, viewPath)
          })

          if (matchingFile) {
            // Cache the result
            cache[cacheKey] = {
              fileId: matchingFile.id,
              timestamp: Date.now(),
            }

            return matchingFile.id
          }
        } catch (err) {
          console.warn(`Failed to search notebook ${notebook.id}:`, err)
        }
      }

      return null
    } catch (err) {
      console.error("Failed to resolve view path:", err)
      return null
    }
  },

  /**
   * Check if a file matches a view path
   */
  matchesPath(file: FileMetadata, viewPath: string): boolean {
    // Direct match
    if (file.path === viewPath) {
      return true
    }

    // Match if file path ends with the view path
    if (file.path.endsWith("/" + viewPath)) {
      return true
    }

    // Match without leading slash
    if (viewPath.startsWith("/") && file.path === viewPath.substring(1)) {
      return true
    }

    return false
  },

  /**
   * Clear cache for a specific path or all paths
   */
  clearCache(viewPath?: string, workspaceSlug?: string) {
    if (viewPath && workspaceSlug) {
      const cacheKey = `${workspaceSlug}:${viewPath}`
      delete cache[cacheKey]
    } else {
      // Clear all cache
      Object.keys(cache).forEach((key) => {
        delete cache[key]
      })
    }
  },

  /**
   * Preload view paths for better performance
   */
  async preload(viewPaths: string[], workspaceSlug: string) {
    const promises = viewPaths.map((path) => this.resolve(path, workspaceSlug))
    await Promise.all(promises)
  },
}
