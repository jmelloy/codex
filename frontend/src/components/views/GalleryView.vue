<template>
  <div class="gallery-view p-6">
    <!-- Header -->
    <div class="mb-6">
      <h2 class="text-2xl font-semibold text-text-primary">
        {{ definition?.title }}
      </h2>
      <p v-if="definition?.description" class="text-text-secondary mt-1">
        {{ definition.description }}
      </p>
      <div class="text-sm text-text-tertiary mt-2">
        {{ images.length }} {{ images.length === 1 ? "image" : "images" }}
      </div>
    </div>

    <!-- Gallery Grid -->
    <div
      class="gallery-grid"
      :style="{ gridTemplateColumns: `repeat(${config.columns || 4}, 1fr)` }"
    >
      <div
        v-for="(image, index) in images"
        :key="image.id"
        class="gallery-item group relative cursor-pointer overflow-hidden rounded-lg border border-border-light bg-bg-hover hover:shadow-lg transition"
        @click="openLightbox(index)"
      >
        <!-- Image -->
        <div class="aspect-square flex items-center justify-center overflow-hidden">
          <img
            :src="getImageUrl(image)"
            :alt="image.title || image.filename"
            class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
            loading="lazy"
          />
        </div>

        <!-- Overlay with metadata -->
        <div
          v-if="config.show_metadata !== false"
          class="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/70 to-transparent p-3 text-white opacity-0 group-hover:opacity-100 transition"
        >
          <div class="font-medium text-sm">
            {{ image.title || image.filename }}
          </div>
          <div v-if="image.description" class="text-xs mt-1 opacity-90">
            {{ truncateText(image.description, 50) }}
          </div>
          <div v-if="image.properties?.date" class="text-xs mt-1 opacity-75">
            {{ formatDate(image.properties.date) }}
          </div>
        </div>
      </div>
    </div>

    <!-- Empty State -->
    <div v-if="images.length === 0" class="text-center py-12 text-text-tertiary">
      <div class="text-4xl mb-2">🖼️</div>
      <div class="text-lg">No images found</div>
    </div>

    <!-- Lightbox -->
    <teleport to="body">
      <div
        v-if="lightboxOpen && currentImage"
        class="lightbox fixed inset-0 bg-black/90 z-50 flex items-center justify-center"
        @click="closeLightbox"
      >
        <!-- Close Button -->
        <button
          class="absolute top-4 right-4 text-white text-4xl hover:text-white/80 z-10"
          @click.stop="closeLightbox"
        >
          ×
        </button>

        <!-- Previous Button -->
        <button
          v-if="lightboxIndex > 0"
          class="absolute left-4 text-white text-4xl hover:text-white/80 z-10"
          @click.stop="previousImage"
        >
          ‹
        </button>

        <!-- Next Button -->
        <button
          v-if="lightboxIndex < images.length - 1"
          class="absolute right-4 text-white text-4xl hover:text-white/80 z-10"
          @click.stop="nextImage"
        >
          ›
        </button>

        <!-- Image Container -->
        <div
          class="flex flex-col items-center justify-center max-w-[90vw] max-h-[90vh]"
          @click.stop
        >
          <!-- Image -->
          <img
            :src="getImageUrl(currentImage)"
            :alt="currentImage.title || currentImage.filename"
            class="max-w-full max-h-[80vh] object-contain"
          />

          <!-- Metadata Panel -->
          <div v-if="config.show_metadata !== false" class="bg-white rounded-lg p-4 mt-4 max-w-2xl">
            <h3 class="text-lg font-semibold text-text-primary">
              {{ currentImage.title || currentImage.filename }}
            </h3>
            <p v-if="currentImage.description" class="text-text-secondary mt-2">
              {{ currentImage.description }}
            </p>

            <!-- Properties -->
            <div class="grid grid-cols-2 gap-2 mt-3 text-sm">
              <div v-if="currentImage.properties?.date">
                <span class="font-medium text-text-primary">Date:</span>
                {{ formatDate(currentImage.properties.date) }}
              </div>
              <div v-if="currentImage.properties?.location">
                <span class="font-medium text-text-primary">Location:</span>
                {{ currentImage.properties.location }}
              </div>
              <div v-if="currentImage.properties?.camera">
                <span class="font-medium text-text-primary">Camera:</span>
                {{ currentImage.properties.camera }}
              </div>
              <div v-if="currentImage.size">
                <span class="font-medium text-text-primary">Size:</span>
                {{ formatFileSize(currentImage.size) }}
              </div>
            </div>

            <!-- Tags -->
            <div v-if="currentImage.properties?.tags" class="flex flex-wrap gap-2 mt-3">
              <span
                v-for="tag in currentImage.properties.tags"
                :key="tag"
                class="px-2 py-1 text-xs bg-blue-100 text-blue-700 rounded"
              >
                {{ tag }}
              </span>
            </div>
          </div>
        </div>

        <!-- Image Counter -->
        <div class="absolute bottom-4 left-1/2 -translate-x-1/2 text-white text-sm">
          {{ lightboxIndex + 1 }} / {{ images.length }}
        </div>
      </div>
    </teleport>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted } from "vue"
import type { GalleryConfig, ViewDefinition } from "@/services/viewParser"
import type { QueryResult } from "@/services/queryService"
import type { FileMetadata } from "@/services/codex"

const props = defineProps<{
  data: QueryResult | null
  config: GalleryConfig
  definition?: ViewDefinition
  workspaceId: number
}>()

const lightboxOpen = ref(false)
const lightboxIndex = ref(0)

// Get all image files
const images = computed(() => {
  if (!props.data?.files) return []
  // Filter for image files only
  return props.data.files.filter(
    (file) => file.file_type === "image" || file.path.match(/\.(jpg|jpeg|png|gif|bmp|webp|svg)$/i)
  )
})

const currentImage = computed(() => {
  if (!lightboxOpen.value || !images.value[lightboxIndex.value]) return null
  return images.value[lightboxIndex.value]
})

// Get image URL
const getImageUrl = (image: FileMetadata): string => {
  return `/api/v1/files/${image.id}/content?workspace_id=${props.workspaceId}&notebook_id=${image.notebook_id}`
}

// Lightbox controls
const openLightbox = (index: number) => {
  lightboxIndex.value = index
  lightboxOpen.value = true
}

const closeLightbox = () => {
  lightboxOpen.value = false
}

const nextImage = () => {
  if (lightboxIndex.value < images.value.length - 1) {
    lightboxIndex.value++
  }
}

const previousImage = () => {
  if (lightboxIndex.value > 0) {
    lightboxIndex.value--
  }
}

// Keyboard navigation
const handleKeyPress = (event: KeyboardEvent) => {
  if (!lightboxOpen.value) return

  switch (event.key) {
    case "ArrowLeft":
      previousImage()
      break
    case "ArrowRight":
      nextImage()
      break
    case "Escape":
      closeLightbox()
      break
  }
}

onMounted(() => {
  window.addEventListener("keydown", handleKeyPress)
})

onUnmounted(() => {
  window.removeEventListener("keydown", handleKeyPress)
})

// Helpers
const truncateText = (text: string, maxLength: number): string => {
  if (text.length <= maxLength) return text
  return text.substring(0, maxLength) + "..."
}

const formatDate = (dateStr: string): string => {
  const date = new Date(dateStr)
  return date.toLocaleDateString("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
  })
}

const formatFileSize = (bytes: number): string => {
  const units = ["B", "KB", "MB", "GB"]
  let size = bytes
  let unitIndex = 0

  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024
    unitIndex++
  }

  return `${size.toFixed(1)} ${units[unitIndex]}`
}
</script>

<style scoped>
.gallery-grid {
  display: grid;
  gap: 1rem;
}

.gallery-item {
  transition: all 0.3s;
}

.lightbox {
  animation: fadeIn 0.2s;
}

@keyframes fadeIn {
  from {
    opacity: 0;
  }

  to {
    opacity: 1;
  }
}
</style>
