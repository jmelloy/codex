import type { Notebook, Page, Entry, Artifact } from "@/types";

const API_BASE = "/api";

function getAuthToken(): string | null {
  return localStorage.getItem("auth_token");
}

function getRefreshToken(): string | null {
  return localStorage.getItem("refresh_token");
}

async function refreshAccessToken(): Promise<boolean> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) return false;

  try {
    const response = await fetch(`${API_BASE}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    if (!response.ok) {
      return false;
    }

    const data = await response.json();
    localStorage.setItem("auth_token", data.access_token);
    return true;
  } catch {
    return false;
  }
}

async function fetchJSON<T>(url: string, options?: RequestInit): Promise<T> {
  const token = getAuthToken();

  let response = await fetch(`${API_BASE}${url}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token && { Authorization: `Bearer ${token}` }),
      ...options?.headers,
    },
  });

  // If we get a 401, try to refresh the token and retry the request
  if (response.status === 401) {
    const refreshed = await refreshAccessToken();
    if (refreshed) {
      // Retry the request with the new token
      const newToken = getAuthToken();
      response = await fetch(`${API_BASE}${url}`, {
        ...options,
        headers: {
          "Content-Type": "application/json",
          ...(newToken && { Authorization: `Bearer ${newToken}` }),
          ...options?.headers,
        },
      });
    }

    // If still unauthorized after refresh attempt, redirect to login
    if (response.status === 401) {
      localStorage.removeItem("auth_token");
      localStorage.removeItem("refresh_token");
      localStorage.removeItem("user");
      window.location.href = "/login";
      throw new Error("Unauthorized");
    }
  }

  if (!response.ok) {
    throw new Error(`API Error: ${response.status} ${response.statusText}`);
  }

  return response.json();
}

export const notebooksApi = {
  list: () => fetchJSON<Notebook[]>("/notebooks"),

  get: (notebookId: string) => fetchJSON<Notebook>(`/notebooks/${notebookId}`),

  create: (data: { title: string; description?: string; tags?: string[] }) =>
    fetchJSON<Notebook>("/notebooks", {
      method: "POST",
      body: JSON.stringify(data),
    }),
};

export const pagesApi = {
  list: (notebookId: string) =>
    fetchJSON<Page[]>(`/notebooks/${notebookId}/pages`),

  get: (pageId: string) => fetchJSON<Page>(`/pages/${pageId}`),

  create: (
    notebookId: string,
    data: { title: string; date?: string; narrative?: Record<string, string> },
  ) =>
    fetchJSON<Page>("/pages", {
      method: "POST",
      body: JSON.stringify({
        notebook_id: notebookId,
        ...data,
      }),
    }),

  update: (
    pageId: string,
    data: { title?: string; narrative?: Record<string, string>; tags?: string[] },
  ) =>
    fetchJSON<Page>(`/pages/${pageId}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),
};

export const entriesApi = {
  list: (pageId: string) => fetchJSON<Entry[]>(`/pages/${pageId}/entries`),

  get: (entryId: string) => fetchJSON<Entry>(`/entries/${entryId}`),

  create: (
    pageId: string,
    data: {
      entry_type: string;
      title: string;
      inputs: Record<string, unknown>;
      tags?: string[];
    },
  ) =>
    fetchJSON<Entry>("/entries", {
      method: "POST",
      body: JSON.stringify({
        page_id: pageId,
        ...data,
      }),
    }),

  execute: (entryId: string) =>
    fetchJSON<Entry>(`/entries/${entryId}/execute`, {
      method: "POST",
    }),

  delete: (entryId: string) =>
    fetchJSON<{ success: boolean }>(`/entries/${entryId}`, {
      method: "DELETE",
    }),

  getLineage: (entryId: string, depth = 3) =>
    fetchJSON<{ ancestors: Entry[]; descendants: Entry[]; entry: Entry }>(
      `/entries/${entryId}/lineage?depth=${depth}`,
    ),

  getArtifacts: (entryId: string) =>
    fetchJSON<Artifact[]>(`/entries/${entryId}/artifacts`),
};

export const artifactsApi = {
  getUrl: (artifactHash: string, thumbnail = false) =>
    `${API_BASE}/artifacts/${artifactHash}${thumbnail ? "?thumbnail=true" : ""}`,

  getInfo: (artifactHash: string) =>
    fetchJSON<Artifact>(`/artifacts/${artifactHash}/info`),
};

export const searchApi = {
  search: (params: {
    query?: string;
    entry_type?: string;
    tags?: string[];
  }) =>
    fetchJSON<{ results: Entry[]; count: number }>("/search", {
      method: "POST",
      body: JSON.stringify(params),
    }),
};

export interface FileTreeItem {
  name: string;
  path: string;
  type: "file" | "directory";
  size?: number;
  modified?: string;
  extension?: string;
  children?: FileTreeItem[];
  properties?: {
    id?: string;
    title?: string;
    type?: string;
    notebook_id?: string;
    [key: string]: unknown;
  };
}

export const filesApi = {
  listNotebooks: () =>
    fetchJSON<{ path: string; files: FileTreeItem[] }>("/files/notebooks"),

  listArtifacts: () =>
    fetchJSON<{ path: string; files: FileTreeItem[] }>("/files/artifacts"),
};
