import type { Block } from "../services/codex"

export interface FileTreeNode {
  name: string
  path: string
  type: "file" | "folder"
  file?: Block
  children?: FileTreeNode[]
  loaded?: boolean
  folderMeta?: {
    title?: string
    description?: string
    properties?: Record<string, any>
    file_count?: number
  }
  // Block fields
  isPage?: boolean
  hasSubpages?: boolean
  blockOrder?: string[]
  block_id?: string
  block_type?: string
  parent_block_id?: string | null
  content_type?: string
  title?: string
  block?: Block
}

/**
 * Convert a block tree (from GET /blocks/tree) into FileTreeNode format.
 */
export function blockTreeToFileTree(blocks: Block[]): FileTreeNode[] {
  return blocks.map((block) => {
    const name = block.path.split("/").pop() || block.title || block.path
    const node: FileTreeNode = {
      name: block.title || name,
      path: block.path,
      type: block.block_type === "page" ? "folder" : "file",
      block_id: block.block_id,
      block_type: block.block_type,
      parent_block_id: block.parent_block_id,
      content_type: block.content_type,
      title: block.title,
      block: block,
      isPage: block.block_type === "page",
      loaded: true,
    }

    if (block.block_type !== "page") {
      node.file = block
    } else {
      node.folderMeta = {
        title: block.title,
        description: block.description,
        properties: block.properties,
      }
      node.hasSubpages = block.children?.some((c) => c.block_type === "page") ?? false
    }

    if (block.children && block.children.length > 0) {
      node.children = blockTreeToFileTree(block.children)
    } else if (block.block_type === "page") {
      node.children = []
    }

    return node
  })
}

/** Hidden metadata filenames that should not appear in the tree */
const HIDDEN_FILENAMES = new Set([".metadata", ".codex-page.json"])

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
  if (parts.length <= 1) return null
  const parentPath = parts.slice(0, -1).join("/")
  return findNode(tree, parentPath)
}

/**
 * Insert a file node into the tree at the correct position
 */
export function insertFileNode(tree: FileTreeNode[], file: Block): void {
  const fname = file.filename || file.path.split("/").pop() || ""
  if (HIDDEN_FILENAMES.has(fname)) return

  const pathParts = file.path.split("/").filter((p) => p !== "")
  if (pathParts.length === 0) return

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
 * Remove a node from the tree by path
 */
export function removeNode(tree: FileTreeNode[], path: string): boolean {
  const parts = path.split("/").filter((p) => p !== "")
  if (parts.length === 0) return false

  if (parts.length === 1) {
    const index = tree.findIndex((n) => n.path === path)
    if (index >= 0) {
      tree.splice(index, 1)
      return true
    }
    return false
  }

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
export function updateFileNode(tree: FileTreeNode[], file: Block): boolean {
  const node = findNode(tree, file.path)
  if (!node || node.type !== "file") return false
  node.file = file
  return true
}

/**
 * Get all file metadata from the tree as a flat array
 */
export function getAllFiles(tree: FileTreeNode[]): Block[] {
  const files: Block[] = []

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

  if (!removeNode(tree, oldPath)) return false

  if (node.type === "file" && node.file) {
    node.file = { ...node.file, path: newPath, filename: newPath.split("/").pop() || newPath }
    node.path = newPath
    node.name = newPath.split("/").pop() || newPath
    insertFileNode(tree, node.file)
  } else {
    const oldPrefix = oldPath
    const newPrefix = newPath

    function updatePaths(n: FileTreeNode) {
      if (n.path === oldPrefix) {
        n.path = newPrefix
      } else if (n.path.startsWith(oldPrefix + "/")) {
        n.path = newPrefix + n.path.substring(oldPrefix.length)
      }
      n.name = n.path.split("/").pop() || n.path
      if (n.file) {
        n.file = { ...n.file, path: n.path, filename: n.path.split("/").pop() || n.path }
      }
      if (n.children) {
        n.children.forEach(updatePaths)
      }
    }

    updatePaths(node)

    // Insert the folder at the new location
    const pathParts = newPath.split("/").filter((p) => p !== "")
    let currentLevel = tree
    let currentPath = ""

    for (let i = 0; i < pathParts.length - 1; i++) {
      const part = pathParts[i]!
      currentPath = currentPath ? `${currentPath}/${part}` : part
      let folderNode = currentLevel.find((n) => n.name === part && n.type === "folder")
      if (!folderNode) {
        folderNode = { name: part, path: currentPath, type: "folder", children: [], loaded: false }
        currentLevel.push(folderNode)
        sortNodes(currentLevel)
      }
      if (!folderNode.children) folderNode.children = []
      currentLevel = folderNode.children
    }

    // Place the moved node
    const existingIndex = currentLevel.findIndex((n) => n.path === newPath)
    if (existingIndex >= 0) {
      currentLevel[existingIndex] = node
    } else {
      currentLevel.push(node)
      sortNodes(currentLevel)
    }
  }

  return true
}
