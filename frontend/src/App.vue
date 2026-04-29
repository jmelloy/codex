<template>
  <div class="min-h-screen bg-gray-900">
    <!-- Top Navigation -->
    <nav class="bg-gray-800 border-b border-gray-700 px-4 py-3 flex items-center gap-4 sticky top-0 z-50">
      <router-link to="/" class="text-xl font-bold text-purple-400 whitespace-nowrap">
        🎨 Diffusion Viewer
      </router-link>
      <div class="flex-1">
        <SearchBar />
      </div>
      <button
        @click="showScanModal = true"
        class="bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors whitespace-nowrap"
      >
        📂 Scan Directory
      </button>
    </nav>

    <!-- Scan Modal -->
    <div
      v-if="showScanModal"
      class="fixed inset-0 bg-black/70 flex items-center justify-center z-50"
      @click.self="showScanModal = false"
    >
      <div class="bg-gray-800 rounded-xl p-6 w-full max-w-md shadow-2xl">
        <h2 class="text-lg font-bold mb-4 text-white">Scan Image Directory</h2>
        <input
          v-model="scanDirectory"
          type="text"
          placeholder="/path/to/your/images"
          class="w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-3 py-2 mb-3 focus:outline-none focus:ring-2 focus:ring-purple-500"
          @keyup.enter="doScan"
        />
        <div v-if="scanResult" class="text-sm mb-3" :class="scanError ? 'text-red-400' : 'text-green-400'">
          {{ scanResult }}
        </div>
        <div class="flex gap-2 justify-end">
          <button
            @click="showScanModal = false"
            class="px-4 py-2 rounded-lg bg-gray-600 hover:bg-gray-500 text-sm transition-colors"
          >
            Close
          </button>
          <button
            @click="doScan"
            :disabled="scanning"
            class="px-4 py-2 rounded-lg bg-purple-600 hover:bg-purple-700 text-sm font-medium disabled:opacity-50 transition-colors"
          >
            {{ scanning ? 'Scanning…' : 'Scan' }}
          </button>
        </div>
      </div>
    </div>

    <router-view />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import SearchBar from './components/SearchBar.vue'
import { useImagesStore } from './stores/images.js'

const store = useImagesStore()
const showScanModal = ref(false)
const scanDirectory = ref('')
const scanning = ref(false)
const scanResult = ref('')
const scanError = ref(false)

async function doScan() {
  if (!scanDirectory.value.trim()) return
  scanning.value = true
  scanResult.value = ''
  scanError.value = false
  try {
    const result = await store.scanDirectory(scanDirectory.value.trim())
    scanResult.value = `✅ Scanned: ${result.scanned}, Added: ${result.added}, Updated: ${result.updated}`
  } catch (e) {
    scanError.value = true
    scanResult.value = '❌ ' + (e.response?.data?.detail || e.message)
  } finally {
    scanning.value = false
  }
}
</script>
