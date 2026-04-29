<template>
  <div class="flex items-center gap-2 flex-1">
    <div class="relative flex-1">
      <input
        v-model="store.searchQuery"
        type="text"
        placeholder="Search images, prompts, descriptions…"
        class="w-full bg-gray-700 border border-gray-600 text-white rounded-lg pl-9 pr-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
        @keyup.enter="search"
      />
      <span class="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 text-sm">🔍</span>
    </div>
    <button
      v-if="store.searchQuery || store.selectedTags.length || store.dateFrom || store.dateTo"
      @click="clearFilters"
      class="text-xs text-gray-400 hover:text-white bg-gray-700 hover:bg-gray-600 px-2 py-1.5 rounded-lg transition-colors whitespace-nowrap"
    >
      Clear ✕
    </button>
    <button
      @click="search"
      class="bg-purple-600 hover:bg-purple-700 text-white px-3 py-1.5 rounded-lg text-sm transition-colors whitespace-nowrap"
    >
      Search
    </button>
  </div>
</template>

<script setup>
import { useImagesStore } from '../stores/images.js'

const store = useImagesStore()

function search() {
  store.fetchImages(true)
}

function clearFilters() {
  store.searchQuery = ''
  store.selectedTags = []
  store.dateFrom = ''
  store.dateTo = ''
  store.fetchImages(true)
}
</script>
