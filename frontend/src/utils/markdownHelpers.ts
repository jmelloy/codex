/**
 * Shared helpers for resolving file references in markdown content.
 * Used by both MarkdownViewer and BlockView.
 */

/** Check if a URL is a local file reference (not an external URL). */
export function isLocalFileReference(href: string): boolean {
  if (href.endsWith(".md") || href.endsWith(".txt")) {
    return true
  }
  return !href.startsWith("http://") && !href.startsWith("https://") && !href.startsWith("/")
}

/** Resolve a file reference to an API URL for serving content. */
export function resolveFileUrl(
  href: string,
  workspaceId: number | string | undefined,
  notebookId: number | string | undefined
): string {
  if (workspaceId && notebookId) {
    if (href.startsWith("http://") || href.startsWith("https://") || href.startsWith("/api/")) {
      return href
    }
    const encodedPath = encodeURIComponent(href)
    return `/api/v1/workspaces/${workspaceId}/notebooks/${notebookId}/blocks/path/${encodedPath}/content`
  }
  return href
}
