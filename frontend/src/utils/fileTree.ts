import type { FileMetadata } from "../services/codex"

export interface FileTreeNode {
  name: string
  path: string
  type: "file" | "folder"
  file?: FileMetadata
  children?: FileTreeNode[]
}

const SIDECAR_EXTENSIONS = [".json", ".xml", ".md"]

/**
 * Check if a file is a sidecar metadata file for another file.
 * Sidecar patterns: filename.ext.json, .filename.ext.json, etc.
 */
export function isSidecarFile(file: FileMetadata, allPaths: Set<string>): boolean {
  const filename = file.filename

  for (const ext of SIDECAR_EXTENSIONS) {
    if (!filename.endsWith(ext)) continue

    // Get the path without the sidecar extension
    const basePath = file.path.slice(0, -ext.length)

    // Check if the parent file exists (e.g., image.png for image.png.json)
    if (allPaths.has(basePath)) {
      return true
    }

    // Check for dot-prefixed sidecar (e.g., .image.png.json for image.png)
    if (filename.startsWith(".")) {
      const dir = file.path.slice(0, file.path.length - filename.length)
      const parentFilename = filename.slice(1, -ext.length) // Remove leading "." and trailing ext
      const parentPath = dir + parentFilename
      if (allPaths.has(parentPath)) {
        return true
      }
    }
  }

  return false
}

/**
 * Build a hierarchical tree structure from a flat list of files
 */
export function buildFileTree(files: FileMetadata[]): FileTreeNode[] {
  const root: FileTreeNode[] = []

  // Create a map to track folders we've already created
  const folderMap = new Map<string, FileTreeNode>()

  // Build a set of all file paths for sidecar detection
  const allPaths = new Set(files.map((f) => f.path))

  // Filter out sidecar files and sort by path
  const visibleFiles = files.filter((f) => !isSidecarFile(f, allPaths))
  const sortedFiles = [...visibleFiles].sort((a, b) => a.path.localeCompare(b.path))

  for (const file of sortedFiles) {
    const pathParts = file.path.split("/").filter((part) => part !== "")
    if (pathParts.length === 0) continue

    let currentLevel = root
    let currentPath = ""

    // Process each part of the path except the last (which is the filename)
    for (let i = 0; i < pathParts.length - 1; i++) {
      const part = pathParts[i]! // Safe because we're iterating within bounds
      currentPath = currentPath ? `${currentPath}/${part}` : part

      // Check if this folder already exists at current level
      let folderNode = folderMap.get(currentPath)

      if (!folderNode) {
        // Create new folder node
        folderNode = {
          name: part,
          path: currentPath,
          type: "folder",
          children: [],
        }

        currentLevel.push(folderNode)
        folderMap.set(currentPath, folderNode)
      }

      // Move to next level
      currentLevel = folderNode.children!
    }

    // Add the file itself
    const filename = pathParts[pathParts.length - 1]! // Safe because pathParts.length > 0
    currentLevel.push({
      name: filename,
      path: file.path,
      type: "file",
      file: file,
    })
  }

  // Sort each level: folders first, then files, both alphabetically
  const sortLevel = (nodes: FileTreeNode[]) => {
    nodes.sort((a, b) => {
      if (a.type !== b.type) {
        return a.type === "folder" ? -1 : 1
      }
      return a.name.localeCompare(b.name)
    })

    // Recursively sort children
    nodes.forEach((node) => {
      if (node.children) {
        sortLevel(node.children)
      }
    })
  }

  sortLevel(root)
  return root
}
