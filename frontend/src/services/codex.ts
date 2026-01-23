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
  file_type: string;
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
