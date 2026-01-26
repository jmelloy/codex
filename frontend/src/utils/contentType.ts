/**
 * Utility functions for working with content types (MIME types)
 */

/**
 * Get the display category from a MIME type
 * Maps MIME types to simple display categories for UI purposes
 */
export function getDisplayType(contentType: string): string {
  // Handle special Codex types
  if (contentType === "application/x-codex-view") {
    return "view"
  }

  // Map common MIME types to display categories
  if (contentType.startsWith("image/")) {
    return "image"
  }

  if (contentType.startsWith("video/")) {
    return "video"
  }

  if (contentType.startsWith("audio/")) {
    return "audio"
  }

  // Text-based types
  if (contentType === "text/markdown") {
    return "markdown"
  }

  if (contentType === "text/html") {
    return "html"
  }

  if (contentType === "application/json") {
    return "json"
  }

  if (contentType === "application/xml" || contentType === "text/xml") {
    return "xml"
  }

  if (contentType === "application/pdf") {
    return "pdf"
  }

  // Code file types
  if (
    contentType.startsWith("text/x-") ||
    contentType === "text/plain" ||
    contentType === "application/javascript" ||
    contentType === "application/typescript" ||
    contentType.includes("python") ||
    contentType.includes("java") ||
    contentType.includes("c++") ||
    contentType === "text/css"
  ) {
    return "code"
  }

  // Generic text for any other text/* types
  if (contentType.startsWith("text/")) {
    return "text"
  }

  // Binary fallback
  return "binary"
}

/**
 * Check if content type can be displayed as text
 */
export function isTextType(contentType: string): boolean {
  return (
    contentType.startsWith("text/") ||
    contentType === "application/json" ||
    contentType === "application/xml" ||
    contentType === "application/x-codex-view"
  )
}

/**
 * Check if content type is an image
 */
export function isImageType(contentType: string): boolean {
  return contentType.startsWith("image/")
}

/**
 * Check if content type is a video
 */
export function isVideoType(contentType: string): boolean {
  return contentType.startsWith("video/")
}

/**
 * Check if content type is audio
 */
export function isAudioType(contentType: string): boolean {
  return contentType.startsWith("audio/")
}
