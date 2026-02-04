<template>
  <div class="h-screen flex flex-col w-full">
    <nav class="bg-primary text-white px-8 py-4 flex justify-between items-center">
      <h1 class="text-2xl font-semibold m-0">Codex - Settings</h1>
      <div class="flex items-center gap-4">
        <button
          @click="goBack"
          class="bg-white/20 text-white border-none px-4 py-2 rounded cursor-pointer hover:bg-white/30 transition"
        >
          ← Back
        </button>
        <span>{{ authStore.user?.username }}</span>
        <button
          @click="handleLogout"
          class="bg-white/20 text-white border-none px-4 py-2 rounded cursor-pointer hover:bg-white/30 transition"
        >
          Logout
        </button>
      </div>
    </nav>

    <div class="flex-1 flex overflow-hidden">
      <!-- Sidebar -->
      <aside class="w-64 bg-bg-secondary border-r border-border-medium overflow-y-auto">
        <nav class="p-4">
          <div class="mb-6">
            <h3 class="text-xs font-semibold uppercase text-text-secondary mb-2 px-3">
              Settings
            </h3>
            <ul class="space-y-1">
              <li>
                <router-link
                  to="/settings/user"
                  :class="[
                    'block px-3 py-2 rounded-md text-sm transition-colors',
                    $route.path === '/settings/user'
                      ? 'bg-primary text-white'
                      : 'text-text-primary hover:bg-bg-tertiary',
                  ]"
                >
                  User Preferences
                </router-link>
              </li>
              <li>
                <router-link
                  to="/settings/workspace"
                  :class="[
                    'block px-3 py-2 rounded-md text-sm transition-colors',
                    $route.path === '/settings/workspace'
                      ? 'bg-primary text-white'
                      : 'text-text-primary hover:bg-bg-tertiary',
                  ]"
                >
                  Workspace Preferences
                </router-link>
              </li>
              <li>
                <router-link
                  to="/settings/notebook"
                  :class="[
                    'block px-3 py-2 rounded-md text-sm transition-colors',
                    $route.path === '/settings/notebook'
                      ? 'bg-primary text-white'
                      : 'text-text-primary hover:bg-bg-tertiary',
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
      <main class="flex-1 overflow-y-auto">
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
/* Additional styling if needed */
</style>
