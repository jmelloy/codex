<template>
  <div class="home">
    <nav class="navbar">
      <h1>Codex</h1>
      <div class="user-info">
        <router-link to="/todos" class="nav-link">Todos</router-link>
        <router-link to="/markdown" class="nav-link">Markdown Editor</router-link>
        <span>{{ authStore.user?.username }}</span>
        <button @click="handleLogout">Logout</button>
      </div>
    </nav>

    <div class="main-content">
      <aside class="sidebar">
        <div class="sidebar-header">
          <h2>Workspaces</h2>
          <button @click="showCreateWorkspace = true">+</button>
        </div>
        <ul class="workspace-list">
          <li
            v-for="workspace in workspaceStore.workspaces"
            :key="workspace.id"
            :class="{ active: workspaceStore.currentWorkspace?.id === workspace.id }"
            @click="selectWorkspace(workspace)"
          >
            {{ workspace.name }}
          </li>
        </ul>
        
        <div v-if="workspaceStore.currentWorkspace" class="notebooks-section">
          <div class="sidebar-header">
            <h3>Notebooks</h3>
            <button @click="showCreateNotebook = true">+</button>
          </div>
          <ul class="notebook-list">
            <li v-for="notebook in workspaceStore.notebooks" :key="notebook.id">
              {{ notebook.name }}
            </li>
          </ul>
        </div>
      </aside>

      <main class="content">
        <div v-if="!workspaceStore.currentWorkspace" class="welcome">
          <h2>Welcome to Codex</h2>
          <p>Select a workspace to get started</p>
        </div>
        <div v-else class="workspace-view">
          <h2>{{ workspaceStore.currentWorkspace.name }}</h2>
          <p>{{ workspaceStore.currentWorkspace.path }}</p>
        </div>
      </main>
    </div>

    <!-- Create Workspace Modal -->
    <div v-if="showCreateWorkspace" class="modal" @click.self="showCreateWorkspace = false">
      <div class="modal-content">
        <h3>Create Workspace</h3>
        <form @submit.prevent="handleCreateWorkspace">
          <div class="form-group">
            <label>Name</label>
            <input v-model="newWorkspace.name" required />
          </div>
          <div class="form-group">
            <label>Path</label>
            <input v-model="newWorkspace.path" required />
          </div>
          <div class="modal-actions">
            <button type="button" @click="showCreateWorkspace = false">Cancel</button>
            <button type="submit">Create</button>
          </div>
        </form>
      </div>
    </div>

    <!-- Create Notebook Modal -->
    <div v-if="showCreateNotebook" class="modal" @click.self="showCreateNotebook = false">
      <div class="modal-content">
        <h3>Create Notebook</h3>
        <form @submit.prevent="handleCreateNotebook">
          <div class="form-group">
            <label>Name</label>
            <input v-model="newNotebook.name" required />
          </div>
          <div class="form-group">
            <label>Path</label>
            <input v-model="newNotebook.path" required />
          </div>
          <div class="modal-actions">
            <button type="button" @click="showCreateNotebook = false">Cancel</button>
            <button type="submit">Create</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useWorkspaceStore } from '../stores/workspace'
import type { Workspace } from '../services/codex'

const router = useRouter()
const authStore = useAuthStore()
const workspaceStore = useWorkspaceStore()

const showCreateWorkspace = ref(false)
const showCreateNotebook = ref(false)
const newWorkspace = ref({ name: '', path: '' })
const newNotebook = ref({ name: '', path: '' })

onMounted(async () => {
  await workspaceStore.fetchWorkspaces()
})

function handleLogout() {
  authStore.logout()
  router.push('/login')
}

function selectWorkspace(workspace: Workspace) {
  workspaceStore.setCurrentWorkspace(workspace)
}

async function handleCreateWorkspace() {
  try {
    await workspaceStore.createWorkspace(newWorkspace.value.name, newWorkspace.value.path)
    showCreateWorkspace.value = false
    newWorkspace.value = { name: '', path: '' }
  } catch (e) {
    // Error handled in store
  }
}

async function handleCreateNotebook() {
  if (!workspaceStore.currentWorkspace) return
  
  try {
    await workspaceStore.createNotebook(
      workspaceStore.currentWorkspace.id,
      newNotebook.value.name,
      newNotebook.value.path
    )
    showCreateNotebook.value = false
    newNotebook.value = { name: '', path: '' }
  } catch (e) {
    // Error handled in store
  }
}
</script>

<style scoped>
.home {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
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
  display: flex;
  flex: 1;
}

.sidebar {
  width: 250px;
  background: #f7fafc;
  border-right: 1px solid #e2e8f0;
  padding: 1rem;
}

.sidebar-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.sidebar-header h2,
.sidebar-header h3 {
  margin: 0;
  font-size: 1rem;
}

.sidebar-header button {
  background: #667eea;
  color: white;
  border: none;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  cursor: pointer;
  font-size: 1.2rem;
  display: flex;
  align-items: center;
  justify-content: center;
}

.workspace-list,
.notebook-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.workspace-list li,
.notebook-list li {
  padding: 0.5rem;
  cursor: pointer;
  border-radius: 4px;
  margin-bottom: 0.25rem;
}

.workspace-list li:hover,
.notebook-list li:hover {
  background: #e2e8f0;
}

.workspace-list li.active {
  background: #667eea;
  color: white;
}

.notebooks-section {
  margin-top: 2rem;
}

.content {
  flex: 1;
  padding: 2rem;
}

.welcome {
  text-align: center;
  margin-top: 4rem;
}

.welcome h2 {
  color: #333;
  margin-bottom: 0.5rem;
}

.welcome p {
  color: #666;
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
  max-width: 400px;
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

.form-group input {
  width: 100%;
  padding: 0.5rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  box-sizing: border-box;
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
