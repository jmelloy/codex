<template>
  <div>
    <!-- Current tags -->
    <div class="flex flex-wrap gap-1 mb-3">
      <span
        v-for="tag in localTags"
        :key="tag.id || tag.name"
        class="flex items-center gap-1 bg-purple-800 text-purple-100 px-2 py-0.5 rounded-full text-xs"
      >
        {{ tag.name }}
        <button @click="removeTag(tag.name)" class="hover:text-red-300 transition-colors ml-0.5">×</button>
      </span>
      <span v-if="!localTags.length" class="text-xs text-gray-500">No tags</span>
    </div>

    <!-- Add tag input -->
    <div class="relative">
      <input
        v-model="newTagInput"
        type="text"
        placeholder="Add tag…"
        class="w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
        @keyup.enter="addTags"
        @input="showSuggestions = true"
        @blur="hideSuggestions"
      />
      <!-- Suggestions dropdown -->
      <div
        v-if="showSuggestions && filteredSuggestions.length"
        class="absolute top-full left-0 right-0 bg-gray-700 border border-gray-600 rounded-lg mt-1 z-20 max-h-40 overflow-y-auto shadow-xl"
      >
        <button
          v-for="sug in filteredSuggestions"
          :key="sug.name"
          class="w-full text-left px-3 py-1.5 text-sm hover:bg-gray-600 text-gray-200"
          @mousedown.prevent="selectSuggestion(sug.name)"
        >
          {{ sug.name }}
        </button>
      </div>
    </div>
    <p class="text-xs text-gray-500 mt-1">Press Enter or comma-separate multiple tags</p>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useImagesStore } from '../stores/images.js'

const props = defineProps({
  imageId: { type: Number, required: true },
  tags: { type: Array, default: () => [] },
})

const emit = defineEmits(['updated'])
const store = useImagesStore()
const newTagInput = ref('')
const showSuggestions = ref(false)
const localTags = ref([...props.tags])

watch(
  () => props.tags,
  (v) => { localTags.value = [...v] }
)

const filteredSuggestions = computed(() => {
  const q = newTagInput.value.toLowerCase().trim()
  if (!q) return []
  return store.allTags.filter(
    (t) =>
      t.name.includes(q) &&
      !localTags.value.find((lt) => lt.name === t.name)
  ).slice(0, 10)
})

async function addTags() {
  const raw = newTagInput.value.split(',').map((t) => t.trim()).filter(Boolean)
  if (!raw.length) return
  newTagInput.value = ''
  showSuggestions.value = false
  await store.addTags(props.imageId, raw)
  emit('updated')
}

async function removeTag(tagName) {
  await store.removeTag(props.imageId, tagName)
  localTags.value = localTags.value.filter((t) => t.name !== tagName)
  emit('updated')
}

function selectSuggestion(name) {
  newTagInput.value = name
  showSuggestions.value = false
  addTags()
}

function hideSuggestions() {
  setTimeout(() => { showSuggestions.value = false }, 150)
}
</script>
