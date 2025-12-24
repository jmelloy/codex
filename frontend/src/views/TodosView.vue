<template>
  <div class="todos">
    <nav class="navbar">
      <h1>Todos</h1>
      <div class="user-info">
        <router-link to="/" class="nav-link">Home</router-link>
        <router-link to="/markdown" class="nav-link">Markdown Editor</router-link>
        <span>{{ authStore.user?.username }}</span>
        <button @click="handleLogout">Logout</button>
      </div>
    </nav>

    <div class="main-content">
      <div v-if="!workspaceStore.currentWorkspace" class="no-workspace">
        <h2>No workspace selected</h2>
        <p>Please select a workspace from the <router-link to="/">home page</router-link></p>
      </div>

      <div v-else class="todos-container">
        <div class="header">
          <h2>Tasks for {{ workspaceStore.currentWorkspace.name }}</h2>
          <button @click="showCreateTask = true" class="create-btn">+ New Task</button>
        </div>

        <div v-if="taskStore.loading && tasks.length === 0" class="loading">
          Loading tasks...
        </div>

        <div v-if="taskStore.error" class="error">
          {{ taskStore.error }}
        </div>

        <div class="task-sections">
          <div class="task-section">
            <h3>Pending</h3>
            <div class="task-list">
              <div
                v-for="task in pendingTasks"
                :key="task.id"
                class="task-card"
              >
                <div class="task-header">
                  <h4>{{ task.title }}</h4>
                  <div class="task-actions">
                    <button
                      @click="updateStatus(task.id, 'in_progress')"
                      class="btn-secondary"
                    >
                      Start
                    </button>
                  </div>
                </div>
                <p v-if="task.description" class="task-description">
                  {{ task.description }}
                </p>
                <div class="task-meta">
                  <span>Created: {{ formatDate(task.created_at) }}</span>
                </div>
              </div>
              <div v-if="pendingTasks.length === 0" class="empty-state">
                No pending tasks
              </div>
            </div>
          </div>

          <div class="task-section">
            <h3>In Progress</h3>
            <div class="task-list">
              <div
                v-for="task in inProgressTasks"
                :key="task.id"
                class="task-card in-progress"
              >
                <div class="task-header">
                  <h4>{{ task.title }}</h4>
                  <div class="task-actions">
                    <button
                      @click="updateStatus(task.id, 'pending')"
                      class="btn-secondary"
                    >
                      Pause
                    </button>
                    <button
                      @click="updateStatus(task.id, 'completed')"
                      class="btn-primary"
                    >
                      Complete
                    </button>
                  </div>
                </div>
                <p v-if="task.description" class="task-description">
                  {{ task.description }}
                </p>
                <div class="task-meta">
                  <span>Started: {{ formatDate(task.updated_at) }}</span>
                </div>
              </div>
              <div v-if="inProgressTasks.length === 0" class="empty-state">
                No tasks in progress
              </div>
            </div>
          </div>

          <div class="task-section">
            <h3>Completed</h3>
            <div class="task-list">
              <div
                v-for="task in completedTasks"
                :key="task.id"
                class="task-card completed"
              >
                <div class="task-header">
                  <h4>{{ task.title }}</h4>
                  <div class="task-actions">
                    <button
                      @click="updateStatus(task.id, 'pending')"
                      class="btn-secondary"
                    >
                      Reopen
                    </button>
                  </div>
                </div>
                <p v-if="task.description" class="task-description">
                  {{ task.description }}
                </p>
                <div class="task-meta">
                  <!-- Show completed_at if available, otherwise fall back to updated_at -->
                  <span>Completed: {{ task.completed_at ? formatDate(task.completed_at) : formatDate(task.updated_at) }}</span>
                </div>
              </div>
              <div v-if="completedTasks.length === 0" class="empty-state">
                No completed tasks
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Create Task Modal -->
    <div v-if="showCreateTask" class="modal" @click.self="showCreateTask = false">
      <div class="modal-content">
        <h3>Create New Task</h3>
        <form @submit.prevent="handleCreateTask">
          <div class="form-group">
            <label>Title</label>
            <input v-model="newTask.title" required />
          </div>
          <div class="form-group">
            <label>Description (optional)</label>
            <textarea v-model="newTask.description" rows="4"></textarea>
          </div>
          <div class="modal-actions">
            <button type="button" @click="showCreateTask = false">Cancel</button>
            <button type="submit">Create</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useWorkspaceStore } from '../stores/workspace'
import { useTaskStore } from '../stores/tasks'

const router = useRouter()
const authStore = useAuthStore()
const workspaceStore = useWorkspaceStore()
const taskStore = useTaskStore()

const showCreateTask = ref(false)
const newTask = ref({ title: '', description: '' })

const tasks = computed(() => taskStore.tasks)

const pendingTasks = computed(() =>
  tasks.value.filter((t) => t.status === 'pending')
)

const inProgressTasks = computed(() =>
  tasks.value.filter((t) => t.status === 'in_progress')
)

const completedTasks = computed(() =>
  tasks.value.filter((t) => t.status === 'completed')
)

onMounted(async () => {
  // If no workspace is selected, try to load the first available workspace
  if (!workspaceStore.currentWorkspace) {
    await workspaceStore.fetchWorkspaces()
    if (workspaceStore.workspaces.length > 0) {
      // Safe to access index 0 since we just checked length
      workspaceStore.setCurrentWorkspace(workspaceStore.workspaces[0]!)
    }
  }
  
  if (workspaceStore.currentWorkspace) {
    await taskStore.fetchTasks(workspaceStore.currentWorkspace.id)
  }
})

function handleLogout() {
  authStore.logout()
  router.push('/login')
}

async function handleCreateTask() {
  if (!workspaceStore.currentWorkspace) return

  try {
    await taskStore.createTask(
      workspaceStore.currentWorkspace.id,
      newTask.value.title,
      newTask.value.description
    )
    showCreateTask.value = false
    newTask.value = { title: '', description: '' }
  } catch (e) {
    // Error handled in store
  }
}

async function updateStatus(taskId: number, status: string) {
  try {
    await taskStore.updateTask(taskId, status)
  } catch (e) {
    // Error handled in store
  }
}

function formatDate(dateStr: string): string {
  if (!dateStr) return 'N/A'
  try {
    const date = new Date(dateStr)
    if (isNaN(date.getTime())) return 'N/A'
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString()
  } catch {
    return 'N/A'
  }
}
</script>

<style scoped>
.todos {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: #f7fafc;
}

.navbar {
  background: #667eea;
  color: white;
  padding: 1rem 2rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.navbar h1 {
  margin: 0;
  font-size: 1.5rem;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.nav-link {
  color: white;
  text-decoration: none;
  padding: 0.5rem 1rem;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 4px;
  transition: background 0.2s;
}

.nav-link:hover {
  background: rgba(255, 255, 255, 0.3);
}

.user-info button {
  background: rgba(255, 255, 255, 0.2);
  color: white;
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 4px;
  cursor: pointer;
}

.main-content {
  flex: 1;
  padding: 2rem;
}

.no-workspace {
  text-align: center;
  margin-top: 4rem;
}

.no-workspace a {
  color: #667eea;
  text-decoration: none;
}

.todos-container {
  max-width: 1400px;
  margin: 0 auto;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
}

.header h2 {
  margin: 0;
  color: #333;
}

.create-btn {
  background: #667eea;
  color: white;
  border: none;
  padding: 0.75rem 1.5rem;
  border-radius: 4px;
  cursor: pointer;
  font-size: 1rem;
  font-weight: 500;
}

.create-btn:hover {
  background: #5568d3;
}

.loading,
.error {
  text-align: center;
  padding: 2rem;
  color: #666;
}

.error {
  color: #e53e3e;
}

.task-sections {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 2rem;
}

@media (max-width: 1024px) {
  .task-sections {
    grid-template-columns: 1fr;
  }
}

.task-section h3 {
  margin: 0 0 1rem;
  color: #333;
  font-size: 1.1rem;
  font-weight: 600;
}

.task-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.task-card {
  background: white;
  border: 2px solid #e2e8f0;
  border-radius: 8px;
  padding: 1rem;
  transition: box-shadow 0.2s;
}

.task-card:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.task-card.in-progress {
  border-color: #667eea;
  background: #f0f4ff;
}

.task-card.completed {
  border-color: #48bb78;
  background: #f0fdf4;
  opacity: 0.8;
}

.task-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 0.5rem;
}

.task-header h4 {
  margin: 0;
  color: #333;
  font-size: 1rem;
}

.task-actions {
  display: flex;
  gap: 0.5rem;
}

.task-actions button {
  border: none;
  padding: 0.25rem 0.75rem;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.875rem;
}

.btn-primary {
  background: #48bb78;
  color: white;
}

.btn-primary:hover {
  background: #38a169;
}

.btn-secondary {
  background: #e2e8f0;
  color: #333;
}

.btn-secondary:hover {
  background: #cbd5e0;
}

.task-description {
  margin: 0.5rem 0;
  color: #666;
  font-size: 0.875rem;
  line-height: 1.4;
}

.task-meta {
  margin-top: 0.5rem;
  font-size: 0.75rem;
  color: #999;
}

.empty-state {
  text-align: center;
  padding: 2rem;
  color: #999;
  background: white;
  border: 2px dashed #e2e8f0;
  border-radius: 8px;
}

.modal {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  padding: 2rem;
  border-radius: 8px;
  width: 100%;
  max-width: 500px;
}

.modal-content h3 {
  margin: 0 0 1rem;
}

.form-group {
  margin-bottom: 1rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 500;
}

.form-group input,
.form-group textarea {
  width: 100%;
  padding: 0.5rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  box-sizing: border-box;
  font-family: inherit;
}

.modal-actions {
  display: flex;
  gap: 0.5rem;
  justify-content: flex-end;
  margin-top: 1.5rem;
}

.modal-actions button {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.modal-actions button[type='button'] {
  background: #e2e8f0;
}

.modal-actions button[type='submit'] {
  background: #667eea;
  color: white;
}
</style>
