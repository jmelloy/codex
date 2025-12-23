<script setup lang="ts">
import { useAuthStore } from "@/stores/auth";

const authStore = useAuthStore();
</script>

<template>
  <div class="home">
    <section class="hero">
      <h1>Welcome to Codex</h1>
      <p class="subtitle">A markdown-first digital laboratory journal</p>
      <div class="hero-actions">
        <RouterLink
          v-if="authStore.isAuthenticated"
          to="/files"
          class="btn btn-primary"
        >
          View Files
        </RouterLink>
        <template v-else>
          <RouterLink to="/login" class="btn btn-primary"> Login </RouterLink>
          <RouterLink to="/register" class="btn btn-secondary">
            Register
          </RouterLink>
        </template>
      </div>
      <div v-if="authStore.user" class="user-info">
        Logged in as <strong>{{ authStore.user.username }}</strong>
      </div>
    </section>

    <section class="features">
      <div class="feature card">
        <h3>📝 Markdown Files</h3>
        <p>
          All your research stored in human-readable markdown files with YAML
          frontmatter for metadata.
        </p>
      </div>
      <div class="feature card">
        <h3>🗂️ File Browser</h3>
        <p>
          Navigate your workspace like a file system with folders, markdown
          documents, and artifacts.
        </p>
      </div>
      <div class="feature card">
        <h3>🔍 Indexed Search</h3>
        <p>
          Fast searching across frontmatter metadata stored in SQLite for quick
          access to any document.
        </p>
      </div>
      <div class="feature card">
        <h3>🔗 Git-Friendly</h3>
        <p>
          Clean, readable diffs and easy collaboration with version control
          systems like Git.
        </p>
      </div>
    </section>
  </div>
</template>

<style scoped>
.home {
  max-width: 1000px;
  margin: 0 auto;
  padding: 2rem;
}

.hero {
  text-align: center;
  padding: 4rem 2rem;
  position: relative;
}

.hero h1 {
  font-size: 3.5rem;
  margin-bottom: 1rem;
  color: var(--color-primary);
  font-family: var(--font-handwritten);
  font-weight: 700;
  letter-spacing: 0.02em;
}

.subtitle {
  font-size: 1.25rem;
  color: var(--color-text-secondary);
  margin-bottom: 2rem;
  font-style: italic;
}

.hero-actions {
  display: flex;
  justify-content: center;
  gap: 1rem;
}

.user-info {
  margin-top: 1.5rem;
  color: var(--color-text-secondary);
  font-size: 0.95rem;
}

.btn-secondary {
  background-color: #6c757d;
}

.btn-secondary:hover {
  background-color: #5a6268;
}

.features {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 1.5rem;
  padding: 2rem 0;
}

.feature {
  position: relative;
  transition: transform 0.2s ease;
}

.feature:hover {
  transform: rotate(-0.5deg) translateY(-2px);
}

.feature:nth-child(even):hover {
  transform: rotate(0.5deg) translateY(-2px);
}

.feature h3 {
  margin-bottom: 0.75rem;
  font-family: var(--font-handwritten);
  font-size: 1.5rem;
  color: var(--color-primary);
}

.feature p {
  color: var(--color-text-secondary);
  line-height: 1.6;
}

/* Decorative notebook spiral holes using CSS circles */
.hero::before {
  content: "";
  position: absolute;
  top: 1rem;
  left: 50%;
  transform: translateX(-50%);
  width: 300px;
  height: 12px;
  background-image: radial-gradient(
    circle at center,
    var(--color-border) 4px,
    transparent 4px
  );
  background-size: 28px 12px;
  background-repeat: repeat-x;
  opacity: 0.8;
}
</style>
