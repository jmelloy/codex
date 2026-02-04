/**
 * Integration service for managing integration plugins
 */
import apiClient from './api'

export interface Integration {
  id: string
  name: string
  description: string
  version: string
  author: string
  api_type: string
  base_url?: string
  auth_method?: string
  enabled: boolean
}

export interface IntegrationProperty {
  name: string
  type: string
  description: string
  required: boolean
  secure?: boolean
  default?: any
  enum?: string[]
  min?: number
  max?: number
  ui: {
    type: string
    label: string
    placeholder?: string
    help?: string
    options?: Array<{ value: string; label: string }>
  }
}

export interface IntegrationDetails extends Integration {
  properties?: IntegrationProperty[]
  blocks?: Array<{
    id: string
    name: string
    description: string
    icon: string
    syntax?: string
  }>
  endpoints?: Array<{
    id: string
    name: string
    description: string
    method?: string
    path?: string
  }>
}

export interface IntegrationConfig {
  plugin_id: string
  config: Record<string, any>
}

export interface IntegrationTestResult {
  success: boolean
  message: string
  details?: Record<string, any>
}

/**
 * List all available integration plugins
 * Note: Requires notebook context for new nested API structure
 */
export async function listIntegrations(
  workspaceId: number | string,
  notebookId: number | string
): Promise<Integration[]> {
  const response = await apiClient.get(
    `/api/v1/workspaces/${workspaceId}/notebooks/${notebookId}/integrations`
  )
  return response.data
}

/**
 * Get details of a specific integration (global route)
 */
export async function getIntegration(integrationId: string): Promise<IntegrationDetails> {
  const response = await apiClient.get(`/api/v1/plugins/integrations/${integrationId}`)
  return response.data
}

/**
 * Get integration configuration for a workspace
 * Note: Requires notebook context for new nested API structure
 */
export async function getIntegrationConfig(
  integrationId: string,
  workspaceId: number | string,
  notebookId: number | string
): Promise<IntegrationConfig> {
  const response = await apiClient.get(
    `/api/v1/workspaces/${workspaceId}/notebooks/${notebookId}/integrations/${integrationId}/config`
  )
  return response.data
}

/**
 * Update integration configuration for a workspace
 * Note: Requires notebook context for new nested API structure
 */
export async function updateIntegrationConfig(
  integrationId: string,
  workspaceId: number | string,
  notebookId: number | string,
  config: Record<string, any>
): Promise<IntegrationConfig> {
  const response = await apiClient.put(
    `/api/v1/workspaces/${workspaceId}/notebooks/${notebookId}/integrations/${integrationId}/config`,
    { config }
  )
  return response.data
}

/**
 * Test integration connection (global route - no workspace/notebook context needed)
 */
export async function testIntegrationConnection(
  integrationId: string,
  config: Record<string, any>
): Promise<IntegrationTestResult> {
  const response = await apiClient.post(
    `/api/v1/plugins/integrations/${integrationId}/test`,
    { config }
  )
  return response.data
}

/**
 * Get available blocks for an integration (global route)
 */
export async function getIntegrationBlocks(integrationId: string) {
  const response = await apiClient.get(`/api/v1/plugins/integrations/${integrationId}/blocks`)
  return response.data
}

/**
 * Execute an integration endpoint
 * Note: Requires notebook context for new nested API structure
 */
export async function executeIntegrationEndpoint(
  integrationId: string,
  workspaceId: number | string,
  notebookId: number | string,
  endpointId: string,
  parameters?: Record<string, any>
) {
  const response = await apiClient.post(
    `/api/v1/workspaces/${workspaceId}/notebooks/${notebookId}/integrations/${integrationId}/execute`,
    {
      endpoint_id: endpointId,
      parameters: parameters || {},
    }
  )
  return response.data
}

/**
 * Enable or disable an integration for a workspace
 * Note: Requires notebook context for new nested API structure
 */
export async function setIntegrationEnabled(
  integrationId: string,
  workspaceId: number | string,
  notebookId: number | string,
  enabled: boolean
): Promise<Integration> {
  const response = await apiClient.put(
    `/api/v1/workspaces/${workspaceId}/notebooks/${notebookId}/integrations/${integrationId}/enable`,
    { enabled }
  )
  return response.data
}
