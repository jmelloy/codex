<template>
  <div class="agent-chat">
    <!-- Header -->
    <div class="chat-header">
      <div class="header-info">
        <div class="header-agent-select" v-if="!session">
          <select v-model="selectedAgentId" class="agent-select" @change="handleAgentChange">
            <option :value="null" disabled>Select an agent...</option>
            <option v-for="agent in agents" :key="agent.id" :value="agent.id">
              {{ agent.name }} ({{ agent.model }})
            </option>
          </select>
        </div>
        <div v-else class="header-title">
          <strong>{{ currentAgent?.name }}</strong>
          <span class="header-model">{{ currentAgent?.model }}</span>
          <span :class="['header-status', `status-${session.status}`]">
            {{ session.status }}
          </span>
        </div>
      </div>
      <div class="header-actions">
        <button
          v-if="session && !isSessionDone"
          @click="handleCancel"
          class="header-btn header-btn-danger"
          title="Cancel session"
        >
          Cancel
        </button>
        <button
          v-if="session && isSessionDone"
          @click="handleNewSession"
          class="header-btn"
          title="New session"
        >
          New
        </button>
        <button @click="$emit('close')" class="header-btn" title="Close">
          &times;
        </button>
      </div>
    </div>

    <!-- Notebook selector (before session starts) -->
    <div v-if="!session && selectedAgentId" class="notebook-selector">
      <label class="nb-label">Notebook path:</label>
      <input
        v-model="notebookPath"
        type="text"
        placeholder="/path/to/notebook"
        class="nb-input"
      />
      <button
        @click="handleStartSession"
        :disabled="!notebookPath.trim() || sessionLoading"
        class="nb-start-btn"
      >
        {{ sessionLoading ? "Starting..." : "Start Session" }}
      </button>
    </div>

    <!-- Messages -->
    <div ref="messagesContainer" class="chat-messages">
      <div v-if="messages.length === 0 && !session" class="chat-empty">
        <p>Select an agent and start a session to begin chatting.</p>
      </div>
      <div v-else-if="messages.length === 0 && session" class="chat-empty">
        <p>Session started. Send a message to begin.</p>
      </div>
      <template v-else>
        <div
          v-for="(msg, idx) in messages"
          :key="idx"
          :class="['message', `message-${msg.role}`]"
        >
          <div class="message-role">{{ roleLabel(msg.role) }}</div>
          <div class="message-content">
            <div v-if="msg.content" class="message-text" v-html="renderContent(msg.content)" />

            <!-- Tool calls -->
            <div v-if="msg.toolCalls && msg.toolCalls.length > 0" class="tool-calls">
              <div v-for="tc in msg.toolCalls" :key="tc.id" class="tool-call-item">
                <div class="tool-call-header">
                  <span class="tool-call-name">{{ tc.name }}</span>
                </div>
                <pre class="tool-call-args">{{ JSON.stringify(tc.arguments, null, 2) }}</pre>
              </div>
            </div>
          </div>
          <div class="message-time">{{ formatTime(msg.timestamp) }}</div>
        </div>
      </template>

      <!-- Loading indicator -->
      <div v-if="sendingMessage" class="message message-assistant">
        <div class="message-role">Agent</div>
        <div class="message-content">
          <div class="typing-indicator">
            <span></span><span></span><span></span>
          </div>
        </div>
      </div>
    </div>

    <!-- Input -->
    <div v-if="session && !isSessionDone" class="chat-input">
      <textarea
        ref="inputEl"
        v-model="inputText"
        @keydown="handleKeydown"
        placeholder="Type a message..."
        rows="1"
        class="input-field"
        :disabled="sendingMessage"
      />
      <button
        @click="handleSend"
        :disabled="!inputText.trim() || sendingMessage"
        class="send-btn"
      >
        Send
      </button>
    </div>

    <!-- Session ended banner -->
    <div v-if="session && isSessionDone" class="session-ended">
      Session {{ session.status }}.
      <button @click="handleNewSession" class="new-session-link">Start a new session</button>
    </div>

    <!-- Error -->
    <div v-if="error" class="chat-error">
      {{ error }}
      <button @click="agentStore.error = null" class="error-dismiss">&times;</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick, onMounted } from "vue"
import { useAgentStore, type ChatMessage } from "../../stores/agent"
import type { Agent, AgentSession } from "../../services/agent"

const props = defineProps<{
  workspaceId: number
  initialNotebookPath?: string
}>()

defineEmits<{
  close: []
}>()

const agentStore = useAgentStore()

const selectedAgentId = ref<number | null>(agentStore.currentAgent?.id ?? null)
const notebookPath = ref(props.initialNotebookPath || "")
const inputText = ref("")
const messagesContainer = ref<HTMLElement | null>(null)
const inputEl = ref<HTMLTextAreaElement | null>(null)

const agents = computed<Agent[]>(() => agentStore.activeAgents)
const currentAgent = computed(() => agentStore.currentAgent)
const session = computed<AgentSession | null>(() => agentStore.currentSession)
const messages = computed<ChatMessage[]>(() => agentStore.chatMessages)
const sendingMessage = computed(() => agentStore.sendingMessage)
const sessionLoading = computed(() => agentStore.sessionLoading)
const error = computed(() => agentStore.error)

const isSessionDone = computed(
  () =>
    session.value !== null &&
    ["completed", "failed", "cancelled"].includes(session.value.status)
)

function handleAgentChange() {
  if (selectedAgentId.value) {
    const agent = agents.value.find((a) => a.id === selectedAgentId.value)
    if (agent) agentStore.selectAgent(agent)
  }
}

async function handleStartSession() {
  if (!selectedAgentId.value || !notebookPath.value.trim()) return
  await agentStore.startSession(selectedAgentId.value, notebookPath.value.trim())
  nextTick(() => inputEl.value?.focus())
}

async function handleSend() {
  const text = inputText.value.trim()
  if (!text) return
  inputText.value = ""
  await agentStore.sendMessage(text)
  scrollToBottom()
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault()
    handleSend()
  }
}

async function handleCancel() {
  await agentStore.cancelSession()
}

function handleNewSession() {
  agentStore.clearChat()
}

function roleLabel(role: string): string {
  switch (role) {
    case "user":
      return "You"
    case "assistant":
      return "Agent"
    case "system":
      return "System"
    case "tool":
      return "Tool"
    default:
      return role
  }
}

function renderContent(content: string): string {
  // Basic markdown-like rendering: code blocks, bold, inline code
  return content
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/```(\w*)\n([\s\S]*?)```/g, '<pre class="code-block"><code>$2</code></pre>')
    .replace(/`([^`]+)`/g, '<code class="inline-code">$1</code>')
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\n/g, "<br>")
}

function formatTime(date: Date): string {
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
}

function scrollToBottom() {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

// Auto-scroll on new messages
watch(
  () => messages.value.length,
  () => scrollToBottom()
)

// Load agents on mount
onMounted(async () => {
  if (agents.value.length === 0) {
    await agentStore.fetchAgents(props.workspaceId)
  }
  if (agentStore.currentAgent) {
    selectedAgentId.value = agentStore.currentAgent.id
  }
})
</script>

<style scoped>
.agent-chat {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--color-bg-primary);
}

/* Header */
.chat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 1rem;
  border-bottom: 1px solid var(--color-border-medium);
  background: var(--color-bg-secondary);
  flex-shrink: 0;
}

.header-info {
  flex: 1;
  min-width: 0;
}

.agent-select {
  padding: 0.375rem 0.5rem;
  border: 1px solid var(--color-border-medium);
  border-radius: 4px;
  background: var(--color-bg-primary);
  color: var(--color-text-primary);
  font-size: 0.875rem;
  width: 100%;
  max-width: 300px;
}

.header-title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
  color: var(--color-text-primary);
}

.header-model {
  font-size: 0.75rem;
  color: var(--color-text-tertiary);
  font-family: var(--font-mono);
}

.header-status {
  font-size: 0.6875rem;
  font-weight: 600;
  padding: 0.125rem 0.375rem;
  border-radius: 3px;
  text-transform: uppercase;
}

.status-pending { background: #fff3cd; color: #856404; }
.status-running { background: #cce5ff; color: #004085; }
.status-completed { background: #d4edda; color: #155724; }
.status-failed { background: #f8d7da; color: #721c24; }
.status-cancelled { background: var(--color-bg-tertiary); color: var(--color-text-tertiary); }

.header-actions {
  display: flex;
  gap: 0.5rem;
  flex-shrink: 0;
}

.header-btn {
  background: none;
  border: 1px solid var(--color-border-medium);
  padding: 0.25rem 0.625rem;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.8125rem;
  color: var(--color-text-primary);
  transition: all 0.2s;
}

.header-btn:hover {
  background: var(--color-bg-tertiary);
}

.header-btn-danger {
  color: #dc3545;
  border-color: #dc3545;
}

.header-btn-danger:hover {
  background: rgba(220, 53, 69, 0.1);
}

/* Notebook selector */
.notebook-selector {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  border-bottom: 1px solid var(--color-border-light);
  background: var(--color-bg-secondary);
  flex-shrink: 0;
}

.nb-label {
  font-size: 0.8125rem;
  font-weight: 500;
  color: var(--color-text-secondary);
  white-space: nowrap;
}

.nb-input {
  flex: 1;
  padding: 0.375rem 0.5rem;
  border: 1px solid var(--color-border-medium);
  border-radius: 4px;
  background: var(--color-bg-primary);
  color: var(--color-text-primary);
  font-size: 0.8125rem;
  font-family: var(--font-mono);
}

.nb-input:focus {
  outline: none;
  border-color: var(--notebook-accent);
}

.nb-start-btn {
  padding: 0.375rem 0.75rem;
  background: var(--notebook-accent);
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 0.8125rem;
  cursor: pointer;
  white-space: nowrap;
  transition: background 0.2s;
}

.nb-start-btn:hover:not(:disabled) {
  background: color-mix(in srgb, var(--notebook-accent) 85%, black);
}

.nb-start-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* Messages */
.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.chat-empty {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-text-tertiary);
  font-size: 0.875rem;
}

.message {
  display: flex;
  flex-direction: column;
  max-width: 85%;
}

.message-user {
  align-self: flex-end;
}

.message-assistant,
.message-system,
.message-tool {
  align-self: flex-start;
}

.message-role {
  font-size: 0.6875rem;
  font-weight: 600;
  text-transform: uppercase;
  color: var(--color-text-tertiary);
  margin-bottom: 0.25rem;
}

.message-user .message-role {
  text-align: right;
}

.message-content {
  padding: 0.625rem 0.875rem;
  border-radius: 8px;
  font-size: 0.875rem;
  line-height: 1.5;
}

.message-user .message-content {
  background: var(--notebook-accent);
  color: white;
  border-bottom-right-radius: 2px;
}

.message-assistant .message-content {
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border-light);
  color: var(--color-text-primary);
  border-bottom-left-radius: 2px;
}

.message-system .message-content {
  background: #fff3cd;
  border: 1px solid #ffc107;
  color: #856404;
  font-size: 0.8125rem;
}

.message-tool .message-content {
  background: var(--color-bg-tertiary);
  border: 1px solid var(--color-border-light);
  color: var(--color-text-secondary);
  font-size: 0.8125rem;
  font-family: var(--font-mono);
}

.message-text :deep(.code-block) {
  background: rgba(0, 0, 0, 0.08);
  padding: 0.5rem;
  border-radius: 4px;
  margin: 0.5rem 0;
  overflow-x: auto;
  font-family: var(--font-mono);
  font-size: 0.8125rem;
}

.message-text :deep(.inline-code) {
  background: rgba(0, 0, 0, 0.08);
  padding: 0.125rem 0.375rem;
  border-radius: 3px;
  font-family: var(--font-mono);
  font-size: 0.8125rem;
}

.message-user .message-text :deep(.code-block),
.message-user .message-text :deep(.inline-code) {
  background: rgba(255, 255, 255, 0.2);
}

.message-time {
  font-size: 0.6875rem;
  color: var(--color-text-tertiary);
  margin-top: 0.25rem;
}

.message-user .message-time {
  text-align: right;
}

/* Tool calls */
.tool-calls {
  margin-top: 0.5rem;
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

.tool-call-item {
  background: var(--color-bg-primary);
  border: 1px solid var(--color-border-light);
  border-radius: 4px;
  overflow: hidden;
}

.tool-call-header {
  padding: 0.375rem 0.625rem;
  background: var(--color-bg-tertiary);
  border-bottom: 1px solid var(--color-border-light);
}

.tool-call-name {
  font-weight: 600;
  font-size: 0.75rem;
  font-family: var(--font-mono);
  color: var(--notebook-accent);
}

.tool-call-args {
  margin: 0;
  padding: 0.375rem 0.625rem;
  font-size: 0.6875rem;
  font-family: var(--font-mono);
  color: var(--color-text-secondary);
  max-height: 6rem;
  overflow-y: auto;
}

/* Typing indicator */
.typing-indicator {
  display: flex;
  gap: 0.25rem;
  padding: 0.25rem 0;
}

.typing-indicator span {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--color-text-tertiary);
  animation: typing 1.4s infinite;
}

.typing-indicator span:nth-child(2) {
  animation-delay: 0.2s;
}

.typing-indicator span:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes typing {
  0%, 60%, 100% { opacity: 0.3; transform: scale(0.8); }
  30% { opacity: 1; transform: scale(1); }
}

/* Input */
.chat-input {
  display: flex;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  border-top: 1px solid var(--color-border-medium);
  background: var(--color-bg-secondary);
  flex-shrink: 0;
}

.input-field {
  flex: 1;
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--color-border-medium);
  border-radius: 6px;
  background: var(--color-bg-primary);
  color: var(--color-text-primary);
  font-size: 0.875rem;
  resize: none;
  max-height: 6rem;
  line-height: 1.4;
}

.input-field:focus {
  outline: none;
  border-color: var(--notebook-accent);
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--notebook-accent) 15%, transparent);
}

.input-field:disabled {
  opacity: 0.6;
}

.send-btn {
  padding: 0.5rem 1rem;
  background: var(--notebook-accent);
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s;
  align-self: flex-end;
}

.send-btn:hover:not(:disabled) {
  background: color-mix(in srgb, var(--notebook-accent) 85%, black);
}

.send-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* Session ended */
.session-ended {
  padding: 0.75rem 1rem;
  text-align: center;
  font-size: 0.875rem;
  color: var(--color-text-secondary);
  border-top: 1px solid var(--color-border-light);
  background: var(--color-bg-secondary);
  flex-shrink: 0;
}

.new-session-link {
  background: none;
  border: none;
  color: var(--notebook-accent);
  cursor: pointer;
  text-decoration: underline;
  font-size: 0.875rem;
}

/* Error */
.chat-error {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.5rem 1rem;
  background: #f8d7da;
  color: #721c24;
  font-size: 0.8125rem;
  flex-shrink: 0;
}

.error-dismiss {
  background: none;
  border: none;
  color: #721c24;
  cursor: pointer;
  font-size: 1.25rem;
  line-height: 1;
}
</style>
