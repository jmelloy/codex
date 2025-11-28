<script setup lang="ts"></script>

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
        <p>
          Organize your work into notebooks, pages, and entries for structured
          documentation.
        </p>
      </div>
      <div class="feature card">
        <h3>🔗 Lineage Tracking</h3>
        <p>
          Track the evolution of your work with parent-child
          relationships and variations.
        </p>
      </div>
      <div class="feature card">
        <h3>📦 Content-Addressable Storage</h3>
        <p>
          Deduplicated artifact storage with automatic thumbnails and efficient
          retrieval.
        </p>
      </div>
      <div class="feature card">
        <h3>🔍 Search</h3>
        <p>
          Find any entry, artifact, or content with powerful search
          capabilities.
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
  content: '';
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
