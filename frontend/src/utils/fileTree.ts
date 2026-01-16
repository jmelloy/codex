import type { FileMetadata } from '../services/codex'

export interface FileTreeNode {
  name: string
  path: string
  type: 'file' | 'folder'
  file?: FileMetadata
  children?: FileTreeNode[]
}

/**
 * Build a hierarchical tree structure from a flat list of files
 */
export function buildFileTree(files: FileMetadata[]): FileTreeNode[] {
  const root: FileTreeNode[] = []
  
  // Create a map to track folders we've already created
  const folderMap = new Map<string, FileTreeNode>()
  
  // Sort files by path to ensure consistent ordering
  const sortedFiles = [...files].sort((a, b) => a.path.localeCompare(b.path))
  
  for (const file of sortedFiles) {
    const pathParts = file.path.split('/').filter(part => part !== '')
    if (pathParts.length === 0) continue
    
    let currentLevel = root
    let currentPath = ''
    
    // Process each part of the path except the last (which is the filename)
    for (let i = 0; i < pathParts.length - 1; i++) {
      const part = pathParts[i]!  // Safe because we're iterating within bounds
      currentPath = currentPath ? `${currentPath}/${part}` : part
      
      // Check if this folder already exists at current level
      let folderNode = folderMap.get(currentPath)
      
      if (!folderNode) {
        // Create new folder node
        folderNode = {
          name: part,
          path: currentPath,
          type: 'folder',
          children: []
        }
        
        currentLevel.push(folderNode)
        folderMap.set(currentPath, folderNode)
      }
      
      // Move to next level
      currentLevel = folderNode.children!
    }
    
    // Add the file itself
    const filename = pathParts[pathParts.length - 1]
    if (filename) {
      currentLevel.push({
        name: filename,
        path: file.path,
        type: 'file',
        file: file
      })
    }
  }
  
  // Sort each level: folders first, then files, both alphabetically
  const sortLevel = (nodes: FileTreeNode[]) => {
    nodes.sort((a, b) => {
      if (a.type !== b.type) {
        return a.type === 'folder' ? -1 : 1
      }
      return a.name.localeCompare(b.name)
    })
    
    // Recursively sort children
    nodes.forEach(node => {
      if (node.children) {
        sortLevel(node.children)
      }
    })
  }
  
  sortLevel(root)
  return root
}
