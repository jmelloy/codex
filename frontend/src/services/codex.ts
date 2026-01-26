import apiClient from "./api";

export interface Workspace {
  id: number;
  name: string;
  path: string;
  owner_id: number;
  theme_setting?: string;
  created_at: string;
  updated_at: string;
}

export interface Notebook {
  id: number;
  name: string;
  path: string;
  description?: string;
  created_at: string;
  updated_at: string;
}

export interface FileMetadata {
  id: number;
  notebook_id: number;
  path: string;
  filename: string;
  content_type: string;  // MIME type (e.g., text/markdown, image/jpeg)
  size: number;
  title?: string;
  description?: string;
  properties?: Record<string, any>; // Unified properties from frontmatter
  created_at: string;
  updated_at: string;
}

export interface FileWithContent extends FileMetadata {
  content: string;
}

export interface FolderMetadata {
  path: string;
  name: string;
  notebook_id: number;
  title?: string;
  description?: string;
  properties?: Record<string, any>;
  file_count: number;
  created_at?: string;
  updated_at?: string;
}

export interface FolderWithFiles extends FolderMetadata {
  files: FileMetadata[];
}
export interface FileHistoryEntry {
  hash: string;
  author: string;
  date: string;
  message: string;
}

export interface FileHistory {
  file_id: number;
  path: string;
  history: FileHistoryEntry[];
}

export interface FileAtCommit {
  file_id: number;
  path: string;
  commit_hash: string;
  content: string;
}

export interface Template {
  id: string;
  name: string;
  description: string;
  icon: string;
  file_extension: string;
  default_name: string;
  content: string;
  source: "default" | "notebook";
}

export const workspaceService = {
  async list(): Promise<Workspace[]> {
    const response = await apiClient.get<Workspace[]>("/api/v1/workspaces/");
    return response.data;
  },

  async get(id: number): Promise<Workspace> {
    const response = await apiClient.get<Workspace>(`/api/v1/workspaces/${id}`);
    return response.data;
  },

  async create(name: string): Promise<Workspace> {
    const response = await apiClient.post<Workspace>("/api/v1/workspaces/", {
      name,
    });
    return response.data;
  },

  async updateTheme(id: number, theme: string): Promise<Workspace> {
    const response = await apiClient.patch<Workspace>(
      `/api/v1/workspaces/${id}/theme`,
      { theme },
    );
    return response.data;
  },
};

export const notebookService = {
  async list(workspaceId: number): Promise<Notebook[]> {
    const response = await apiClient.get<Notebook[]>(
      `/api/v1/notebooks/?workspace_id=${workspaceId}`,
    );
    return response.data;
  },

  async get(id: number): Promise<Notebook> {
    const response = await apiClient.get<Notebook>(`/api/v1/notebooks/${id}`);
    return response.data;
  },

  async create(workspaceId: number, name: string): Promise<Notebook> {
    const response = await apiClient.post<Notebook>("/api/v1/notebooks/", {
      workspace_id: workspaceId,
      name,
    });
    return response.data;
  },
};

export const fileService = {
  async list(notebookId: number, workspaceId: number): Promise<FileMetadata[]> {
    const response = await apiClient.get<FileMetadata[]>(
      `/api/v1/files/?notebook_id=${notebookId}&workspace_id=${workspaceId}`,
    );
    return response.data;
  },

  async get(
    id: number,
    workspaceId: number,
    notebookId: number,
  ): Promise<FileWithContent> {
    const response = await apiClient.get<FileWithContent>(
      `/api/v1/files/${id}?workspace_id=${workspaceId}&notebook_id=${notebookId}`,
    );
    return response.data;
  },

  /**
   * Get a file by its path or filename.
   * Supports exact path match or filename-only search.
   */
  async getByPath(
    path: string,
    workspaceId: number,
    notebookId: number,
  ): Promise<FileWithContent> {
    const encodedPath = encodeURIComponent(path);
    const response = await apiClient.get<FileWithContent>(
      `/api/v1/files/by-path?path=${encodedPath}&workspace_id=${workspaceId}&notebook_id=${notebookId}`,
    );
    return response.data;
  },

  /**
   * Get the content URL for a file by path (for binary files like images).
   */
  getContentUrlByPath(
    path: string,
    workspaceId: number,
    notebookId: number,
  ): string {
    const encodedPath = encodeURIComponent(path);
    return `/api/v1/files/by-path/content?path=${encodedPath}&workspace_id=${workspaceId}&notebook_id=${notebookId}`;
  },

  /**
   * Get the content URL for a file by ID (for binary files like images).
   */
  getContentUrl(id: number, workspaceId: number, notebookId: number): string {
    return `/api/v1/files/${id}/content?workspace_id=${workspaceId}&notebook_id=${notebookId}`;
  },

  /**
   * Resolve a link to a file, supporting relative paths and filenames.
   */
  async resolveLink(
    link: string,
    workspaceId: number,
    notebookId: number,
    currentFilePath?: string,
  ): Promise<FileMetadata & { resolved_path: string }> {
    const response = await apiClient.post<
      FileMetadata & { resolved_path: string }
    >(
      `/api/v1/files/resolve-link?workspace_id=${workspaceId}&notebook_id=${notebookId}`,
      {
        link,
        current_file_path: currentFilePath,
      },
    );
    return response.data;
  },

  async create(
    notebookId: number,
    workspaceId: number,
    path: string,
    content: string,
  ): Promise<FileMetadata> {
    const response = await apiClient.post<FileMetadata>("/api/v1/files/", {
      notebook_id: notebookId,
      workspace_id: workspaceId,
      path,
      content,
    });
    return response.data;
  },

  async update(
    id: number,
    workspaceId: number,
    notebookId: number,
    content: string,
    properties?: Record<string, any>,
  ): Promise<FileMetadata> {
    const response = await apiClient.put<FileMetadata>(
      `/api/v1/files/${id}?workspace_id=${workspaceId}&notebook_id=${notebookId}`,
      {
        content,
        properties,
      },
    );
    return response.data;
  },

  async delete(id: number, workspaceId: number): Promise<void> {
    await apiClient.delete(`/api/v1/files/${id}?workspace_id=${workspaceId}`);
  },

  async upload(
    notebookId: number,
    workspaceId: number,
    file: File,
    path?: string,
  ): Promise<FileMetadata> {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("notebook_id", String(notebookId));
    formData.append("workspace_id", String(workspaceId));
    if (path) {
      formData.append("path", path);
    }
    const response = await apiClient.post<FileMetadata>(
      "/api/v1/files/upload",
      formData,
      {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      },
    );
    return response.data;
  },

  async move(
    id: number,
    workspaceId: number,
    notebookId: number,
    newPath: string,
  ): Promise<FileMetadata> {
    const response = await apiClient.patch<FileMetadata>(
      `/api/v1/files/${id}/move?workspace_id=${workspaceId}&notebook_id=${notebookId}`,
      { new_path: newPath },
    );
    return response.data;
  },

  /**
   * Get git history for a file.
   */
  async getHistory(
    id: number,
    workspaceId: number,
    notebookId: number,
    maxCount: number = 20,
  ): Promise<FileHistory> {
    const response = await apiClient.get<FileHistory>(
      `/api/v1/files/${id}/history?workspace_id=${workspaceId}&notebook_id=${notebookId}&max_count=${maxCount}`,
    );
    return response.data;
  },

  /**
   * Get file content at a specific commit.
   */
  async getAtCommit(
    id: number,
    workspaceId: number,
    notebookId: number,
    commitHash: string,
  ): Promise<FileAtCommit> {
    const response = await apiClient.get<FileAtCommit>(
      `/api/v1/files/${id}/history/${commitHash}?workspace_id=${workspaceId}&notebook_id=${notebookId}`,
    );
    return response.data;
  },
};

export const templateService = {
  /**
   * List available templates for a notebook.
   */
  async list(notebookId: number, workspaceId: number): Promise<Template[]> {
    const response = await apiClient.get<{ templates: Template[] }>(
      `/api/v1/files/templates?notebook_id=${notebookId}&workspace_id=${workspaceId}`,
    );
    return response.data.templates;
  },

  /**
   * Create a file from a template.
   */
  async createFromTemplate(
    notebookId: number,
    workspaceId: number,
    templateId: string,
    filename?: string,
  ): Promise<FileMetadata> {
    const response = await apiClient.post<FileMetadata>(
      "/api/v1/files/from-template",
      {
        notebook_id: notebookId,
        workspace_id: workspaceId,
        template_id: templateId,
        filename: filename || null,
      },
    );
    return response.data;
  },

  /**
   * Expand date patterns in a string (client-side preview).
   */
  expandPattern(pattern: string, title: string = "untitled"): string {
    const now = new Date();
    const yyyy = now.getFullYear().toString();
    const yy = yyyy.slice(-2);
    const mm = String(now.getMonth() + 1).padStart(2, "0");
    const dd = String(now.getDate()).padStart(2, "0");
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
    ] as const;
    const month = monthNames[now.getMonth()] ?? "January";
    const mon = month.slice(0, 3);

    return pattern
      .replace(/{yyyy}/g, yyyy)
      .replace(/{yy}/g, yy)
      .replace(/{mm}/g, mm)
      .replace(/{dd}/g, dd)
      .replace(/{month}/g, month)
      .replace(/{mon}/g, mon)
      .replace(/{title}/g, title);
  },
};

export const folderService = {
  /**
   * Get folder metadata and contents.
   * The folder metadata is stored in a .file within the folder.
   */
  async get(
    path: string,
    notebookId: number,
    workspaceId: number,
  ): Promise<FolderWithFiles> {
    const encodedPath = encodeURIComponent(path);
    const response = await apiClient.get<FolderWithFiles>(
      `/api/v1/folders/${encodedPath}?notebook_id=${notebookId}&workspace_id=${workspaceId}`,
    );
    return response.data;
  },

  /**
   * Update folder properties.
   * This updates the .file within the folder.
   */
  async updateProperties(
    path: string,
    notebookId: number,
    workspaceId: number,
    properties: Record<string, any>,
  ): Promise<FolderMetadata> {
    const encodedPath = encodeURIComponent(path);
    const response = await apiClient.put<FolderMetadata>(
      `/api/v1/folders/${encodedPath}?notebook_id=${notebookId}&workspace_id=${workspaceId}`,
      { properties },
    );
    return response.data;
  },

  /**
   * Delete a folder and all its contents.
   */
  async delete(
    path: string,
    notebookId: number,
    workspaceId: number,
  ): Promise<void> {
    const encodedPath = encodeURIComponent(path);
    await apiClient.delete(
      `/api/v1/folders/${encodedPath}?notebook_id=${notebookId}&workspace_id=${workspaceId}`,
    );
  },
};

export const searchService = {
  async search(workspaceId: number, query: string): Promise<any> {
    const response = await apiClient.get(
      `/api/v1/search/?workspace_id=${workspaceId}&q=${query}`,
    );
    return response.data;
  },

  async searchByTags(workspaceId: number, tags: string[]): Promise<any> {
    const response = await apiClient.get(
      `/api/v1/search/tags?workspace_id=${workspaceId}&tags=${tags.join(",")}`,
    );
    return response.data;
  },
};
