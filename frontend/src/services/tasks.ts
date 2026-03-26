import apiClient from "./api"

export interface Task {
  id: number
  workspace_id: number
  title: string
  description: string | null
  status: "pending" | "in_progress" | "completed" | "failed"
  assigned_to: string | null
  job_id: string | null
  job_type: string
  created_at: string
  updated_at: string
  completed_at: string | null
}

export interface TaskCreate {
  title: string
  description?: string
  job_type?: string
}

export interface TaskUpdate {
  status?: string
  assigned_to?: string
}

export interface TaskListParams {
  status?: string
  assigned_to?: string
}

export interface TaskStatus {
  task_id: number
  status: string
  job_id: string | null
  job_status?: string
  job_result?: unknown
}

function tasksUrl(workspaceIdentifier: string): string {
  return `/api/v1/workspaces/${workspaceIdentifier}/tasks`
}

export const taskService = {
  async list(workspaceIdentifier: string, params?: TaskListParams): Promise<Task[]> {
    const response = await apiClient.get<Task[]>(`${tasksUrl(workspaceIdentifier)}/`, {
      params,
    })
    return response.data
  },

  async get(workspaceIdentifier: string, taskId: number): Promise<Task> {
    const response = await apiClient.get<Task>(`${tasksUrl(workspaceIdentifier)}/${taskId}`)
    return response.data
  },

  async create(workspaceIdentifier: string, data: TaskCreate): Promise<Task> {
    const response = await apiClient.post<Task>(`${tasksUrl(workspaceIdentifier)}/`, data)
    return response.data
  },

  async update(workspaceIdentifier: string, taskId: number, data: TaskUpdate): Promise<Task> {
    const response = await apiClient.put<Task>(
      `${tasksUrl(workspaceIdentifier)}/${taskId}`,
      data,
    )
    return response.data
  },

  async delete(workspaceIdentifier: string, taskId: number): Promise<void> {
    await apiClient.delete(`${tasksUrl(workspaceIdentifier)}/${taskId}`)
  },

  async enqueue(workspaceIdentifier: string, taskId: number): Promise<Task> {
    const response = await apiClient.post<Task>(
      `${tasksUrl(workspaceIdentifier)}/${taskId}/enqueue`,
    )
    return response.data
  },

  async status(workspaceIdentifier: string, taskId: number): Promise<TaskStatus> {
    const response = await apiClient.get<TaskStatus>(
      `${tasksUrl(workspaceIdentifier)}/${taskId}/status`,
    )
    return response.data
  },
}
