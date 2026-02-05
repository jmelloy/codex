<template>
  <div class="min-h-screen flex flex-col notebook-texture w-full">
    <!-- Header -->
    <nav class="bg-primary text-white px-8 py-4 flex justify-between items-center shadow-md">
      <h1 class="m-0 text-2xl">Page Viewer</h1>
      <div>
        <router-link
          to="/"
          class="text-white no-underline px-4 py-2 bg-bg-primary/20 rounded transition hover:bg-bg-primary/30"
        >
          ← Back to Home
        </router-link>
      </div>
    </nav>

    <!-- Loading State -->
    <div v-if="loading" class="flex-1 flex items-center justify-center">
      <div class="text-text-secondary">Loading page...</div>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="flex-1 flex items-center justify-center">
      <div class="text-red-600">{{ error }}</div>
    </div>

    <!-- Page Content -->
    <div v-else-if="page" class="flex-1 p-8 max-w-5xl mx-auto w-full">
      <!-- Page Header -->
      <div class="mb-8 pb-6 border-b-2 border-border-light">
        <h1 class="text-4xl font-bold text-text-primary mb-2">
          {{ page.title || "Untitled Page" }}
        </h1>
        <p v-if="page.description" class="text-lg text-text-secondary mb-4">
          {{ page.description }}
        </p>
        <div class="flex gap-4 text-sm text-text-tertiary">
          <span v-if="page.created_at">
            Created: {{ formatDate(page.created_at) }}
          </span>
          <span v-if="page.updated_at">
            Updated: {{ formatDate(page.updated_at) }}
          </span>
          <span>
            {{ page.blocks.length }} {{ page.blocks.length === 1 ? "block" : "blocks" }}
          </span>
        </div>
      </div>

      <!-- Blocks List -->
      <div v-if="page.blocks.length > 0" class="space-y-6">
        <div
          v-for="block in page.blocks"
          :key="block.position"
          class="bg-white rounded-lg shadow-sm border border-border-light p-6 hover:shadow-md transition-shadow"
        >
          <!-- Block Header -->
          <div class="flex items-start gap-4 mb-4">
            <div
              class="flex-shrink-0 w-12 h-12 bg-primary text-white rounded-full flex items-center justify-center font-bold text-lg"
            >
              {{ block.position }}
            </div>
            <div class="flex-1">
              <div class="flex items-center gap-2 mb-1">
                <!-- Block Type Icon -->
                <span v-if="block.type === 'markdown'" class="text-2xl" title="Markdown file">
                  📝
                </span>
                <span v-else-if="isImage(block.name)" class="text-2xl" title="Image file">
                  🖼️
                </span>
                <span v-else-if="isCode(block.name)" class="text-2xl" title="Code file">
                  💻
                </span>
                <span v-else-if="isData(block.name)" class="text-2xl" title="Data file">
                  📊
                </span>
                <span v-else class="text-2xl" title="File">
                  📄
                </span>
                
                <h3 class="text-xl font-semibold text-text-primary m-0">
                  {{ block.name }}
                </h3>
              </div>
              <p class="text-sm text-text-tertiary m-0">
                {{ block.file }}
              </p>
            </div>
          </div>

          <!-- Block Content Preview -->
          <div class="mt-4 p-4 bg-bg-secondary rounded">
            <div v-if="block.type === 'markdown'" class="text-text-secondary">
              <a
                :href="`/markdown?file=${encodeURIComponent(block.path)}`"
                class="text-primary hover:underline"
              >
                View markdown content →
              </a>
            </div>
            <div v-else-if="isImage(block.name)" class="text-text-secondary">
              Image file: {{ block.name }}
            </div>
            <div v-else class="text-text-secondary">
              File: {{ block.name }}
            </div>
          </div>
        </div>
      </div>

      <!-- Empty State -->
      <div v-else class="text-center py-16">
        <div class="text-6xl mb-4">📭</div>
        <p class="text-xl text-text-secondary">No blocks in this page yet</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue"
import { useRoute } from "vue-router"
import { pageService, type PageWithBlocks } from "../services/codex"

const route = useRoute()

const page = ref<PageWithBlocks | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)

// Get route parameters
const notebookId = ref<number>(parseInt(route.params.notebookId as string))
const workspaceId = ref<number>(parseInt(route.query.workspace_id as string))
// Handle pagePath which might be an array due to the + route pattern
const pagePath = ref<string>(
  Array.isArray(route.params.pagePath) 
    ? route.params.pagePath.join("/")
    : route.params.pagePath as string
)

// Helper functions
const formatDate = (dateStr: string) => {
  try {
    const date = new Date(dateStr)
    return date.toLocaleDateString(undefined, {
      year: "numeric",
      month: "long",
      day: "numeric",
    })
  } catch {
    return dateStr
  }
}

const isImage = (filename: string): boolean => {
  return /\.(jpg|jpeg|png|gif|svg|webp)$/i.test(filename)
}

const isCode = (filename: string): boolean => {
  return /\.(js|ts|jsx|tsx|py|java|cpp|c|h|go|rs|rb|php|css|html|json|xml|yaml|yml)$/i.test(filename)
}

const isData = (filename: string): boolean => {
  return /\.(csv|xlsx|xls|json|xml|sql|db)$/i.test(filename)
}

// Load page data
const loadPage = async () => {
  loading.value = true
  error.value = null

  try {
    page.value = await pageService.get(
      pagePath.value,
      notebookId.value,
      workspaceId.value
    )
  } catch (err: any) {
    console.error("Failed to load page:", err)
    error.value = err.message || "Failed to load page"
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadPage()
})
</script>

<style scoped>
/* Additional styles can be added here if needed */
</style>
