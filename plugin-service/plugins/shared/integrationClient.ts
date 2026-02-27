/**
 * Shared integration client for plugin components.
 *
 * Centralizes auth token injection, URL construction, and response
 * parsing for plugin integration API calls.
 */

export interface IntegrationExecuteResult<T = any> {
  success: boolean;
  data: T | null;
  error: string | null;
}

export const integrationClient = {
  async execute<T = any>(
    pluginId: string,
    endpointId: string,
    parameters: Record<string, any>,
    context: { workspaceId: number | string; notebookId?: number | string },
  ): Promise<IntegrationExecuteResult<T>> {
    const token = localStorage.getItem("access_token");
    if (!token) {
      throw new Error("Not authenticated");
    }

    const url = context.notebookId
      ? `/api/v1/workspaces/${context.workspaceId}/notebooks/${context.notebookId}/integrations/${pluginId}/execute`
      : `/api/v1/plugins/integrations/${pluginId}/execute?workspace_id=${context.workspaceId}`;

    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        endpoint_id: endpointId,
        parameters,
      }),
    });

    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      throw new Error(data.error || data.detail || `HTTP ${response.status}`);
    }

    return await response.json();
  },
};
