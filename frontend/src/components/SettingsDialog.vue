<template>
  <Teleport to="body">
    <div v-if="modelValue" class="settings-overlay" @click="handleOverlayClick">
      <div class="settings-container" @click.stop>
        <div class="settings-grid">
          <!-- Navigation Panel -->
          <nav class="settings-nav-panel">
            <div class="settings-nav-header">
              <h2>Configuration</h2>
              <button @click="closeDialog" class="close-btn" aria-label="Close settings">
                <span aria-hidden="true">&times;</span>
              </button>
            </div>
            
            <div class="nav-tree">
              <!-- User Section -->
              <div class="nav-section">
                <button 
                  @click="navigateTo({ type: 'user' })" 
                  :class="{ active: activeSection?.type === 'user' }"
                  class="nav-item nav-item-top">
                  <span class="nav-icon">👤</span>
                  <span class="nav-label">User Settings</span>
                </button>
              </div>

              <!-- Workspaces Section -->
              <div class="nav-section">
                <div class="nav-section-title">Workspaces</div>
                <div v-if="availableWorkspaces.length === 0" class="nav-empty">
                  No workspaces
                </div>
                <div v-else class="nav-hierarchy">
                  <div v-for="ws in availableWorkspaces" :key="ws.id" class="nav-workspace-block">
                    <button 
                      @click="navigateTo({ type: 'workspace', workspaceId: ws.id })"
                      :class="{ active: activeSection?.type === 'workspace' && activeSection?.workspaceId === ws.id }"
                      class="nav-item">
                      <span class="nav-icon">🗂️</span>
                      <span class="nav-label">{{ ws.name }}</span>
                    </button>
                    
                    <!-- Notebooks under workspace -->
                    <div v-if="workspaceNotebooks[ws.id]?.length" class="nav-notebooks-list">
                      <button 
                        v-for="nb in workspaceNotebooks[ws.id]" 
                        :key="nb.id"
                        @click="navigateTo({ type: 'notebook', workspaceId: ws.id, notebookId: nb.id })"
                        :class="{ active: activeSection?.type === 'notebook' && activeSection?.notebookId === nb.id }"
                        class="nav-item nav-item-nested">
                        <span class="nav-icon">📓</span>
                        <span class="nav-label">{{ nb.name }}</span>
                      </button>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Agents Section -->
              <div class="nav-section">
                <button
                  @click="navigateTo({ type: 'agents', workspaceId: workspaceStore.currentWorkspace?.id })"
                  :class="{ active: activeSection?.type === 'agents' }"
                  class="nav-item nav-item-top">
                  <span class="nav-icon">🤖</span>
                  <span class="nav-label">AI Agents</span>
                </button>
              </div>

              <!-- Integrations Section -->
              <div class="nav-section">
                <button
                  @click="navigateTo({ type: 'integrations' })"
                  :class="{ active: activeSection?.type === 'integrations' }"
                  class="nav-item nav-item-top">
                  <span class="nav-icon">🔌</span>
                  <span class="nav-label">Integrations</span>
                </button>
              </div>
            </div>
          </nav>

          <!-- Content Panel -->
          <main class="settings-content-panel">
            <UserSettingsPanel v-if="activeSection?.type === 'user'" />
            <WorkspaceSettingsPanel 
              v-else-if="activeSection?.type === 'workspace' && activeSection.workspaceId" 
              :workspaceId="activeSection.workspaceId" />
            <NotebookSettingsPanel 
              v-else-if="activeSection?.type === 'notebook' && activeSection.workspaceId && activeSection.notebookId" 
              :workspaceId="activeSection.workspaceId"
              :notebookId="activeSection.notebookId" />
            <AgentsPanel
              v-else-if="activeSection?.type === 'agents' && activeSection.workspaceId"
              :workspaceId="activeSection.workspaceId"
              @open-chat="handleOpenAgentChat" />
            <IntegrationsPanel v-else-if="activeSection?.type === 'integrations'" />
            <div v-else class="empty-panel">Select a settings category</div>
          </main>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useWorkspaceStore } from '../stores/workspace'
import UserSettingsPanel from './settings/UserSettingsPanel.vue'
import WorkspaceSettingsPanel from './settings/WorkspaceSettingsPanel.vue'
import NotebookSettingsPanel from './settings/NotebookSettingsPanel.vue'
import IntegrationsPanel from './settings/IntegrationsPanel.vue'
import AgentsPanel from './settings/AgentsPanel.vue'
import { useAgentStore } from '../stores/agent'
import type { Agent } from '../services/agent'

interface NavigationTarget {
  type: 'user' | 'workspace' | 'notebook' | 'integrations' | 'agents'
  workspaceId?: number
  notebookId?: number
}

const props = defineProps<{
  modelValue: boolean
  initialSection?: NavigationTarget
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  'open-agent-chat': [agent: Agent]
}>()

const agentStore = useAgentStore()

function handleOpenAgentChat(agent: Agent) {
  agentStore.openChat(agent)
  closeDialog()
}

const workspaceStore = useWorkspaceStore()
const activeSection = ref<NavigationTarget | null>(null)
const workspaceNotebooks = ref<Record<number, any[]>>({})

const availableWorkspaces = computed(() => workspaceStore.workspaces || [])

function closeDialog() {
  emit('update:modelValue', false)
}

function handleOverlayClick() {
  closeDialog()
}

function navigateTo(target: NavigationTarget) {
  activeSection.value = target
  
  // Load notebooks for workspace if needed
  if (target.type === 'workspace' && target.workspaceId) {
    loadNotebooksForWorkspace(target.workspaceId)
  }
}

async function loadNotebooksForWorkspace(workspaceId: number) {
  if (workspaceNotebooks.value[workspaceId]) return
  
  try {
    const workspace = availableWorkspaces.value.find(w => w.id === workspaceId)
    if (workspace) {
      await workspaceStore.fetchNotebooks(workspaceId)
      workspaceNotebooks.value[workspaceId] = workspaceStore.notebooks
    }
  } catch (err) {
    console.error('Failed to load notebooks:', err)
  }
}

watch(() => props.modelValue, (isOpen) => {
  if (isOpen) {
    if (props.initialSection) {
      activeSection.value = props.initialSection
    } else if (!activeSection.value) {
      activeSection.value = { type: 'user' }
    }
  }
})

onMounted(async () => {
  await workspaceStore.fetchWorkspaces()
})
</script>

<style scoped>
.settings-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  padding: 1.5rem;
}

.settings-container {
  background: var(--color-bg-primary);
  border-radius: 12px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.4);
  max-width: 1200px;
  width: 100%;
  max-height: 85vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.settings-grid {
  display: grid;
  grid-template-columns: 280px 1fr;
  height: 100%;
  overflow: hidden;
}

.settings-nav-panel {
  background: var(--color-bg-secondary);
  border-right: 1px solid var(--color-border-medium);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.settings-nav-header {
  padding: 1.5rem;
  border-bottom: 1px solid var(--color-border-medium);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.settings-nav-header h2 {
  margin: 0;
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--color-text-primary);
}

.close-btn {
  background: none;
  border: none;
  font-size: 2rem;
  line-height: 1;
  cursor: pointer;
  color: var(--color-text-secondary);
  padding: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  transition: all 0.2s;
}

.close-btn:hover {
  background: var(--color-bg-tertiary);
  color: var(--color-text-primary);
}

.nav-tree {
  flex: 1;
  overflow-y: auto;
  padding: 1rem;
}

.nav-section {
  margin-bottom: 1.5rem;
}

.nav-section-title {
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--color-text-tertiary);
  padding: 0.5rem 0.75rem;
  margin-bottom: 0.25rem;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.625rem 0.75rem;
  width: 100%;
  border: none;
  background: none;
  color: var(--color-text-primary);
  cursor: pointer;
  border-radius: 6px;
  transition: all 0.15s;
  font-size: 0.9375rem;
  text-align: left;
}

.nav-item:hover {
  background: var(--color-bg-tertiary);
}

.nav-item.active {
  background: var(--notebook-accent);
  color: var(--color-text-inverse);
  font-weight: 500;
}

.nav-item-top {
  font-weight: 500;
}

.nav-item-nested {
  padding-left: 2rem;
  font-size: 0.875rem;
}

.nav-icon {
  font-size: 1.125rem;
}

.nav-label {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.nav-empty {
  padding: 0.75rem;
  color: var(--color-text-tertiary);
  font-size: 0.875rem;
  font-style: italic;
}

.nav-hierarchy {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.nav-workspace-block {
  display: flex;
  flex-direction: column;
}

.nav-notebooks-list {
  display: flex;
  flex-direction: column;
  margin-top: 0.25rem;
}

.settings-content-panel {
  overflow-y: auto;
  background: var(--color-bg-primary);
}

.empty-panel {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--color-text-tertiary);
  font-size: 1rem;
}

@media (max-width: 768px) {
  .settings-grid {
    grid-template-columns: 1fr;
  }
  
  .settings-nav-panel {
    display: none;
  }
}
</style>
