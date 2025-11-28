<script setup lang="ts">
import { RouterView } from 'vue-router'
</script>

<template>
  <div class="app">
    <header class="app-header">
      <nav>
        <RouterLink to="/" class="nav-brand">Codex</RouterLink>
        <div class="nav-links">
          <RouterLink to="/notebooks">Notebooks</RouterLink>
          <RouterLink to="/search">Search</RouterLink>
        </div>
      </nav>
    </header>
    <main class="app-main">
      <RouterView />
    </main>
  </div>
</template>

<style scoped>
.app {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.app-header {
  background: var(--color-primary);
  padding: 1rem 2rem;
}

.app-header nav {
  display: flex;
  justify-content: space-between;
  align-items: center;
  max-width: 1400px;
  margin: 0 auto;
}

.nav-brand {
  font-size: 1.5rem;
  font-weight: 700;
  color: white;
  text-decoration: none;
}

.nav-links {
  display: flex;
  gap: 1.5rem;
}

.nav-links a {
  color: rgba(255, 255, 255, 0.9);
  text-decoration: none;
  font-weight: 500;
}

.nav-links a:hover,
.nav-links a.router-link-active {
  color: white;
}

.app-main {
  flex: 1;
  padding: 2rem;
  max-width: 1400px;
  margin: 0 auto;
  width: 100%;
}
</style>
