import apiClient from "./api"

export interface Workspace {
  id: number
  name: string
  path: string
  slug: string // Extracted from path - last component
  owner_id: number
  theme_setting?: string
  created_at: string
  updated_at: string
}

export interface Notebook {
  id: number
  name: string
  path: string
  slug: string // Same as path - relative path from workspace
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
  directory_path: string // e.g., "experiment-log.page" or "protein-trial"
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

/**
 * Extract the slug from a workspace path.
 * The slug is the last component of the path.
 */
function extractWorkspaceSlug(workspace: Workspace): string {
  if (workspace.slug) return workspace.slug
  // Fallback: extract from path
  const parts = workspace.path.split("/")
  return parts[parts.length - 1] || ""
}

/**
 * Extract the slug from a notebook.
 * The notebook slug is its path (relative path from workspace).
 */
function extractNotebookSlug(notebook: Notebook): string {
  return notebook.slug || notebook.path
}

export const workspaceService = {
  async list(): Promise<Workspace[]> {
    const response = await apiClient.get<Workspace[]>("/api/v1/workspaces/")
    // Add slug field if not present (for backwards compatibility)
    return response.data.map((ws) => ({
      ...ws,
      slug: extractWorkspaceSlug(ws),
    }))
  },

  async get(slugOrId: string | number): Promise<Workspace> {
    // Support both slug (string) and ID (number) for backwards compatibility
    if (typeof slugOrId === "number") {
      // Legacy: get by ID
      const response = await apiClient.get<Workspace>(`/api/v1/workspaces/${slugOrId}`)
      return {
        ...response.data,
        slug: extractWorkspaceSlug(response.data),
      }
    }
    // New: get by slug
    const response = await apiClient.get<Workspace>(`/api/v1/${slugOrId}/`)
    return response.data
  },

  async create(name: string): Promise<Workspace> {
    const response = await apiClient.post<Workspace>("/api/v1/workspaces/", {
      name,
    })
    return {
      ...response.data,
      slug: extractWorkspaceSlug(response.data),
    }
  },

  async updateTheme(slugOrId: string | number, theme: string): Promise<Workspace> {
    if (typeof slugOrId === "number") {
      // Legacy: update by ID
      const response = await apiClient.patch<Workspace>(`/api/v1/workspaces/${slugOrId}/theme`, {
        theme,
      })
      return {
        ...response.data,
        slug: extractWorkspaceSlug(response.data),
      }
    }
    // New: update by slug
    const response = await apiClient.patch<Workspace>(`/api/v1/${slugOrId}/theme`, { theme })
    return response.data
  },
}

export const notebookService = {
  async list(workspaceSlug: string): Promise<Notebook[]> {
    const response = await apiClient.get<Notebook[]>(`/api/v1/${workspaceSlug}/notebooks`)
    return response.data.map((nb) => ({
      ...nb,
      slug: extractNotebookSlug(nb),
    }))
  },

  async get(workspaceSlug: string, notebookSlug: string): Promise<Notebook> {
    const response = await apiClient.get<Notebook>(`/api/v1/${workspaceSlug}/${notebookSlug}`)
    return response.data
  },

  async create(workspaceSlug: string, name: string, description?: string): Promise<Notebook> {
    const response = await apiClient.post<Notebook>(`/api/v1/${workspaceSlug}/notebooks`, {
      name,
      description,
    })
    return response.data
  },

  async getIndexingStatus(
    workspaceSlug: string,
    notebookSlug: string
  ): Promise<{ notebook_id: number; status: string; is_alive: boolean }> {
    const response = await apiClient.get(`/api/v1/${workspaceSlug}/${notebookSlug}/indexing-status`)
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
    return (
      text
        .toLowerCase()
        .replace(/[^\w\s-]/g, "")
        .replace(/[-\s]+/g, "-")
        .trim()
        .replace(/^-+|-+$/g, "") || "page"
    )
  },

  /**
   * List all pages in a notebook by scanning for page directories.
   */
  async list(workspaceSlug: string, notebookSlug: string): Promise<PageListItem[]> {
    // Get all files in the notebook
    const files = await fileService.list(workspaceSlug, notebookSlug)

    // Find all .page and .page.json files
    const pageFiles = files.filter((f) => f.filename === ".page" || f.filename === ".page.json")

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
          const content = await fileService.getContentByPath(workspaceSlug, notebookSlug, pageFile.path)
          const metadata = JSON.parse(content.content)

          // Count blocks in this directory
          const blockCount = files.filter(
            (f) => f.path.startsWith(dirPath + "/") && /^\d{3}-/.test(f.filename)
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
      if (pages.some((p) => p.directory_path === dirPath)) {
        continue
      }

      const blockCount = files.filter(
        (f) => f.path.startsWith(dirPath + "/") && /^\d{3}-/.test(f.filename)
      ).length

      let metadata: any = {}
      try {
        const pageFilePath = `${dirPath}/.page`
        const content = await fileService.getContentByPath(workspaceSlug, notebookSlug, pageFilePath)
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
  async get(
    workspaceSlug: string,
    notebookSlug: string,
    directoryPath: string
  ): Promise<PageWithBlocks> {
    let metadata: any = {}
    const pageFilePath = `${directoryPath}/.page`

    try {
      const content = await fileService.getContentByPath(workspaceSlug, notebookSlug, pageFilePath)
      metadata = JSON.parse(content.content)
    } catch (e) {
      try {
        const content = await fileService.getContentByPath(
          workspaceSlug,
          notebookSlug,
          `${directoryPath}/.page.json`
        )
        metadata = JSON.parse(content.content)
      } catch (e2) {
        // No metadata file
      }
    }

    const files = await fileService.list(workspaceSlug, notebookSlug)
    const blockFiles = files
      .filter((f) => f.path.startsWith(directoryPath + "/") && /^\d{3}-/.test(f.filename))
      .sort((a, b) => a.filename.localeCompare(b.filename))

    const blocks: Block[] = blockFiles.map((f) => {
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
  async create(
    _workspaceSlug: string,
    _notebookSlug: string,
    _title: string,
    _description?: string
  ): Promise<Page> {
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
    workspaceSlug: string,
    notebookSlug: string,
    directoryPath: string,
    title?: string,
    description?: string
  ): Promise<Page> {
    const pageFilePath = `${directoryPath}/.page`
    let metadata: any = {}

    try {
      const content = await fileService.getContentByPath(workspaceSlug, notebookSlug, pageFilePath)
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
  async delete(
    _workspaceSlug: string,
    _notebookSlug: string,
    _directoryPath: string
  ): Promise<void> {
    // TODO: Need backend endpoint to delete directory
    throw new Error("Deleting pages requires backend directory deletion support")
  },

  /**
   * Create a block (numbered file) in the page.
   */
  async createBlock(
    _workspaceSlug: string,
    _notebookSlug: string,
    _directoryPath: string,
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
    _workspaceSlug: string,
    _notebookSlug: string,
    _directoryPath: string,
    _blocks: { file: string; new_position: number }[]
  ): Promise<void> {
    // TODO: Need backend endpoint to rename files
    throw new Error("Reordering blocks requires backend file rename support")
  },

  /**
   * Delete a block file.
   */
  async deleteBlock(
    _workspaceSlug: string,
    _notebookSlug: string,
    _directoryPath: string,
    _blockFilename: string
  ): Promise<void> {
    // TODO: Need backend endpoint to delete file by path
    throw new Error("Deleting blocks requires backend file deletion support")
  },
}

export const fileService = {
  async list(workspaceSlug: string, notebookSlug: string): Promise<FileMetadata[]> {
    const response = await apiClient.get<{ files: FileMetadata[]; pagination: any }>(
      `/api/v1/${workspaceSlug}/${notebookSlug}/files`
    )
    // For backwards compatibility, return just the files array
    // The frontend currently loads all files at once for the tree
    return response.data.files || response.data
  },

  /**
   * Get file metadata by path (without content).
   * Use getContent() to fetch the file content separately.
   */
  async get(workspaceSlug: string, notebookSlug: string, filePath: string): Promise<FileMetadata> {
    const encodedPath = encodeURIComponent(filePath)
    const response = await apiClient.get<FileMetadata>(
      `/api/v1/${workspaceSlug}/${notebookSlug}/files/${encodedPath}`
    )
    return response.data
  },

  /**
   * Get text content for a file by path.
   * For markdown files, returns body content without frontmatter.
   * For view files (.cdx), returns raw content including frontmatter.
   */
  async getContent(
    workspaceSlug: string,
    notebookSlug: string,
    filePath: string
  ): Promise<FileTextContent> {
    const encodedPath = encodeURIComponent(filePath)
    const response = await apiClient.get<FileTextContent>(
      `/api/v1/${workspaceSlug}/${notebookSlug}/files/${encodedPath}/text`
    )
    return response.data
  },

  /**
   * Alias for getContent - get text content by path.
   */
  async getContentByPath(
    workspaceSlug: string,
    notebookSlug: string,
    filePath: string
  ): Promise<FileTextContent> {
    return this.getContent(workspaceSlug, notebookSlug, filePath)
  },

  /**
   * Get the content URL for a file by path (for binary files like images).
   */
  getContentUrl(workspaceSlug: string, notebookSlug: string, filePath: string): string {
    const encodedPath = encodeURIComponent(filePath)
    return `/api/v1/${workspaceSlug}/${notebookSlug}/files/${encodedPath}/content`
  },

  /**
   * Alias for getContentUrl.
   */
  getContentUrlByPath(workspaceSlug: string, notebookSlug: string, filePath: string): string {
    return this.getContentUrl(workspaceSlug, notebookSlug, filePath)
  },

  /**
   * Resolve a link to a file, supporting relative paths and filenames.
   */
  async resolveLink(
    workspaceSlug: string,
    notebookSlug: string,
    link: string,
    currentFilePath?: string
  ): Promise<FileMetadata & { resolved_path: string }> {
    const response = await apiClient.post<FileMetadata & { resolved_path: string }>(
      `/api/v1/${workspaceSlug}/${notebookSlug}/files/resolve-link`,
      {
        link,
        current_file_path: currentFilePath,
      }
    )
    return response.data
  },

  async create(
    workspaceSlug: string,
    notebookSlug: string,
    path: string,
    content: string
  ): Promise<FileMetadata> {
    const response = await apiClient.post<FileMetadata>(
      `/api/v1/${workspaceSlug}/${notebookSlug}/files`,
      {
        path,
        content,
      }
    )
    return response.data
  },

  async update(
    workspaceSlug: string,
    notebookSlug: string,
    filePath: string,
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
    const encodedPath = encodeURIComponent(filePath)
    const response = await apiClient.put<FileMetadata>(
      `/api/v1/${workspaceSlug}/${notebookSlug}/files/${encodedPath}`,
      body
    )
    return response.data
  },

  async delete(workspaceSlug: string, notebookSlug: string, filePath: string): Promise<void> {
    const encodedPath = encodeURIComponent(filePath)
    await apiClient.delete(`/api/v1/${workspaceSlug}/${notebookSlug}/files/${encodedPath}`)
  },

  async upload(
    workspaceSlug: string,
    notebookSlug: string,
    file: File,
    path?: string
  ): Promise<FileMetadata> {
    const formData = new FormData()
    formData.append("file", file)
    if (path) {
      formData.append("path", path)
    }
    const response = await apiClient.post<FileMetadata>(
      `/api/v1/${workspaceSlug}/${notebookSlug}/files/upload`,
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
    workspaceSlug: string,
    notebookSlug: string,
    filePath: string,
    newPath: string
  ): Promise<FileMetadata> {
    const encodedPath = encodeURIComponent(filePath)
    const response = await apiClient.patch<FileMetadata>(
      `/api/v1/${workspaceSlug}/${notebookSlug}/files/${encodedPath}/move`,
      { new_path: newPath }
    )
    return response.data
  },

  /**
   * Get git history for a file.
   */
  async getHistory(
    workspaceSlug: string,
    notebookSlug: string,
    filePath: string,
    maxCount: number = 20
  ): Promise<FileHistory> {
    const encodedPath = encodeURIComponent(filePath)
    const response = await apiClient.get<FileHistory>(
      `/api/v1/${workspaceSlug}/${notebookSlug}/files/${encodedPath}/history?max_count=${maxCount}`
    )
    return response.data
  },

  /**
   * Get file content at a specific commit.
   */
  async getAtCommit(
    workspaceSlug: string,
    notebookSlug: string,
    filePath: string,
    commitHash: string
  ): Promise<FileAtCommit> {
    const encodedPath = encodeURIComponent(filePath)
    const response = await apiClient.get<FileAtCommit>(
      `/api/v1/${workspaceSlug}/${notebookSlug}/files/${encodedPath}/history/${commitHash}`
    )
    return response.data
  },
}

export const templateService = {
  /**
   * List available templates for a notebook.
   */
  async list(_workspaceSlug: string, _notebookSlug: string): Promise<Template[]> {
    // Templates are still accessed via the old endpoint for now
    // This could be migrated to a new slug-based endpoint later
    const response = await apiClient.get<{ templates: Template[] }>(
      `/api/v1/files/templates?notebook_id=0&workspace_id=0`
    )
    return response.data.templates
  },

  /**
   * Create a file from a template.
   */
  async createFromTemplate(
    _workspaceSlug: string,
    _notebookSlug: string,
    templateId: string,
    filename?: string
  ): Promise<FileMetadata> {
    // For now, use the old endpoint - this would need a new v2 endpoint
    const response = await apiClient.post<FileMetadata>("/api/v1/files/from-template", {
      notebook_id: 0, // Will need to be resolved
      workspace_id: 0, // Will need to be resolved
      template_id: templateId,
      filename: filename || null,
    })
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
  async get(
    workspaceSlug: string,
    notebookSlug: string,
    folderPath: string
  ): Promise<FolderWithFiles> {
    const encodedPath = encodeURIComponent(folderPath)
    const response = await apiClient.get<FolderWithFiles>(
      `/api/v1/${workspaceSlug}/${notebookSlug}/folders/${encodedPath}`
    )
    return response.data
  },

  /**
   * Update folder properties.
   * This updates the .metadata file within the folder.
   */
  async updateProperties(
    workspaceSlug: string,
    notebookSlug: string,
    folderPath: string,
    properties: Record<string, any>
  ): Promise<FolderMetadata> {
    const encodedPath = encodeURIComponent(folderPath)
    const response = await apiClient.put<FolderMetadata>(
      `/api/v1/${workspaceSlug}/${notebookSlug}/folders/${encodedPath}`,
      { properties }
    )
    return response.data
  },

  /**
   * Delete a folder and all its contents.
   */
  async delete(workspaceSlug: string, notebookSlug: string, folderPath: string): Promise<void> {
    const encodedPath = encodeURIComponent(folderPath)
    await apiClient.delete(`/api/v1/${workspaceSlug}/${notebookSlug}/folders/${encodedPath}`)
  },
}

export const searchService = {
  async search(workspaceSlug: string, query: string): Promise<any> {
    const response = await apiClient.get(`/api/v1/${workspaceSlug}/search?q=${query}`)
    return response.data
  },

  async searchByTags(workspaceSlug: string, tags: string[]): Promise<any> {
    const response = await apiClient.get(
      `/api/v1/${workspaceSlug}/search/tags?tags=${tags.join(",")}`
    )
    return response.data
  },
}

export const taskService = {
  async list(workspaceSlug: string): Promise<any[]> {
    const response = await apiClient.get(`/api/v1/${workspaceSlug}/tasks`)
    return response.data
  },

  async get(workspaceSlug: string, taskId: number): Promise<any> {
    const response = await apiClient.get(`/api/v1/${workspaceSlug}/tasks/${taskId}`)
    return response.data
  },

  async create(workspaceSlug: string, title: string, description?: string): Promise<any> {
    const response = await apiClient.post(
      `/api/v1/${workspaceSlug}/tasks?title=${encodeURIComponent(title)}${description ? `&description=${encodeURIComponent(description)}` : ""}`
    )
    return response.data
  },

  async update(
    workspaceSlug: string,
    taskId: number,
    status?: string,
    assignedTo?: string
  ): Promise<any> {
    const params = new URLSearchParams()
    if (status) params.append("status", status)
    if (assignedTo) params.append("assigned_to", assignedTo)
    const response = await apiClient.put(
      `/api/v1/${workspaceSlug}/tasks/${taskId}?${params.toString()}`
    )
    return response.data
  },
}
