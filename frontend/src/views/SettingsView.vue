<template>
  <div class="h-screen flex flex-col w-full">
    <nav class="settings-nav px-8 py-4 flex justify-between items-center">
      <h1 class="text-2xl font-semibold m-0">Codex - Settings</h1>
      <div class="flex items-center gap-4">
        <button
          @click="goBack"
          class="settings-nav-button border-none px-4 py-2 rounded cursor-pointer transition"
        >
          ← Back
        </button>
        <span>{{ authStore.user?.username }}</span>
        <button
          @click="handleLogout"
          class="settings-nav-button border-none px-4 py-2 rounded cursor-pointer transition"
        >
          Logout
        </button>
      </div>
    </nav>

    <div class="flex-1 flex overflow-hidden">
      <!-- Sidebar -->
      <aside class="settings-sidebar w-64 overflow-y-auto">
        <nav class="p-4">
          <div class="mb-6">
            <h3 class="settings-sidebar-heading text-xs font-semibold uppercase mb-2 px-3">
              Settings
            </h3>
            <ul class="space-y-1">
              <li>
                <router-link
                  to="/settings/user"
                  :class="[
                    'settings-nav-link block px-3 py-2 rounded-md text-sm transition-colors',
                    { 'settings-nav-link-active': $route.path === '/settings/user' },
                  ]"
                >
                  User Preferences
                </router-link>
              </li>
              <li>
                <router-link
                  to="/settings/workspace"
                  :class="[
                    'settings-nav-link block px-3 py-2 rounded-md text-sm transition-colors',
                    { 'settings-nav-link-active': $route.path === '/settings/workspace' },
                  ]"
                >
                  Workspace Preferences
                </router-link>
              </li>
              <li>
                <router-link
                  to="/settings/notebook"
                  :class="[
                    'settings-nav-link block px-3 py-2 rounded-md text-sm transition-colors',
                    { 'settings-nav-link-active': $route.path === '/settings/notebook' },
                  ]"
                >
                  Notebook Preferences
                </router-link>
              </li>
            </ul>
          </div>
        </nav>
      </aside>

      <!-- Main Content -->
      <main class="settings-main flex-1 overflow-y-auto">
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from "vue-router"
import { useAuthStore } from "../stores/auth"

const router = useRouter()
const authStore = useAuthStore()

function goBack() {
  router.push("/")
}

function handleLogout() {
  authStore.logout()
  router.push("/login")
}
</script>

<style scoped>
/* Settings navigation - theme aware */
.settings-nav {
  background: var(--notebook-accent);
  color: var(--color-text-inverse);
}

.settings-nav-button {
  background: color-mix(in srgb, white 20%, transparent);
  color: var(--color-text-inverse);
}

.settings-nav-button:hover {
  background: color-mix(in srgb, white 30%, transparent);
}

/* Settings sidebar - theme aware */
.settings-sidebar {
  background: var(--color-bg-secondary);
  border-right: 1px solid var(--color-border-medium);
}

.settings-sidebar-heading {
  color: var(--color-text-secondary);
}

.settings-nav-link {
  color: var(--color-text-primary);
}

.settings-nav-link:hover:not(.settings-nav-link-active) {
  background: var(--color-bg-tertiary);
}

.settings-nav-link-active {
  background: var(--notebook-accent);
  color: var(--color-text-inverse);
}

/* Main content area */
.settings-main {
  background: var(--color-bg-primary);
}
</style>
