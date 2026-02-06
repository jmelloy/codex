<template>
  <div class="panel-wrapper">
    <div class="panel-header">
      <div>
        <h1 class="panel-title">AI Agents</h1>
        <p class="panel-subtitle">Configure AI agents for this workspace</p>
      </div>
      <button
        v-if="!showConfig"
        @click="startCreate"
        class="create-btn"
      >
        + New Agent
      </button>
    </div>

    <div class="panel-content">
      <!-- Agent Config Form (Create/Edit) -->
      <div v-if="showConfig" class="config-container">
        <AgentConfig
          :workspace-id="workspaceId"
          :agent="editingAgent ?? undefined"
          @saved="handleSaved"
          @cancel="showConfig = false"
        />
      </div>

      <!-- Agent List -->
      <div v-else>
        <div v-if="loading" class="loading-state">Loading agents...</div>
        <div v-else-if="agents.length === 0" class="empty-state">
          <p>No agents configured for this workspace.</p>
          <p>Create an agent to get started with AI-assisted notebook management.</p>
        </div>
        <div v-else class="agents-list">
          <div
            v-for="agent in agents"
            :key="agent.id"
            :class="['agent-card', { 'agent-inactive': !agent.is_active }]"
          >
            <div class="card-main">
              <div class="card-header">
                <div class="card-title-row">
                  <h3 class="agent-name">{{ agent.name }}</h3>
                  <div class="agent-badges">
                    <span class="agent-provider">{{ agent.provider }}</span>
                    <span class="agent-model">{{ agent.model }}</span>
                  </div>
                </div>
                <p v-if="agent.description" class="agent-description">
                  {{ agent.description }}
                </p>
                <div class="agent-capabilities">
                  <span v-if="agent.can_read" class="cap-badge cap-read">Read</span>
                  <span v-if="agent.can_write" class="cap-badge cap-write">Write</span>
                  <span v-if="agent.can_create" class="cap-badge cap-create">Create</span>
                  <span v-if="agent.can_delete" class="cap-badge cap-delete">Delete</span>
                </div>
              </div>

              <div class="card-actions">
                <label class="toggle-label">
                  <input
                    type="checkbox"
                    :checked="agent.is_active"
                    @change="handleToggleActive(agent)"
                    class="toggle-checkbox"
                  />
                  <span class="toggle-slider"></span>
                </label>
                <button @click="startEdit(agent)" class="action-btn" title="Edit">
                  Edit
                </button>
                <button @click="openChat(agent)" class="action-btn action-btn-primary" title="Chat">
                  Chat
                </button>
                <button @click="handleDelete(agent)" class="action-btn action-btn-danger" title="Delete">
                  Del
                </button>
              </div>
            </div>

            <!-- Expandable Activity Log -->
            <div v-if="expandedAgent === agent.id" class="card-expanded">
              <AgentActivityLog :agent-id="agent.id" />
            </div>
            <button
              @click="expandedAgent = expandedAgent === agent.id ? null : agent.id"
              class="card-expand-btn"
            >
              {{ expandedAgent === agent.id ? "Hide Activity" : "Show Activity" }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue"
import { useAgentStore } from "../../stores/agent"
import AgentConfig from "../agent/AgentConfig.vue"
import AgentActivityLog from "../agent/AgentActivityLog.vue"
import type { Agent } from "../../services/agent"

const props = defineProps<{
  workspaceId: number
}>()

const emit = defineEmits<{
  "open-chat": [agent: Agent]
}>()

const agentStore = useAgentStore()

const showConfig = ref(false)
const editingAgent = ref<Agent | null>(null)
const expandedAgent = ref<number | null>(null)

const agents = computed(() => agentStore.agents)
const loading = computed(() => agentStore.loading)

function startCreate() {
  editingAgent.value = null
  showConfig.value = true
}

function startEdit(agent: Agent) {
  editingAgent.value = agent
  showConfig.value = true
}

function handleSaved() {
  showConfig.value = false
  editingAgent.value = null
}

async function handleToggleActive(agent: Agent) {
  await agentStore.toggleAgentActive(agent.id, !agent.is_active)
}

async function handleDelete(agent: Agent) {
  if (confirm(`Delete agent "${agent.name}"? This cannot be undone.`)) {
    await agentStore.deleteAgent(agent.id)
  }
}

function openChat(agent: Agent) {
  emit("open-chat", agent)
}

onMounted(async () => {
  await agentStore.fetchAgents(props.workspaceId)
})
</script>

<style scoped>
.panel-wrapper {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 2rem 2.5rem;
  border-bottom: 1px solid var(--color-border-light);
}

.panel-title {
  margin: 0 0 0.5rem;
  font-size: 2rem;
  font-weight: 700;
  color: var(--color-text-primary);
}

.panel-subtitle {
  margin: 0;
  color: var(--color-text-secondary);
  font-size: 1rem;
}

.create-btn {
  padding: 0.5rem 1.25rem;
  background: var(--notebook-accent);
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s;
  white-space: nowrap;
}

.create-btn:hover {
  background: color-mix(in srgb, var(--notebook-accent) 85%, black);
}

.panel-content {
  flex: 1;
  overflow-y: auto;
  padding: 2rem 2.5rem;
}

.config-container {
  max-width: 640px;
}

.loading-state,
.empty-state {
  padding: 3rem;
  text-align: center;
  color: var(--color-text-tertiary);
}

.empty-state p {
  margin: 0.25rem 0;
}

.agents-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.agent-card {
  border: 1px solid var(--color-border-medium);
  border-radius: 8px;
  overflow: hidden;
  transition: all 0.2s;
}

.agent-card:hover {
  border-color: var(--notebook-accent);
}

.agent-inactive {
  opacity: 0.65;
}

.card-main {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 1.25rem 1.5rem;
  gap: 1rem;
}

.card-header {
  flex: 1;
  min-width: 0;
}

.card-title-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 0.375rem;
  flex-wrap: wrap;
}

.agent-name {
  margin: 0;
  font-size: 1.0625rem;
  font-weight: 600;
  color: var(--color-text-primary);
}

.agent-badges {
  display: flex;
  gap: 0.375rem;
}

.agent-provider,
.agent-model {
  font-size: 0.6875rem;
  padding: 0.125rem 0.5rem;
  border-radius: 10px;
  font-family: var(--font-mono);
}

.agent-provider {
  background: var(--color-bg-tertiary);
  color: var(--color-text-secondary);
}

.agent-model {
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border-light);
  color: var(--color-text-tertiary);
}

.agent-description {
  margin: 0 0 0.5rem;
  font-size: 0.875rem;
  color: var(--color-text-secondary);
  line-height: 1.4;
}

.agent-capabilities {
  display: flex;
  gap: 0.375rem;
}

.cap-badge {
  font-size: 0.6875rem;
  font-weight: 600;
  padding: 0.125rem 0.375rem;
  border-radius: 3px;
  text-transform: uppercase;
}

.cap-read { background: #d4edda; color: #155724; }
.cap-write { background: #cce5ff; color: #004085; }
.cap-create { background: #fff3cd; color: #856404; }
.cap-delete { background: #f8d7da; color: #721c24; }

.card-actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-shrink: 0;
}

.toggle-label {
  position: relative;
  display: inline-block;
  width: 40px;
  height: 22px;
  cursor: pointer;
}

.toggle-checkbox {
  opacity: 0;
  width: 0;
  height: 0;
}

.toggle-slider {
  position: absolute;
  inset: 0;
  background-color: #ccc;
  border-radius: 22px;
  transition: 0.25s;
}

.toggle-slider::before {
  content: "";
  position: absolute;
  height: 16px;
  width: 16px;
  left: 3px;
  bottom: 3px;
  background-color: white;
  border-radius: 50%;
  transition: 0.25s;
}

.toggle-checkbox:checked + .toggle-slider {
  background-color: var(--notebook-accent);
}

.toggle-checkbox:checked + .toggle-slider::before {
  transform: translateX(18px);
}

.action-btn {
  padding: 0.375rem 0.625rem;
  border: 1px solid var(--color-border-medium);
  border-radius: 4px;
  background: none;
  color: var(--color-text-secondary);
  font-size: 0.75rem;
  cursor: pointer;
  transition: all 0.2s;
}

.action-btn:hover {
  background: var(--color-bg-tertiary);
  color: var(--color-text-primary);
}

.action-btn-primary {
  color: var(--notebook-accent);
  border-color: var(--notebook-accent);
}

.action-btn-primary:hover {
  background: color-mix(in srgb, var(--notebook-accent) 10%, transparent);
}

.action-btn-danger {
  color: #dc3545;
  border-color: #dc3545;
}

.action-btn-danger:hover {
  background: rgba(220, 53, 69, 0.1);
}

.card-expanded {
  padding: 1.25rem 1.5rem;
  border-top: 1px solid var(--color-border-light);
  background: var(--color-bg-secondary);
}

.card-expand-btn {
  width: 100%;
  padding: 0.5rem;
  background: var(--color-bg-secondary);
  border: none;
  border-top: 1px solid var(--color-border-light);
  color: var(--color-text-tertiary);
  font-size: 0.75rem;
  cursor: pointer;
  transition: all 0.2s;
}

.card-expand-btn:hover {
  background: var(--color-bg-tertiary);
  color: var(--color-text-primary);
}
</style>
