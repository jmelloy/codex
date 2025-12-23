import apiClient from "./api";

export interface Workspace {
  id: number;
  name: string;
  path: string;
  owner_id: number;
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
  created_at: string;
  updated_at: string;
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

  async create(name: string, path: string): Promise<Workspace> {
    const response = await apiClient.post<Workspace>("/api/v1/workspaces/", {
      name,
      path,
    });
    return response.data;
  },
};

export const notebookService = {
  async list(workspaceId: number): Promise<Notebook[]> {
    const response = await apiClient.get<Notebook[]>(
      `/api/v1/notebooks/?workspace_id=${workspaceId}`
    );
    return response.data;
  },

  async get(id: number): Promise<Notebook> {
    const response = await apiClient.get<Notebook>(`/api/v1/notebooks/${id}`);
    return response.data;
  },

  async create(
    workspaceId: number,
    name: string,
    path: string
  ): Promise<Notebook> {
    const response = await apiClient.post<Notebook>("/api/v1/notebooks/", {
      workspace_id: workspaceId,
      name,
      path,
    });
    return response.data;
  },
};

export const fileService = {
  async list(notebookId: number): Promise<FileMetadata[]> {
    const response = await apiClient.get<FileMetadata[]>(
      `/api/v1/files/?notebook_id=${notebookId}`
    );
    return response.data;
  },

  async get(id: number): Promise<FileMetadata> {
    const response = await apiClient.get<FileMetadata>(`/api/v1/files/${id}`);
    return response.data;
  },

  async create(
    notebookId: number,
    path: string,
    content: string
  ): Promise<FileMetadata> {
    const response = await apiClient.post<FileMetadata>("/api/v1/files/", {
      notebook_id: notebookId,
      path,
      content,
    });
    return response.data;
  },

  async update(id: number, content: string): Promise<FileMetadata> {
    const response = await apiClient.put<FileMetadata>(`/api/v1/files/${id}`, {
      content,
    });
    return response.data;
  },
};

export const searchService = {
  async search(workspaceId: number, query: string): Promise<any> {
    const response = await apiClient.get(
      `/api/v1/search/?workspace_id=${workspaceId}&q=${query}`
    );
    return response.data;
  },

  async searchByTags(workspaceId: number, tags: string[]): Promise<any> {
    const response = await apiClient.get(
      `/api/v1/search/tags?workspace_id=${workspaceId}&tags=${tags.join(",")}`
    );
    return response.data;
  },
};
