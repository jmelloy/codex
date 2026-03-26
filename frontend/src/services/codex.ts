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
    | "database"
  content_format: "markdown" | "json" | "binary"
  order_index: number
  title?: string
  filename?: string
  content?: string
  content_type?: string
  size?: number
  description?: string
  properties?: Record<string, any>
  hash?: string
  file_type?: string
  sidecar_path?: string
  file_created_at?: string
  file_modified_at?: string
  s3_bucket?: string
  s3_key?: string
  s3_version_id?: string
  git_tracked?: boolean
  last_commit_hash?: string
  children?: Block[]
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
  files_changed?: string[]
}

export interface RootBlocksResponse {
  blocks: Block[]
  notebook_id: number
  workspace_id: number
}

export interface BlockChildrenResponse {
  parent_block_id: string
  children: Block[]
}

export interface ReorderBlocksResponse {
  parent_block_id: string
  blocks: Block[]
}

export interface BlockTreeResponse {
  tree: Block[]
  notebook_id: number
  workspace_id: number
}

export interface BlockTextContent {
  content: string
  properties?: Record<string, any>
}

export interface BlockHistory {
  block_id: string
  path: string
  history: FileHistoryEntry[]
}

export interface FileChangeDetail {
  path: string
  change_type: string
  diff: string | null
}

export interface PageAtCommit {
  block_id: string
  path: string
  commit_hash: string
  files: FileChangeDetail[]
}

export interface BlockAtCommit {
  block_id: string
  path: string
  commit_hash: string
  content: string
}

export interface ImportFolderResponse {
  path: string
  block_id: string
  pages_created: number
  blocks_created: number
}

export interface SearchResult {
  id: number
  notebook_id: number
  path: string
  filename: string
  content_type: string
  size: number
  title?: string
  description?: string
  properties?: Record<string, any>
  created_at: string
  updated_at: string
  notebook_name?: string
  snippet?: string
  score?: number
}

export interface SearchResponse {
  query: string
  workspace_id: number
  workspace_slug: string
  results: SearchResult[]
  message?: string
}

export interface NotebookSearchResponse extends SearchResponse {
  notebook_id: number
  notebook_slug: string
}

export interface TagSearchResponse {
  tags: string[]
  workspace_id: number
  workspace_slug: string
  results: SearchResult[]
  message?: string
}

export interface NotebookTagSearchResponse extends TagSearchResponse {
  notebook_id: number
  notebook_slug: string
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



export const blockService = {
  /**
   * List root-level blocks/pages in a notebook.
   */
  async listRootBlocks(
    notebookId: number | string,
    workspaceId: number | string
  ): Promise<RootBlocksResponse> {
    const response = await apiClient.get<RootBlocksResponse>(
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
  ): Promise<BlockChildrenResponse> {
    const response = await apiClient.get<BlockChildrenResponse>(
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
  ): Promise<Block & { blocks?: Block[] }> {
    const response = await apiClient.post<Block & { blocks?: Block[] }>(
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
    content: string,
    blockType?: string
  ): Promise<Block & { blocks?: Block[] }> {
    const data: { content: string; block_type?: string } = { content }
    if (blockType) data.block_type = blockType
    const response = await apiClient.put<Block & { blocks?: Block[] }>(
      `/api/v1/workspaces/${workspaceId}/notebooks/${notebookId}/blocks/${blockId}`,
      data
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
  ): Promise<ReorderBlocksResponse> {
    const response = await apiClient.patch<ReorderBlocksResponse>(
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
  ): Promise<{ message: string; blocks?: Block[] }> {
    const response = await apiClient.delete<{ message: string; blocks?: Block[] }>(
      `/api/v1/workspaces/${workspaceId}/notebooks/${notebookId}/blocks/${blockId}`
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

  /**
   * Get hierarchical block tree for sidebar navigation.
   */
  async getTree(
    notebookId: number | string,
    workspaceId: number | string
  ): Promise<BlockTreeResponse> {
    const response = await apiClient.get<BlockTreeResponse>(
      `/api/v1/workspaces/${workspaceId}/notebooks/${notebookId}/blocks/tree`
    )
    return response.data
  },

  /**
   * Get text content for a block (strips frontmatter).
   */
  async getText(
    blockId: string,
    notebookId: number | string,
    workspaceId: number | string
  ): Promise<BlockTextContent> {
    const response = await apiClient.get<BlockTextContent>(
      `/api/v1/workspaces/${workspaceId}/notebooks/${notebookId}/blocks/${blockId}/text`
    )
    return response.data
  },

  /**
   * Get the content URL for a block (for binary files like images).
   */
  getContentUrl(blockId: string, notebookId: number | string, workspaceId: number | string): string {
    return `/api/v1/workspaces/${workspaceId}/notebooks/${notebookId}/blocks/${blockId}/content`
  },

  /**
   * Get the content URL for a block by path.
   */
  getContentUrlByPath(path: string, notebookId: number | string, workspaceId: number | string): string {
    const encodedPath = encodeURIComponent(path)
    return `/api/v1/workspaces/${workspaceId}/notebooks/${notebookId}/blocks/path/${encodedPath}/content`
  },

  /**
   * Upload a file as a block within a page.
   */
  async upload(
    notebookId: number | string,
    workspaceId: number | string,
    file: File,
    parentBlockId?: string
  ): Promise<Block> {
    const formData = new FormData()
    formData.append("file", file)
    if (parentBlockId) {
      formData.append("parent_block_id", parentBlockId)
    }
    const response = await apiClient.post<Block>(
      `/api/v1/workspaces/${workspaceId}/notebooks/${notebookId}/blocks/upload`,
      formData
    )
    return response.data
  },

  /**
   * Upload a zip file containing a folder structure.
   */
  async uploadFolderZip(
    notebookId: number | string,
    workspaceId: number | string,
    zipFile: File,
    parentPath?: string
  ): Promise<{ path: string; block_id: string; pages_created: number; blocks_created: number }> {
    const formData = new FormData()
    formData.append("file", zipFile)
    if (parentPath) {
      formData.append("parent_path", parentPath)
    }
    const response = await apiClient.post(
      `/api/v1/workspaces/${workspaceId}/notebooks/${notebookId}/blocks/upload-folder-zip`,
      formData
    )
    return response.data
  },

  /**
   * Get git history for a block.
   */
  async getHistory(
    blockId: string,
    notebookId: number | string,
    workspaceId: number | string
  ): Promise<BlockHistory> {
    const response = await apiClient.get<BlockHistory>(
      `/api/v1/workspaces/${workspaceId}/notebooks/${notebookId}/blocks/${blockId}/history`
    )
    return response.data
  },

  /**
   * Get block content at a specific commit.
   */
  async getAtCommit(
    blockId: string,
    notebookId: number | string,
    workspaceId: number | string,
    commitHash: string
  ): Promise<BlockAtCommit | PageAtCommit> {
    const response = await apiClient.get<BlockAtCommit | PageAtCommit>(
      `/api/v1/workspaces/${workspaceId}/notebooks/${notebookId}/blocks/${blockId}/history/${commitHash}`
    )
    return response.data
  },

  /**
   * Resolve a relative link to a block.
   */
  async resolveLink(
    link: string,
    notebookId: number | string,
    workspaceId: number | string,
    currentFilePath?: string
  ): Promise<Block & { resolved_path: string }> {
    const response = await apiClient.post<Block & { resolved_path: string }>(
      `/api/v1/workspaces/${workspaceId}/notebooks/${notebookId}/blocks/resolve-link`,
      { link, current_file_path: currentFilePath }
    )
    return response.data
  },

  /**
   * Update block properties.
   */
  async updateProperties(
    blockId: string,
    notebookId: number | string,
    workspaceId: number | string,
    properties: Record<string, any>
  ): Promise<Block> {
    const response = await apiClient.patch<Block>(
      `/api/v1/workspaces/${workspaceId}/notebooks/${notebookId}/blocks/${blockId}/properties`,
      { properties }
    )
    return response.data
  },

  /**
   * Import a folder tree as nested pages.
   */
  async importFolder(
    notebookId: number | string,
    workspaceId: number | string,
    folderPath: string
  ): Promise<ImportFolderResponse> {
    const response = await apiClient.post<ImportFolderResponse>(
      `/api/v1/workspaces/${workspaceId}/notebooks/${notebookId}/blocks/import-folder`,
      { folder_path: folderPath }
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
  async search(workspaceId: number | string, query: string): Promise<SearchResponse> {
    const response = await apiClient.get<SearchResponse>(
      `/api/v1/workspaces/${workspaceId}/search/?q=${encodeURIComponent(query)}`
    )
    return response.data
  },

  /**
   * Search files and content in a specific notebook.
   */
  async searchInNotebook(
    workspaceId: number | string,
    notebookId: number | string,
    query: string
  ): Promise<NotebookSearchResponse> {
    const response = await apiClient.get<NotebookSearchResponse>(
      `/api/v1/workspaces/${workspaceId}/notebooks/${notebookId}/search/?q=${encodeURIComponent(query)}`
    )
    return response.data
  },

  /**
   * Search by tags across all notebooks in a workspace.
   */
  async searchByTags(workspaceId: number | string, tags: string[]): Promise<TagSearchResponse> {
    const params = new URLSearchParams()
    tags.forEach(tag => params.append('tags', tag))
    const response = await apiClient.get<TagSearchResponse>(
      `/api/v1/workspaces/${workspaceId}/search/tags?${params.toString()}`
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
  ): Promise<NotebookTagSearchResponse> {
    const params = new URLSearchParams()
    tags.forEach(tag => params.append('tags', tag))
    const response = await apiClient.get<NotebookTagSearchResponse>(
      `/api/v1/workspaces/${workspaceId}/notebooks/${notebookId}/search/tags?${params.toString()}`
    )
    return response.data
  },
}

