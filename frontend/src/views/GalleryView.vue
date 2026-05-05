<template>
  <div class="flex h-[calc(100vh-57px)]">
    <!-- Sidebar Filters -->
    <aside class="w-64 bg-gray-800 border-r border-gray-700 overflow-y-auto p-4 flex-shrink-0">
      <h2 class="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">Filters</h2>

      <!-- Rating filter -->
      <div class="mb-4">
        <label class="block text-xs text-gray-400 mb-1">Min Rating</label>
        <select
          v-model.number="store.minRating"
          @change="store.fetchImages(true)"
          class="w-full bg-gray-700 border border-gray-600 text-white rounded px-2 py-1 text-sm"
        >
          <option :value="-999">All (including unrated)</option>
          <option :value="0">Unrated &amp; above</option>
          <option :value="1">Thumbs up &amp; above</option>
          <option :value="2">★★+</option>
          <option :value="3">★★★+</option>
          <option :value="4">★★★★+</option>
          <option :value="5">★★★★★</option>
        </select>
      </div>

      <!-- Show hidden toggle -->
      <div class="mb-4 flex items-center gap-2">
        <input
          id="show-hidden"
          type="checkbox"
          v-model="store.showHidden"
          @change="store.fetchImages(true)"
          class="rounded"
        />
        <label for="show-hidden" class="text-sm text-gray-300">Show thumbs-down</label>
      </div>

      <!-- Date range -->
      <div class="mb-4">
        <label class="block text-xs text-gray-400 mb-1">Date From</label>
        <input
          v-model="store.dateFrom"
          type="date"
          @change="store.fetchImages(true)"
          class="w-full bg-gray-700 border border-gray-600 text-white rounded px-2 py-1 text-sm"
        />
      </div>
      <div class="mb-4">
        <label class="block text-xs text-gray-400 mb-1">Date To</label>
        <input
          v-model="store.dateTo"
          type="date"
          @change="store.fetchImages(true)"
          class="w-full bg-gray-700 border border-gray-600 text-white rounded px-2 py-1 text-sm"
        />
      </div>

      <!-- Sort -->
      <div class="mb-4">
        <label class="block text-xs text-gray-400 mb-1">Sort By</label>
        <select
          v-model="store.sortBy"
          @change="store.fetchImages(true)"
          class="w-full bg-gray-700 border border-gray-600 text-white rounded px-2 py-1 text-sm mb-1"
        >
          <option value="date_taken">Date Taken</option>
          <option value="created_at">Date Added</option>
          <option value="rating">Rating</option>
          <option value="filename">Filename</option>
        </select>
        <select
          v-model="store.sortDir"
          @change="store.fetchImages(true)"
          class="w-full bg-gray-700 border border-gray-600 text-white rounded px-2 py-1 text-sm"
        >
          <option value="desc">Newest First</option>
          <option value="asc">Oldest First</option>
        </select>
      </div>

      <!-- Tag filter -->
      <div class="mb-4">
        <label class="block text-xs text-gray-400 mb-1">Filter by Tags</label>
        <div class="flex flex-wrap gap-1 max-h-48 overflow-y-auto">
          <button
            v-for="tag in store.allTags"
            :key="tag.id"
            @click="toggleTagFilter(tag.name)"
            :class="[
              'px-2 py-0.5 rounded text-xs transition-colors',
              store.selectedTags.includes(tag.name)
                ? 'bg-purple-600 text-white'
                : 'bg-gray-700 text-gray-300 hover:bg-gray-600',
            ]"
          >
            {{ tag.name }} ({{ tag.image_count }})
          </button>
        </div>
      </div>

      <!-- Bulk actions -->
      <div v-if="store.selectedImageIds.length" class="mt-4 border-t border-gray-700 pt-4">
        <p class="text-xs text-gray-400 mb-2">{{ store.selectedImageIds.length }} selected</p>
        <div class="flex gap-1 mb-3">
          <button @click="store.selectAll()" class="text-xs bg-gray-700 hover:bg-gray-600 px-2 py-1 rounded">
            All
          </button>
          <button @click="store.clearSelection()" class="text-xs bg-gray-700 hover:bg-gray-600 px-2 py-1 rounded">
            None
          </button>
        </div>

        <!-- Add tags -->
        <input
          v-model="bulkTagInput"
          placeholder="tag1, tag2…"
          class="w-full bg-gray-700 border border-gray-600 text-white rounded px-2 py-1 text-xs mb-1"
          @keyup.enter="doBulkTag"
        />
        <button
          @click="doBulkTag"
          class="w-full bg-purple-600 hover:bg-purple-700 text-white rounded px-2 py-1 text-xs mb-3"
        >
          Bulk Tag
        </button>

        <!-- Remove tag -->
        <div v-if="selectedImagesTags.length" class="mb-3">
          <label class="block text-xs text-gray-400 mb-1">Remove Tag</label>
          <select
            v-model="bulkRemoveTagInput"
            class="w-full bg-gray-700 border border-gray-600 text-white rounded px-2 py-1 text-xs mb-1"
          >
            <option value="">— pick a tag —</option>
            <option v-for="tag in selectedImagesTags" :key="tag" :value="tag">{{ tag }}</option>
          </select>
          <button
            @click="doBulkRemoveTag"
            :disabled="!bulkRemoveTagInput"
            class="w-full bg-red-700 hover:bg-red-600 disabled:opacity-40 text-white rounded px-2 py-1 text-xs"
          >
            Remove Tag
          </button>
        </div>

        <!-- Thumbs down -->
        <button
          @click="doBulkThumbsDown"
          class="w-full bg-gray-700 hover:bg-gray-600 text-white rounded px-2 py-1 text-xs"
        >
          👎 Thumbs Down
        </button>
      </div>
    </aside>

    <!-- Gallery -->
    <main class="flex-1 overflow-y-auto p-4" ref="galleryEl">
      <!-- Loading / empty states -->
      <div v-if="store.loading && !store.images.length" class="flex items-center justify-center h-64">
        <div class="text-gray-400 text-lg">Loading…</div>
      </div>
      <div v-else-if="!store.images.length" class="flex flex-col items-center justify-center h-64 gap-4">
        <div class="text-6xl">🖼️</div>
        <p class="text-gray-400 text-lg">No images found.</p>
        <p class="text-gray-500 text-sm">Use "Scan Directory" to add images.</p>
      </div>

      <!-- Date-grouped grid -->
      <template v-else>
        <div v-for="(group, date) in groupedImages" :key="date" class="mb-8">
          <h3 class="text-sm font-semibold text-gray-400 mb-3 uppercase tracking-wider">
            {{ formatDate(date) }}
          </h3>
          <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
            <ImageCard
              v-for="img in group"
              :key="img.id"
              :image="img"
              :selected="store.selectedImageIds.includes(img.id)"
              @toggle-select="store.toggleImageSelection(img.id)"
              @rate="(r) => store.rateImage(img.id, r)"
            />
          </div>
        </div>

        <!-- Load More -->
        <div class="flex justify-center mt-6 pb-8">
          <button
            v-if="store.page < store.pages"
            @click="store.fetchMoreImages()"
            :disabled="store.loading"
            class="bg-gray-700 hover:bg-gray-600 text-white px-6 py-2 rounded-lg disabled:opacity-50 transition-colors"
          >
            {{ store.loading ? 'Loading…' : `Load More (${store.total - store.images.length} remaining)` }}
          </button>
          <p v-else class="text-gray-500 text-sm">All {{ store.total }} images loaded</p>
        </div>
      </template>
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useImagesStore } from '../stores/images.js'
import ImageCard from '../components/ImageCard.vue'

const store = useImagesStore()
const bulkTagInput = ref('')
const bulkRemoveTagInput = ref('')
const galleryEl = ref(null)

onMounted(() => {
  store.fetchImages(true)
  store.fetchAllTags()
})

function toggleTagFilter(tagName) {
  const idx = store.selectedTags.indexOf(tagName)
  if (idx === -1) store.selectedTags.push(tagName)
  else store.selectedTags.splice(idx, 1)
  store.fetchImages(true)
}

async function doBulkTag() {
  const tags = bulkTagInput.value.split(',').map((t) => t.trim()).filter(Boolean)
  if (!tags.length) return
  await store.bulkTag(tags)
  bulkTagInput.value = ''
}

const selectedImagesTags = computed(() => {
  const names = new Set()
  for (const img of store.images) {
    if (store.selectedImageIds.includes(img.id)) {
      for (const tag of img.tags) names.add(tag.name)
    }
  }
  return [...names].sort()
})

async function doBulkRemoveTag() {
  const tag = bulkRemoveTagInput.value
  if (!tag) return
  const n = store.selectedImageIds.length
  if (!confirm(`Remove tag "${tag}" from ${n} selected image${n !== 1 ? 's' : ''}?`)) return
  await store.bulkRemoveTag(tag)
  bulkRemoveTagInput.value = ''
}

async function doBulkThumbsDown() {
  const n = store.selectedImageIds.length
  if (!confirm(`Mark ${n} image${n !== 1 ? 's' : ''} as thumbs-down? They will be hidden.`)) return
  await store.bulkRate(-1)
  store.clearSelection()
}

const groupedImages = computed(() => {
  const groups = {}
  for (const img of store.images) {
    const date = img.date_taken ? img.date_taken.split('T')[0] : 'Unknown Date'
    if (!groups[date]) groups[date] = []
    groups[date].push(img)
  }
  return groups
})

function formatDate(dateStr) {
  if (dateStr === 'Unknown Date') return dateStr
  try {
    return new Date(dateStr + 'T00:00:00').toLocaleDateString(undefined, {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    })
  } catch {
    return dateStr
  }
}
</script>
