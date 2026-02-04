import apiClient from "./api"

export interface Workspace {
  id: number
  slug?: string
  name: string
  path: string
  owner_id: number
  theme_setting?: string
  created_at: string
  updated_at: string
}

export interface Notebook {
  id: number
  slug?: string
  name: string
  path: string
  description?: string
  created_at: string
  updated_at: string
}

export interface FileMetadata {
  id: number
  notebook_id: number
  path: string
  filename: string
  content_type: string // MIME type (e.g., text/markdown, image/jpeg)
  size: number
  title?: string
  description?: string
  properties?: Record<string, any> // Unified properties from frontmatter
  created_at: string
  updated_at: string
}

export interface FileWithContent extends FileMetadata {
  content: string
}

export interface FileTextContent {
  id: number
  content: string
  properties?: Record<string, any>
}

export interface FolderMetadata {
  path: string
  name: string
  notebook_id: number
  title?: string
  description?: string
  properties?: Record<string, any>
  file_count: number
  created_at?: string
  updated_at?: string
}

export interface SubfolderMetadata {
  path: string
  name: string
  title?: string
  description?: string
  properties?: Record<string, any>
  created_at?: string
  updated_at?: string
}

export interface FolderWithFiles extends FolderMetadata {
  files: FileMetadata[]
  subfolders?: SubfolderMetadata[]
}
export interface FileHistoryEntry {
  hash: string
  author: string
  date: string
  message: string
}

export interface FileHistory {
  file_id: number
  path: string
  history: FileHistoryEntry[]
}

export interface FileAtCommit {
  file_id: number
  path: string
  commit_hash: string
  content: string
}

export interface Template {
  id: string
  name: string
  description: string
  icon: string
  file_extension: string
  default_name: string
  content: string
  source: "default" | "notebook"
}

export interface Page {
  directory_path: string  // e.g., "experiment-log.page" or "protein-trial"
  title?: string
  description?: string
  created_at?: string
  updated_at?: string
}

export interface PageListItem extends Page {
  block_count: number
}

export interface Block {
  position: number
  file: string
  name: string
  type: string
  path: string
}

export interface PageWithBlocks extends Page {
  blocks: Block[]
}

export const workspaceService = {
  async list(): Promise<Workspace[]> {
    const response = await apiClient.get<Workspace[]>("/api/v1/workspaces/")
    return response.data
  },

  async get(identifier: number | string): Promise<Workspace> {
    const response = await apiClient.get<Workspace>(`/api/v1/workspaces/${identifier}`)
    return response.data
  },

  async create(name: string): Promise<Workspace> {
    const response = await apiClient.post<Workspace>("/api/v1/workspaces/", {
      name,
    })
    return response.data
  },

  async updateTheme(identifier: number | string, theme: string): Promise<Workspace> {
    const response = await apiClient.patch<Workspace>(`/api/v1/workspaces/${identifier}/theme`, { theme })
    return response.data
  },
}

export const notebookService = {
  async list(workspaceIdentifier: number | string): Promise<Notebook[]> {
    const response = await apiClient.get<Notebook[]>(
      `/api/v1/workspaces/${workspaceIdentifier}/notebooks/`
    )
    return response.data
  },

  async get(workspaceIdentifier: number | string, notebookIdentifier: number | string): Promise<Notebook> {
    const response = await apiClient.get<Notebook>(
      `/api/v1/workspaces/${workspaceIdentifier}/notebooks/${notebookIdentifier}`
    )
    return response.data
  },

  async create(workspaceIdentifier: number | string, name: string, description?: string): Promise<Notebook> {
    const response = await apiClient.post<Notebook>(
      `/api/v1/workspaces/${workspaceIdentifier}/notebooks/`,
      {
        name,
        description,
      }
    )
    return response.data
  },
}

export const pageService = {
  /**
   * Helper to check if a path looks like a page directory.
   */
  _isPageDirectory(path: string): boolean {
    return path.endsWith(".page")
  },

  /**
   * Helper to get display name (remove .page suffix).
   */
  _getDisplayName(path: string): string {
    if (path.endsWith(".page")) {
      return path.slice(0, -5)
    }
    return path
  },

  /**
   * Helper to slugify a title for directory name.
   */
  _slugify(text: string): string {
    return text
      .toLowerCase()
      .replace(/[^\w\s-]/g, "")
      .replace(/[-\s]+/g, "-")
      .trim()
      .replace(/^-+|-+$/g, "") || "page"
  },

  /**
   * List all pages in a notebook by scanning for page directories.
   */
  async list(notebookId: number, workspaceId: number): Promise<PageListItem[]> {
    // Get all files in the notebook
    const files = await fileService.list(notebookId, workspaceId)
    
    // Find all .page and .page.json files
    const pageFiles = files.filter(f => 
      f.filename === ".page" || f.filename === ".page.json"
    )
    
    // Also find directories with .page suffix
    const pageDirs = new Set<string>()
    for (const file of files) {
      const parts = file.path.split("/")
      for (let i = 0; i < parts.length; i++) {
        const part = parts[i]
        if (part && part.endsWith(".page")) {
          pageDirs.add(parts.slice(0, i + 1).join("/"))
        }
      }
    }
    
    // Build page list
    const pages: PageListItem[] = []
    
    // Add pages from .page files
    for (const pageFile of pageFiles) {
      const dirPath = pageFile.path.substring(0, pageFile.path.lastIndexOf("/"))
      if (dirPath) {
        try {
          const content = await fileService.getContentByPath(pageFile.path, workspaceId, notebookId)
          const metadata = JSON.parse(content.content)
          
          // Count blocks in this directory
          const blockCount = files.filter(f => 
            f.path.startsWith(dirPath + "/") && 
            /^\d{3}-/.test(f.filename)
          ).length
          
          pages.push({
            directory_path: dirPath,
            title: metadata.title || this._getDisplayName(dirPath),
            description: metadata.description,
            created_at: metadata.created_time,
            updated_at: metadata.last_edited_time,
            block_count: blockCount,
          })
        } catch (e) {
          console.error(`Failed to read page metadata for ${pageFile.path}:`, e)
        }
      }
    }
    
    // Add pages from .page suffix directories  
    for (const dirPath of pageDirs) {
      if (pages.some(p => p.directory_path === dirPath)) {
        continue
      }
      
      const blockCount = files.filter(f => 
        f.path.startsWith(dirPath + "/") && 
        /^\d{3}-/.test(f.filename)
      ).length
      
      let metadata: any = {}
      try {
        const pageFilePath = `${dirPath}/.page`
        const content = await fileService.getContentByPath(pageFilePath, workspaceId, notebookId)
        metadata = JSON.parse(content.content)
      } catch (e) {
        // No metadata file
      }
      
      pages.push({
        directory_path: dirPath,
        title: metadata.title || this._getDisplayName(dirPath),
        description: metadata.description,
        created_at: metadata.created_time,
        updated_at: metadata.last_edited_time,
        block_count: blockCount,
      })
    }
    
    return pages
  },

  /**
   * Get page details with blocks.
   */
  async get(directoryPath: string, notebookId: number, workspaceId: number): Promise<PageWithBlocks> {
    let metadata: any = {}
    const pageFilePath = `${directoryPath}/.page`
    
    try {
      const content = await fileService.getContentByPath(pageFilePath, workspaceId, notebookId)
      metadata = JSON.parse(content.content)
    } catch (e) {
      try {
        const content = await fileService.getContentByPath(`${directoryPath}/.page.json`, workspaceId, notebookId)
        metadata = JSON.parse(content.content)
      } catch (e2) {
        // No metadata file
      }
    }
    
    const files = await fileService.list(notebookId, workspaceId)
    const blockFiles = files
      .filter(f => f.path.startsWith(directoryPath + "/") && /^\d{3}-/.test(f.filename))
      .sort((a, b) => a.filename.localeCompare(b.filename))
    
    const blocks: Block[] = blockFiles.map(f => {
      const match = f.filename.match(/^(\d{3})-(.+)$/)
      const position = match && match[1] ? parseInt(match[1]) : 0
      const name = match && match[2] ? match[2] : f.filename
      const type = f.filename.match(/\.(md|markdown)$/i) ? "markdown" : "file"
      
      return {
        position,
        file: f.filename,
        name,
        type,
        path: f.path,
      }
    })
    
    return {
      directory_path: directoryPath,
      title: metadata.title || this._getDisplayName(directoryPath),
      description: metadata.description,
      created_at: metadata.created_time,
      updated_at: metadata.last_edited_time,
      blocks,
    }
  },

  /**
   * Create a new page directory with .page metadata file.
   * Note: This requires backend support for creating directories and files.
   */
  async create(_notebookId: number, _workspaceId: number, _title: string, _description?: string): Promise<Page> {
    // Future implementation would:
    // 1. Create slug from title
    // 2. Create directory with .page suffix
    // 3. Create .page file with metadata
    
    // TODO: Need backend endpoint to create directory and file
    throw new Error("Creating pages requires backend directory creation support")
  },

  /**
   * Update page metadata by updating the .page file.
   */
  async update(
    directoryPath: string,
    notebookId: number,
    workspaceId: number,
    title?: string,
    description?: string
  ): Promise<Page> {
    const pageFilePath = `${directoryPath}/.page`
    let metadata: any = {}
    
    try {
      const content = await fileService.getContentByPath(pageFilePath, workspaceId, notebookId)
      metadata = JSON.parse(content.content)
    } catch (e) {
      // Create new metadata if doesn't exist
    }
    
    if (title !== undefined) metadata.title = title
    if (description !== undefined) metadata.description = description
    metadata.last_edited_time = new Date().toISOString()
    
    // TODO: Need backend endpoint to update file content by path
    throw new Error("Updating pages requires backend file update support")
  },

  /**
   * Delete a page by deleting the directory.
   */
  async delete(_directoryPath: string, _notebookId: number, _workspaceId: number): Promise<void> {
    // TODO: Need backend endpoint to delete directory
    throw new Error("Deleting pages requires backend directory deletion support")
  },

  /**
   * Create a block (numbered file) in the page.
   */
  async createBlock(
    _directoryPath: string,
    _notebookId: number,
    _workspaceId: number,
    _filename: string
  ): Promise<Block> {
    // Future implementation would:
    // 1. Get current page and find next position number
    // 2. Create file with pattern: NNN-filename
    
    // TODO: Need backend endpoint to create file at specific path
    throw new Error("Creating blocks requires backend file creation support")
  },

  /**
   * Reorder blocks by renaming files.
   */
  async reorderBlocks(
    _directoryPath: string,
    _notebookId: number,
    _workspaceId: number,
    _blocks: { file: string; new_position: number }[]
  ): Promise<void> {
    // TODO: Need backend endpoint to rename files
    throw new Error("Reordering blocks requires backend file rename support")
  },

  /**
   * Delete a block file.
   */
  async deleteBlock(
    _directoryPath: string,
    _notebookId: number,
    _workspaceId: number,
    _blockFilename: string
  ): Promise<void> {
    // TODO: Need backend endpoint to delete file by path
    throw new Error("Deleting blocks requires backend file deletion support")
  },
}


export const fileService = {
  async list(notebookId: number | string, workspaceId: number | string): Promise<FileMetadata[]> {
    const response = await apiClient.get<{ files: FileMetadata[]; pagination: any }>(
      `/api/v1/workspaces/${workspaceId}/notebooks/${notebookId}/files/`
    )
    // For backwards compatibility, return just the files array
    // The frontend currently loads all files at once for the tree
    return response.data.files || response.data
  },

  /**
   * Get file metadata (without content).
   * Use getContent() to fetch the file content separately.
   */
  async get(id: number, workspaceId: number | string, notebookId: number | string): Promise<FileMetadata> {
    const response = await apiClient.get<FileMetadata>(
      `/api/v1/workspaces/${workspaceId}/notebooks/${notebookId}/files/${id}`
    )
    return response.data
  },

  /**
   * Get text content for a file.
   * For markdown files, returns body content without frontmatter.
   * For view files (.cdx), returns raw content including frontmatter.
   */
  async getContent(id: number, workspaceId: number | string, notebookId: number | string): Promise<FileTextContent> {
    const response = await apiClient.get<FileTextContent>(
      `/api/v1/workspaces/${workspaceId}/notebooks/${notebookId}/files/${id}/text`
    )
    return response.data
  },

  /**
   * Get file metadata by its path or filename (without content).
   * Supports exact path match or filename-only search.
   * Use getContentByPath() to fetch content separately.
   */
  async getByPath(path: string, workspaceId: number | string, notebookId: number | string): Promise<FileMetadata> {
    const encodedPath = encodeURIComponent(path)
    const response = await apiClient.get<FileMetadata>(
      `/api/v1/workspaces/${workspaceId}/notebooks/${notebookId}/files/path/${encodedPath}`
    )
    return response.data
  },

  /**
   * Get text content for a file by its path or filename.
   */
  async getContentByPath(
    path: string,
    workspaceId: number | string,
    notebookId: number | string
  ): Promise<FileTextContent> {
    const encodedPath = encodeURIComponent(path)
    const response = await apiClient.get<FileTextContent>(
      `/api/v1/workspaces/${workspaceId}/notebooks/${notebookId}/files/path/${encodedPath}/text`
    )
    return response.data
  },

  /**
   * Get the content URL for a file by path (for binary files like images).
   */
  getContentUrlByPath(path: string, workspaceId: number | string, notebookId: number | string): string {
    const encodedPath = encodeURIComponent(path)
    return `/api/v1/workspaces/${workspaceId}/notebooks/${notebookId}/files/path/${encodedPath}/content`
  },

  /**
   * Get the content URL for a file by ID (for binary files like images).
   */
  getContentUrl(id: number, workspaceId: number | string, notebookId: number | string): string {
    return `/api/v1/workspaces/${workspaceId}/notebooks/${notebookId}/files/${id}/content`
  },

  /**
   * Resolve a link to a file, supporting relative paths and filenames.
   */
  async resolveLink(
    link: string,
    workspaceId: number | string,
    notebookId: number | string,
    currentFilePath?: string
  ): Promise<FileMetadata & { resolved_path: string }> {
    const response = await apiClient.post<FileMetadata & { resolved_path: string }>(
      `/api/v1/workspaces/${workspaceId}/notebooks/${notebookId}/files/resolve-link`,
      {
        link,
        current_file_path: currentFilePath,
      }
    )
    return response.data
  },

  async create(
    notebookId: number | string,
    workspaceId: number | string,
    path: string,
    content: string
  ): Promise<FileMetadata> {
    const response = await apiClient.post<FileMetadata>(
      `/api/v1/workspaces/${workspaceId}/notebooks/${notebookId}/files/`, 
      {
        path,
        content,
      }
    )
    return response.data
  },

  async update(
    id: number,
    workspaceId: number | string,
    notebookId: number | string,
    content?: string | null,
    properties?: Record<string, any>
  ): Promise<FileMetadata> {
    // Only include content in body if it's a string (not null/undefined)
    // This allows updating just properties on binary files like images
    const body: { content?: string; properties?: Record<string, any> } = {}
    if (typeof content === "string") {
      body.content = content
    }
    if (properties !== undefined) {
      body.properties = properties
    }
    const response = await apiClient.put<FileMetadata>(
      `/api/v1/workspaces/${workspaceId}/notebooks/${notebookId}/files/${id}`,
      body
    )
    return response.data
  },

  async delete(id: number, workspaceId: number | string, notebookId: number | string): Promise<void> {
    await apiClient.delete(`/api/v1/workspaces/${workspaceId}/notebooks/${notebookId}/files/${id}`)
  },

  async upload(
    notebookId: number | string,
    workspaceId: number | string,
    file: File,
    path?: string
  ): Promise<FileMetadata> {
    const formData = new FormData()
    formData.append("file", file)
    if (path) {
      formData.append("path", path)
    }
    const response = await apiClient.post<FileMetadata>(
      `/api/v1/workspaces/${workspaceId}/notebooks/${notebookId}/files/upload`,
      formData,
      {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      }
    )
    return response.data
  },

  async move(
    id: number,
    workspaceId: number | string,
    notebookId: number | string,
    newPath: string
  ): Promise<FileMetadata> {
    const response = await apiClient.patch<FileMetadata>(
      `/api/v1/workspaces/${workspaceId}/notebooks/${notebookId}/files/${id}/move`,
      { new_path: newPath }
    )
    return response.data
  },

  /**
   * Get git history for a file.
   */
  async getHistory(
    id: number,
    workspaceId: number | string,
    notebookId: number | string,
    maxCount: number = 20
  ): Promise<FileHistory> {
    const response = await apiClient.get<FileHistory>(
      `/api/v1/workspaces/${workspaceId}/notebooks/${notebookId}/files/${id}/history?max_count=${maxCount}`
    )
    return response.data
  },

  /**
   * Get file content at a specific commit.
   */
  async getAtCommit(
    id: number,
    workspaceId: number | string,
    notebookId: number | string,
    commitHash: string
  ): Promise<FileAtCommit> {
    const response = await apiClient.get<FileAtCommit>(
      `/api/v1/workspaces/${workspaceId}/notebooks/${notebookId}/files/${id}/history/${commitHash}`
    )
    return response.data
  },
}

export const templateService = {
  /**
   * List available templates for a notebook.
   */
  async list(notebookId: number | string, workspaceId: number | string): Promise<Template[]> {
    const response = await apiClient.get<{ templates: Template[] }>(
      `/api/v1/workspaces/${workspaceId}/notebooks/${notebookId}/files/templates`
    )
    return response.data.templates
  },

  /**
   * Create a file from a template.
   */
  async createFromTemplate(
    notebookId: number | string,
    workspaceId: number | string,
    templateId: string,
    filename?: string
  ): Promise<FileMetadata> {
    const response = await apiClient.post<FileMetadata>(
      `/api/v1/workspaces/${workspaceId}/notebooks/${notebookId}/files/from-template`,
      {
        template_id: templateId,
        filename: filename || null,
      }
    )
    return response.data
  },

  /**
   * Expand date patterns in a string (client-side preview).
   */
  expandPattern(pattern: string, title: string = "untitled"): string {
    const now = new Date()
    const yyyy = now.getFullYear().toString()
    const yy = yyyy.slice(-2)
    const mm = String(now.getMonth() + 1).padStart(2, "0")
    const dd = String(now.getDate()).padStart(2, "0")
    const monthNames: readonly string[] = [
      "January",
      "February",
      "March",
      "April",
      "May",
      "June",
      "July",
      "August",
      "September",
      "October",
      "November",
      "December",
    ] as const
    const month = monthNames[now.getMonth()] ?? "January"
    const mon = month.slice(0, 3)

    return pattern
      .replace(/{yyyy}/g, yyyy)
      .replace(/{yy}/g, yy)
      .replace(/{mm}/g, mm)
      .replace(/{dd}/g, dd)
      .replace(/{month}/g, month)
      .replace(/{mon}/g, mon)
      .replace(/{title}/g, title)
  },
}

export const folderService = {
  /**
   * Get folder metadata and contents.
   * The folder metadata is stored in a .metadata file within the folder.
   */
  async get(path: string, notebookId: number | string, workspaceId: number | string): Promise<FolderWithFiles> {
    const encodedPath = encodeURIComponent(path)
    const response = await apiClient.get<FolderWithFiles>(
      `/api/v1/workspaces/${workspaceId}/notebooks/${notebookId}/folders/${encodedPath}`
    )
    return response.data
  },

  /**
   * Update folder properties.
   * This updates the .metadata file within the folder.
   */
  async updateProperties(
    path: string,
    notebookId: number | string,
    workspaceId: number | string,
    properties: Record<string, any>
  ): Promise<FolderMetadata> {
    const encodedPath = encodeURIComponent(path)
    const response = await apiClient.put<FolderMetadata>(
      `/api/v1/workspaces/${workspaceId}/notebooks/${notebookId}/folders/${encodedPath}`,
      { properties }
    )
    return response.data
  },

  /**
   * Delete a folder and all its contents.
   */
  async delete(path: string, notebookId: number | string, workspaceId: number | string): Promise<void> {
    const encodedPath = encodeURIComponent(path)
    await apiClient.delete(
      `/api/v1/workspaces/${workspaceId}/notebooks/${notebookId}/folders/${encodedPath}`
    )
  },
}

export const searchService = {
  /**
   * Search files and content across all notebooks in a workspace.
   */
  async search(workspaceId: number | string, query: string): Promise<any> {
    const response = await apiClient.get(`/api/v1/workspaces/${workspaceId}/search/?q=${query}`)
    return response.data
  },

  /**
   * Search files and content in a specific notebook.
   */
  async searchInNotebook(workspaceId: number | string, notebookId: number | string, query: string): Promise<any> {
    const response = await apiClient.get(
      `/api/v1/workspaces/${workspaceId}/notebooks/${notebookId}/search/?q=${query}`
    )
    return response.data
  },

  /**
   * Search by tags across all notebooks in a workspace.
   */
  async searchByTags(workspaceId: number | string, tags: string[]): Promise<any> {
    const response = await apiClient.get(
      `/api/v1/workspaces/${workspaceId}/search/tags?tags=${tags.join(",")}`
    )
    return response.data
  },

  /**
   * Search by tags in a specific notebook.
   */
  async searchByTagsInNotebook(
    workspaceId: number | string,
    notebookId: number | string,
    tags: string[]
  ): Promise<any> {
    const response = await apiClient.get(
      `/api/v1/workspaces/${workspaceId}/notebooks/${notebookId}/search/tags?tags=${tags.join(",")}`
    )
    return response.data
  },
}

