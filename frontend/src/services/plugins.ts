/** Shared plugin types used by WorkspaceSettingsPanel and NotebookSettingsPanel */

export interface PluginData {
  id: string
  name: string
  version: string
  type: string
  enabled: boolean
  manifest: any
}

export interface PluginConfiguration {
  plugin_id: string
  version: string | null
  enabled: boolean
  config: any
}
