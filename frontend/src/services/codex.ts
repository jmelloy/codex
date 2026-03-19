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
  is_page?: boolean
  block_order?: string[]
}

export interface Block {
  id: number
  block_id: string
  parent_block_id: string | null
  notebook_id: number
  path: string
  block_type:
    | "page"
    | "text"
    | "heading"
    | "code"
    | "image"
    | "list"
    | "quote"
    | "divider"
    | "embed"
    | "file"
  content_format: "markdown" | "json" | "binary"
  order_index: number
  title?: string
  file_id?: number
  content?: string
  created_at: string
  updated_at: string
}

export interface PageMetadata {
  version: number
  block_id: string
  path?: string
  title: string
  description?: string
  properties?: Record<string, any>
  blocks: Array<{
    block_id: string
    type: string
    file: string
    order: number
  }>
}

export interface BlockWithChildren extends Block {
  children?: Block[]
  page_metadata?: PageMetadata
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

  async delete(identifier: number | string): Promise<void> {
    await apiClient.delete(`/api/v1/workspaces/${identifier}`)
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

  async delete(workspaceIdentifier: number | string, notebookIdentifier: number | string): Promise<void> {
    await apiClient.delete(`/api/v1/workspaces/${workspaceIdentifier}/notebooks/${notebookIdentifier}`)
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

export const blockService = {
  /**
   * List root-level blocks/pages in a notebook.
   */
  async listRootBlocks(
    notebookId: number | string,
    workspaceId: number | string
  ): Promise<{ blocks: Block[]; notebook_id: number; workspace_id: number }> {
    const response = await apiClient.get(
      `/api/v1/workspaces/${workspaceId}/notebooks/${notebookId}/blocks/`
    )
    return response.data
  },

  /**
   * Get a single block with metadata and content.
   */
  async getBlock(
    blockId: string,
    notebookId: number | string,
    workspaceId: number | string
  ): Promise<BlockWithChildren> {
    const response = await apiClient.get<BlockWithChildren>(
      `/api/v1/workspaces/${workspaceId}/notebooks/${notebookId}/blocks/${blockId}`
    )
    return response.data
  },

  /**
   * Get ordered children of a page block.
   */
  async getChildren(
    blockId: string,
    notebookId: number | string,
    workspaceId: number | string
  ): Promise<{ parent_block_id: string; children: Block[] }> {
    const response = await apiClient.get(
      `/api/v1/workspaces/${workspaceId}/notebooks/${notebookId}/blocks/${blockId}/children`
    )
    return response.data
  },

  /**
   * Create a new block within a page.
   */
  async createBlock(
    notebookId: number | string,
    workspaceId: number | string,
    data: {
      parent_block_id: string
      block_type?: string
      content?: string
      position?: number
      content_format?: string
    }
  ): Promise<Block> {
    const response = await apiClient.post<Block>(
      `/api/v1/workspaces/${workspaceId}/notebooks/${notebookId}/blocks/`,
      data
    )
    return response.data
  },

  /**
   * Create a new page (folder with block structure).
   */
  async createPage(
    notebookId: number | string,
    workspaceId: number | string,
    data: {
      parent_path?: string
      title: string
      description?: string
      properties?: Record<string, any>
    }
  ): Promise<PageMetadata> {
    const response = await apiClient.post<PageMetadata>(
      `/api/v1/workspaces/${workspaceId}/notebooks/${notebookId}/blocks/pages`,
      data
    )
    return response.data
  },

  /**
   * Update block content.
   */
  async updateBlock(
    blockId: string,
    notebookId: number | string,
    workspaceId: number | string,
    content: string
  ): Promise<Block> {
    const response = await apiClient.put<Block>(
      `/api/v1/workspaces/${workspaceId}/notebooks/${notebookId}/blocks/${blockId}`,
      { content }
    )
    return response.data
  },

  /**
   * Move a block to a new parent and/or position.
   */
  async moveBlock(
    blockId: string,
    notebookId: number | string,
    workspaceId: number | string,
    data: {
      new_parent_block_id?: string
      position?: number
    }
  ): Promise<Block> {
    const response = await apiClient.patch<Block>(
      `/api/v1/workspaces/${workspaceId}/notebooks/${notebookId}/blocks/${blockId}/move`,
      data
    )
    return response.data
  },

  /**
   * Reorder children of a page block.
   */
  async reorderBlocks(
    blockId: string,
    notebookId: number | string,
    workspaceId: number | string,
    blockIds: string[]
  ): Promise<any> {
    const response = await apiClient.patch(
      `/api/v1/workspaces/${workspaceId}/notebooks/${notebookId}/blocks/${blockId}/reorder`,
      { block_ids: blockIds }
    )
    return response.data
  },

  /**
   * Delete a block. For pages, recursively deletes all children.
   */
  async deleteBlock(
    blockId: string,
    notebookId: number | string,
    workspaceId: number | string
  ): Promise<void> {
    await apiClient.delete(
      `/api/v1/workspaces/${workspaceId}/notebooks/${notebookId}/blocks/${blockId}`
    )
  },

  /**
   * Convert an existing markdown file to a page of blocks.
   */
  async convertFileToBlocks(
    notebookId: number | string,
    workspaceId: number | string,
    fileId: number
  ): Promise<PageMetadata> {
    const response = await apiClient.post<PageMetadata>(
      `/api/v1/workspaces/${workspaceId}/notebooks/${notebookId}/blocks/convert-file`,
      { file_id: fileId }
    )
    return response.data
  },

  /**
   * Import a markdown file as a page of blocks.
   */
  async importMarkdown(
    notebookId: number | string,
    workspaceId: number | string,
    file: File
  ): Promise<PageMetadata> {
    const formData = new FormData()
    formData.append("file", file)
    const response = await apiClient.post<PageMetadata>(
      `/api/v1/workspaces/${workspaceId}/notebooks/${notebookId}/blocks/import-markdown`,
      formData,
      { headers: { "Content-Type": "multipart/form-data" } }
    )
    return response.data
  },
}

export const userService = {
  async deleteAccount(): Promise<void> {
    await apiClient.delete("/api/v1/users/me")
  },
}

export const searchService = {
  /**
   * Search files and content across all notebooks in a workspace.
   */
  async search(workspaceId: number | string, query: string): Promise<any> {
    const response = await apiClient.get(
      `/api/v1/workspaces/${workspaceId}/search/?q=${encodeURIComponent(query)}`
    )
    return response.data
  },

  /**
   * Search files and content in a specific notebook.
   */
  async searchInNotebook(workspaceId: number | string, notebookId: number | string, query: string): Promise<any> {
    const response = await apiClient.get(
      `/api/v1/workspaces/${workspaceId}/notebooks/${notebookId}/search/?q=${encodeURIComponent(query)}`
    )
    return response.data
  },

  /**
   * Search by tags across all notebooks in a workspace.
   */
  async searchByTags(workspaceId: number | string, tags: string[]): Promise<any> {
    const response = await apiClient.get(
      `/api/v1/workspaces/${workspaceId}/search/tags?tags=${encodeURIComponent(tags.join(","))}`
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
      `/api/v1/workspaces/${workspaceId}/notebooks/${notebookId}/search/tags?tags=${encodeURIComponent(tags.join(","))}`
    )
    return response.data
  },
}

