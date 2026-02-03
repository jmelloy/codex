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
 */
export async function listIntegrations(workspaceId?: number): Promise<Integration[]> {
  const url = workspaceId 
    ? `/api/v1/plugins/integrations?workspace_id=${workspaceId}`
    : '/api/v1/plugins/integrations'
  const response = await apiClient.get(url)
  return response.data
}

/**
 * Get details of a specific integration
 */
export async function getIntegration(integrationId: string): Promise<IntegrationDetails> {
  const response = await apiClient.get(`/api/v1/plugins/integrations/${integrationId}`)
  return response.data
}

/**
 * Get integration configuration for a workspace
 */
export async function getIntegrationConfig(
  integrationId: string,
  workspaceId: number
): Promise<IntegrationConfig> {
  const response = await apiClient.get(
    `/api/v1/plugins/integrations/${integrationId}/config?workspace_id=${workspaceId}`
  )
  return response.data
}

/**
 * Update integration configuration for a workspace
 */
export async function updateIntegrationConfig(
  integrationId: string,
  workspaceId: number,
  config: Record<string, any>
): Promise<IntegrationConfig> {
  const response = await apiClient.put(
    `/api/v1/plugins/integrations/${integrationId}/config?workspace_id=${workspaceId}`,
    { config }
  )
  return response.data
}

/**
 * Test integration connection
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
 * Get available blocks for an integration
 */
export async function getIntegrationBlocks(integrationId: string) {
  const response = await apiClient.get(`/api/v1/plugins/integrations/${integrationId}/blocks`)
  return response.data
}

/**
 * Execute an integration endpoint
 */
export async function executeIntegrationEndpoint(
  integrationId: string,
  workspaceId: number,
  endpointId: string,
  parameters?: Record<string, any>
) {
  const response = await apiClient.post(
    `/api/v1/plugins/integrations/${integrationId}/execute?workspace_id=${workspaceId}`,
    {
      endpoint_id: endpointId,
      parameters: parameters || {},
    }
  )
  return response.data
}

/**
 * Enable or disable an integration for a workspace
 */
export async function setIntegrationEnabled(
  integrationId: string,
  workspaceId: number,
  enabled: boolean
): Promise<Integration> {
  const response = await apiClient.put(
    `/api/v1/plugins/integrations/${integrationId}/enable?workspace_id=${workspaceId}`,
    { enabled }
  )
  return response.data
}
