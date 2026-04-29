<template>
  <div
    class="relative group rounded-lg overflow-hidden bg-gray-800 cursor-pointer"
    @click.stop="handleClick"
  >
    <!-- Checkbox -->
    <div class="absolute top-2 left-2 z-10" @click.stop>
      <input
        type="checkbox"
        :checked="selected"
        @change="$emit('toggle-select')"
        class="w-4 h-4 rounded accent-purple-500"
      />
    </div>

    <!-- Thumbnail -->
    <div class="aspect-square overflow-hidden bg-gray-700">
      <img
        :src="`/api/images/${image.id}/thumbnail`"
        :alt="image.filename"
        class="w-full h-full object-cover transition-transform duration-200 group-hover:scale-105"
        loading="lazy"
        @error="onImgError"
      />
    </div>

    <!-- Hover overlay with quick actions -->
    <div class="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-end">
      <div class="w-full p-2 flex justify-between items-center" @click.stop>
        <div class="flex gap-1">
          <button
            @click="$emit('rate', 1)"
            :class="['text-xl transition-transform hover:scale-125', image.rating === 1 ? 'opacity-100' : 'opacity-70']"
            title="Thumbs up"
          >👍</button>
          <button
            @click="$emit('rate', -1)"
            :class="['text-xl transition-transform hover:scale-125', image.rating === -1 ? 'opacity-100' : 'opacity-70']"
            title="Thumbs down (hide)"
          >👎</button>
        </div>
        <div class="flex gap-0.5">
          <button
            v-for="star in 5"
            :key="star"
            @click="$emit('rate', star + 1)"
            class="text-sm leading-none"
            :class="image.rating >= star + 1 ? 'text-yellow-400' : 'text-gray-500'"
          >★</button>
        </div>
      </div>
    </div>

    <!-- Bottom info -->
    <div class="p-2">
      <p class="text-xs text-gray-400 truncate" :title="image.filename">{{ image.filename }}</p>
      <div class="flex items-center justify-between mt-1">
        <!-- Rating indicator -->
        <span class="text-sm">
          <span v-if="image.rating === 1">👍</span>
          <span v-else-if="image.rating === -1">👎</span>
          <span v-else-if="image.rating >= 2" class="text-yellow-400 text-xs">
            {{ '★'.repeat(image.rating - 1) }}
          </span>
        </span>
        <!-- Tags count -->
        <span v-if="image.tags?.length" class="text-xs text-purple-400">
          {{ image.tags.length }} tag{{ image.tags.length !== 1 ? 's' : '' }}
        </span>
      </div>
      <!-- Tags preview -->
      <div v-if="image.tags?.length" class="flex flex-wrap gap-0.5 mt-1">
        <span
          v-for="tag in image.tags.slice(0, 3)"
          :key="tag.id"
          class="bg-gray-700 text-gray-300 text-xs px-1 py-0.5 rounded"
        >{{ tag.name }}</span>
        <span v-if="image.tags.length > 3" class="text-xs text-gray-500">+{{ image.tags.length - 3 }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'

const props = defineProps({
  image: { type: Object, required: true },
  selected: { type: Boolean, default: false },
})

const emit = defineEmits(['toggle-select', 'rate'])
const router = useRouter()

function handleClick() {
  router.push(`/image/${props.image.id}`)
}

function onImgError(e) {
  e.target.src = `data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='100' height='100'%3E%3Crect width='100' height='100' fill='%23374151'/%3E%3Ctext x='50%25' y='50%25' text-anchor='middle' dy='.3em' fill='%236b7280' font-size='12'%3E No Image%3C/text%3E%3C/svg%3E`
}
</script>
