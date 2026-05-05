import apiClient from "./api"

export interface ProjectSummary {
  slug: string
  name: string
  image_count: number
}

export interface ImageInfo {
  id: number
  block_id: string
  notebook_id: number
  notebook_slug: string
  workspace_slug: string
  title?: string
  filename?: string
  content_type?: string
  roles: string[]
}

export interface RoleGroup {
  role: string
  images: ImageInfo[]
}

export interface ProjectDetail {
  slug: string
  name: string
  total_images: number
  roles: RoleGroup[]
}

export const projectService = {
  async list(workspaceSlug: string): Promise<ProjectSummary[]> {
    const response = await apiClient.get<ProjectSummary[]>(
      `/api/v1/workspaces/${workspaceSlug}/projects/`
    )
    return response.data
  },

  async get(workspaceSlug: string, slug: string): Promise<ProjectDetail> {
    const response = await apiClient.get<ProjectDetail>(
      `/api/v1/workspaces/${workspaceSlug}/projects/${slug}`
    )
    return response.data
  },

  async assign(
    workspaceSlug: string,
    slug: string,
    imageIds: string[],
    roles: string[]
  ): Promise<void> {
    await apiClient.post(`/api/v1/workspaces/${workspaceSlug}/projects/${slug}/assign`, {
      image_ids: imageIds,
      roles,
    })
  },

  async unassign(workspaceSlug: string, slug: string, imageIds: string[]): Promise<void> {
    await apiClient.delete(`/api/v1/workspaces/${workspaceSlug}/projects/${slug}/assign`, {
      data: { image_ids: imageIds },
    })
  },
}
