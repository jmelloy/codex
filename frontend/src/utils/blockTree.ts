import type { Block } from "../services/codex"

export interface BlockTreeNode {
  name: string
  path: string
  type: "leaf" | "page"
  block?: Block
  leafBlock?: Block
  children?: BlockTreeNode[]
  loaded?: boolean
  pageMeta?: {
    title?: string
    description?: string
    properties?: Record<string, any>
    block_count?: number
  }
  isPage?: boolean
  hasSubpages?: boolean
  blockOrder?: string[]
  block_id?: string
  block_type?: string
  parent_block_id?: string | null
  content_type?: string
  title?: string
}

/**
 * Convert a block tree (from GET /blocks/tree) into BlockTreeNode format.
 */
export function blockTreeToBlockTree(blocks: Block[]): BlockTreeNode[] {
  return blocks.map((block) => {
    const name = block.path.split("/").pop() || block.title || block.path
    const node: BlockTreeNode = {
      name: block.title || name,
      path: block.path,
      type: block.block_type === "page" ? "page" : "leaf",
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
      node.leafBlock = block
    } else {
      node.pageMeta = {
        title: block.title,
        description: block.description,
        properties: block.properties,
      }
      node.hasSubpages = block.children?.some((c) => c.block_type === "page") ?? false
    }

    if (block.children && block.children.length > 0) {
      node.children = blockTreeToBlockTree(block.children)
    } else if (block.block_type === "page") {
      node.children = []
    }

    return node
  })
}

/** Hidden metadata filenames that should not appear in the tree */
const HIDDEN_FILENAMES = new Set([".metadata", ".codex-page.json"])

/**
 * Sort nodes: pages first, then leaf blocks, both alphabetically
 */
function sortNodes(nodes: BlockTreeNode[]): void {
  nodes.sort((a, b) => {
    if (a.type !== b.type) {
      return a.type === "page" ? -1 : 1
    }
    return a.name.localeCompare(b.name)
  })
}

/**
 * Find a node in the tree by path
 */
export function findNode(tree: BlockTreeNode[], path: string): BlockTreeNode | null {
  const parts = path.split("/").filter((p) => p !== "")
  if (parts.length === 0) return null

  let currentLevel = tree
  let node: BlockTreeNode | null = null

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
 * Find the parent node for a given path
 */
export function findParentNode(tree: BlockTreeNode[], path: string): BlockTreeNode | null {
  const parts = path.split("/").filter((p) => p !== "")
  if (parts.length <= 1) return null
  const parentPath = parts.slice(0, -1).join("/")
  return findNode(tree, parentPath)
}

/**
 * Insert a leaf block node into the tree at the correct position
 */
export function insertBlockNode(tree: BlockTreeNode[], block: Block): void {
  const fname = block.filename || block.path.split("/").pop() || ""
  if (HIDDEN_FILENAMES.has(fname)) return

  const pathParts = block.path.split("/").filter((p) => p !== "")
  if (pathParts.length === 0) return

  let currentLevel = tree
  let currentPath = ""

  for (let i = 0; i < pathParts.length - 1; i++) {
    const part = pathParts[i]!
    currentPath = currentPath ? `${currentPath}/${part}` : part

    let pageNode = currentLevel.find((n) => n.name === part && n.type === "page")
    if (!pageNode) {
      pageNode = {
        name: part,
        path: currentPath,
        type: "page",
        children: [],
        loaded: false,
      }
      currentLevel.push(pageNode)
      sortNodes(currentLevel)
    }
    if (!pageNode.children) {
      pageNode.children = []
    }
    currentLevel = pageNode.children
  }

  const filename = pathParts[pathParts.length - 1]!
  const existingIndex = currentLevel.findIndex((n) => n.path === block.path)
  const blockNode: BlockTreeNode = {
    name: filename,
    path: block.path,
    type: "leaf",
    leafBlock: block,
  }

  if (existingIndex >= 0) {
    currentLevel[existingIndex] = blockNode
  } else {
    currentLevel.push(blockNode)
    sortNodes(currentLevel)
  }
}

/**
 * Remove a node from the tree by path
 */
export function removeNode(tree: BlockTreeNode[], path: string): boolean {
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
 * Update a leaf block node's metadata in the tree
 */
export function updateBlockNode(tree: BlockTreeNode[], block: Block): boolean {
  const node = findNode(tree, block.path)
  if (!node || node.type !== "leaf") return false
  node.leafBlock = block
  return true
}

/**
 * Get all leaf block metadata from the tree as a flat array
 */
export function getAllBlocks(tree: BlockTreeNode[]): Block[] {
  const blocks: Block[] = []

  function walk(nodes: BlockTreeNode[]) {
    for (const node of nodes) {
      if (node.type === "leaf" && node.leafBlock) {
        blocks.push(node.leafBlock)
      }
      if (node.children) {
        walk(node.children)
      }
    }
  }

  walk(tree)
  return blocks
}

/**
 * Move a node from one path to another
 */
export function moveNode(tree: BlockTreeNode[], oldPath: string, newPath: string): boolean {
  const node = findNode(tree, oldPath)
  if (!node) return false

  if (!removeNode(tree, oldPath)) return false

  if (node.type === "leaf" && node.leafBlock) {
    node.leafBlock = { ...node.leafBlock, path: newPath, filename: newPath.split("/").pop() || newPath }
    node.path = newPath
    node.name = newPath.split("/").pop() || newPath
    insertBlockNode(tree, node.leafBlock)
  } else {
    const oldPrefix = oldPath
    const newPrefix = newPath

    function updatePaths(n: BlockTreeNode) {
      if (n.path === oldPrefix) {
        n.path = newPrefix
      } else if (n.path.startsWith(oldPrefix + "/")) {
        n.path = newPrefix + n.path.substring(oldPrefix.length)
      }
      n.name = n.path.split("/").pop() || n.path
      if (n.leafBlock) {
        n.leafBlock = { ...n.leafBlock, path: n.path, filename: n.path.split("/").pop() || n.path }
      }
      if (n.children) {
        n.children.forEach(updatePaths)
      }
    }

    updatePaths(node)

    // Insert the page at the new location
    const pathParts = newPath.split("/").filter((p) => p !== "")
    let currentLevel = tree
    let currentPath = ""

    for (let i = 0; i < pathParts.length - 1; i++) {
      const part = pathParts[i]!
      currentPath = currentPath ? `${currentPath}/${part}` : part
      let pageNode = currentLevel.find((n) => n.name === part && n.type === "page")
      if (!pageNode) {
        pageNode = { name: part, path: currentPath, type: "page", children: [], loaded: false }
        currentLevel.push(pageNode)
        sortNodes(currentLevel)
      }
      if (!pageNode.children) pageNode.children = []
      currentLevel = pageNode.children
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
