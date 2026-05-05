import { defineStore } from "pinia"
import { ref } from "vue"
import {
  projectService,
  type ProjectSummary,
  type ProjectDetail,
} from "../services/projects"

export const useProjectsStore = defineStore("projects", () => {
  const projects = ref<ProjectSummary[]>([])
  const currentProject = ref<ProjectDetail | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetchProjects(workspaceSlug: string) {
    loading.value = true
    error.value = null
    try {
      projects.value = await projectService.list(workspaceSlug)
    } catch (e: any) {
      error.value = e?.message ?? "Failed to load projects"
    } finally {
      loading.value = false
    }
  }

  async function fetchProject(workspaceSlug: string, slug: string) {
    loading.value = true
    error.value = null
    try {
      currentProject.value = await projectService.get(workspaceSlug, slug)
    } catch (e: any) {
      error.value = e?.message ?? "Failed to load project"
    } finally {
      loading.value = false
    }
  }

  async function assign(
    workspaceSlug: string,
    slug: string,
    imageIds: string[],
    roles: string[]
  ) {
    await projectService.assign(workspaceSlug, slug, imageIds, roles)
  }

  async function unassign(workspaceSlug: string, slug: string, imageIds: string[]) {
    await projectService.unassign(workspaceSlug, slug, imageIds)
  }

  return {
    projects,
    currentProject,
    loading,
    error,
    fetchProjects,
    fetchProject,
    assign,
    unassign,
  }
})
