<script setup lang="ts">
</script>

<template>
  <div class="home">
    <section class="hero">
      <h1>Welcome to Codex</h1>
      <p class="subtitle">A hierarchical digital laboratory journal system</p>
      <div class="hero-actions">
        <RouterLink to="/notebooks" class="btn btn-primary">
          View Notebooks
        </RouterLink>
      </div>
    </section>

    <section class="features">
      <div class="feature card">
        <h3>📓 Notebooks</h3>
        <p>Organize your work into notebooks, pages, and entries for structured experimentation.</p>
      </div>
      <div class="feature card">
        <h3>🔗 Lineage Tracking</h3>
        <p>Track the evolution of your experiments with parent-child relationships and variations.</p>
      </div>
      <div class="feature card">
        <h3>📦 Content-Addressable Storage</h3>
        <p>Deduplicated artifact storage with automatic thumbnails and efficient retrieval.</p>
      </div>
      <div class="feature card">
        <h3>🔍 Search</h3>
        <p>Find any entry, artifact, or experiment with powerful search capabilities.</p>
      </div>
    </section>
  </div>
</template>

<style scoped>
.home {
  max-width: 1000px;
  margin: 0 auto;
}

.hero {
  text-align: center;
  padding: 4rem 2rem;
}

.hero h1 {
  font-size: 3rem;
  margin-bottom: 1rem;
  color: var(--color-primary);
}

.subtitle {
  font-size: 1.25rem;
  color: var(--color-text-secondary);
  margin-bottom: 2rem;
}

.hero-actions {
  display: flex;
  justify-content: center;
  gap: 1rem;
}

.features {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 1.5rem;
  padding: 2rem 0;
}

.feature h3 {
  margin-bottom: 0.5rem;
}

.feature p {
  color: var(--color-text-secondary);
}
</style>
