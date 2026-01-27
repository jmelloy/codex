import type { FileMetadata, FolderWithFiles, SubfolderMetadata } from "../services/codex"

export interface FileTreeNode {
  name: string
  path: string
  type: "file" | "folder"
  file?: FileMetadata
  children?: FileTreeNode[]
  // For folders, track if contents have been loaded
  loaded?: boolean
  // Folder metadata from API
  folderMeta?: {
    title?: string
    description?: string
    properties?: Record<string, any>
    file_count?: number
  }
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

/**
 * Sort nodes: folders first, then files, both alphabetically
 */
function sortNodes(nodes: FileTreeNode[]): void {
  nodes.sort((a, b) => {
    if (a.type !== b.type) {
      return a.type === "folder" ? -1 : 1
    }
    return a.name.localeCompare(b.name)
  })
}

/**
 * Find a node in the tree by path
 */
export function findNode(tree: FileTreeNode[], path: string): FileTreeNode | null {
  const parts = path.split("/").filter((p) => p !== "")
  if (parts.length === 0) return null

  let currentLevel = tree
  let node: FileTreeNode | null = null

  for (let i = 0; i < parts.length; i++) {
    const part = parts[i]
    node = currentLevel.find((n) => n.name === part) || null
    if (!node) return null
    if (i < parts.length - 1) {
      if (!node.children) return null
      currentLevel = node.children
    }
  }

  return node
}

/**
 * Find the parent folder node for a given path
 */
export function findParentNode(tree: FileTreeNode[], path: string): FileTreeNode | null {
  const parts = path.split("/").filter((p) => p !== "")
  if (parts.length <= 1) return null // No parent, it's at root

  const parentPath = parts.slice(0, -1).join("/")
  return findNode(tree, parentPath)
}

/**
 * Insert a file node into the tree at the correct position
 */
export function insertFileNode(tree: FileTreeNode[], file: FileMetadata): void {
  const pathParts = file.path.split("/").filter((p) => p !== "")
  if (pathParts.length === 0) return

  // Ensure all parent folders exist
  let currentLevel = tree
  let currentPath = ""

  for (let i = 0; i < pathParts.length - 1; i++) {
    const part = pathParts[i]!
    currentPath = currentPath ? `${currentPath}/${part}` : part

    let folderNode = currentLevel.find((n) => n.name === part && n.type === "folder")
    if (!folderNode) {
      folderNode = {
        name: part,
        path: currentPath,
        type: "folder",
        children: [],
        loaded: false,
      }
      currentLevel.push(folderNode)
      sortNodes(currentLevel)
    }
    if (!folderNode.children) {
      folderNode.children = []
    }
    currentLevel = folderNode.children
  }

  // Add the file node
  const filename = pathParts[pathParts.length - 1]!
  const existingIndex = currentLevel.findIndex((n) => n.path === file.path)
  const fileNode: FileTreeNode = {
    name: filename,
    path: file.path,
    type: "file",
    file: file,
  }

  if (existingIndex >= 0) {
    currentLevel[existingIndex] = fileNode
  } else {
    currentLevel.push(fileNode)
    sortNodes(currentLevel)
  }
}

/**
 * Insert or update a folder node in the tree
 */
export function insertFolderNode(
  tree: FileTreeNode[],
  folderPath: string,
  meta?: SubfolderMetadata
): FileTreeNode {
  const pathParts = folderPath.split("/").filter((p) => p !== "")
  if (pathParts.length === 0) {
    throw new Error("Cannot insert folder at root")
  }

  let currentLevel = tree
  let currentPath = ""
  let node: FileTreeNode | null = null

  for (let i = 0; i < pathParts.length; i++) {
    const part = pathParts[i]!
    currentPath = currentPath ? `${currentPath}/${part}` : part

    node = currentLevel.find((n) => n.name === part && n.type === "folder") || null
    if (!node) {
      node = {
        name: part,
        path: currentPath,
        type: "folder",
        children: [],
        loaded: false,
      }
      currentLevel.push(node)
      sortNodes(currentLevel)
    }

    if (i === pathParts.length - 1 && meta) {
      // Apply metadata to the final folder
      node.folderMeta = {
        title: meta.title,
        description: meta.description,
        properties: meta.properties,
      }
    }

    if (!node.children) {
      node.children = []
    }
    currentLevel = node.children
  }

  return node!
}

/**
 * Remove a node from the tree by path
 */
export function removeNode(tree: FileTreeNode[], path: string): boolean {
  const parts = path.split("/").filter((p) => p !== "")
  if (parts.length === 0) return false

  if (parts.length === 1) {
    // Remove from root
    const index = tree.findIndex((n) => n.path === path)
    if (index >= 0) {
      tree.splice(index, 1)
      return true
    }
    return false
  }

  // Find parent and remove from there
  const parentPath = parts.slice(0, -1).join("/")
  const parent = findNode(tree, parentPath)
  if (!parent || !parent.children) return false

  const index = parent.children.findIndex((n) => n.path === path)
  if (index >= 0) {
    parent.children.splice(index, 1)
    return true
  }
  return false
}

/**
 * Update a file node's metadata in the tree
 */
export function updateFileNode(tree: FileTreeNode[], file: FileMetadata): boolean {
  const node = findNode(tree, file.path)
  if (!node || node.type !== "file") return false

  node.file = file
  return true
}

/**
 * Merge folder contents into the tree at a specific path.
 * This is called when folder contents are loaded from the API.
 */
export function mergeFolderContents(
  tree: FileTreeNode[],
  folderPath: string,
  folderData: FolderWithFiles,
  allPaths: Set<string>
): void {
  // Get or create the folder node
  let targetChildren: FileTreeNode[]

  if (!folderPath) {
    // Merging at root level
    targetChildren = tree
  } else {
    const folderNode = insertFolderNode(tree, folderPath)
    folderNode.loaded = true
    folderNode.folderMeta = {
      title: folderData.title,
      description: folderData.description,
      properties: folderData.properties,
      file_count: folderData.file_count,
    }
    targetChildren = folderNode.children!
  }

  // Add subfolders
  if (folderData.subfolders) {
    for (const subfolder of folderData.subfolders) {
      const existingFolder = targetChildren.find(
        (n) => n.path === subfolder.path && n.type === "folder"
      )
      if (existingFolder) {
        // Update metadata but preserve children and loaded state
        existingFolder.folderMeta = {
          title: subfolder.title,
          description: subfolder.description,
          properties: subfolder.properties,
        }
      } else {
        targetChildren.push({
          name: subfolder.name,
          path: subfolder.path,
          type: "folder",
          children: [],
          loaded: false,
          folderMeta: {
            title: subfolder.title,
            description: subfolder.description,
            properties: subfolder.properties,
          },
        })
      }
    }
  }

  // Add files (filter out sidecars)
  const visibleFiles = folderData.files.filter((f) => !isSidecarFile(f, allPaths))
  for (const file of visibleFiles) {
    const existingFile = targetChildren.find((n) => n.path === file.path && n.type === "file")
    if (existingFile) {
      existingFile.file = file
    } else {
      targetChildren.push({
        name: file.filename,
        path: file.path,
        type: "file",
        file: file,
      })
    }
  }

  sortNodes(targetChildren)
}

/**
 * Build a set of all file paths in the tree (for sidecar detection)
 */
export function getAllPaths(tree: FileTreeNode[]): Set<string> {
  const paths = new Set<string>()

  function walk(nodes: FileTreeNode[]) {
    for (const node of nodes) {
      paths.add(node.path)
      if (node.children) {
        walk(node.children)
      }
    }
  }

  walk(tree)
  return paths
}

/**
 * Get all file metadata from the tree as a flat array
 */
export function getAllFiles(tree: FileTreeNode[]): FileMetadata[] {
  const files: FileMetadata[] = []

  function walk(nodes: FileTreeNode[]) {
    for (const node of nodes) {
      if (node.type === "file" && node.file) {
        files.push(node.file)
      }
      if (node.children) {
        walk(node.children)
      }
    }
  }

  walk(tree)
  return files
}

/**
 * Move a node from one path to another
 */
export function moveNode(tree: FileTreeNode[], oldPath: string, newPath: string): boolean {
  const node = findNode(tree, oldPath)
  if (!node) return false

  // Remove from old location
  if (!removeNode(tree, oldPath)) return false

  // Update path and insert at new location
  if (node.type === "file" && node.file) {
    node.file = { ...node.file, path: newPath, filename: newPath.split("/").pop()! }
    node.path = newPath
    node.name = newPath.split("/").pop()!
    insertFileNode(tree, node.file)
  } else {
    // For folders, need to recursively update all child paths
    const oldPrefix = oldPath
    const newPrefix = newPath

    function updatePaths(n: FileTreeNode) {
      n.path = n.path.replace(oldPrefix, newPrefix)
      if (n.file) {
        n.file = { ...n.file, path: n.path, filename: n.path.split("/").pop()! }
      }
      if (n.children) {
        n.children.forEach(updatePaths)
      }
    }

    updatePaths(node)
    insertFolderNode(tree, newPath)
    const newNode = findNode(tree, newPath)
    if (newNode) {
      newNode.children = node.children
      newNode.loaded = node.loaded
      newNode.folderMeta = node.folderMeta
    }
  }

  return true
}
