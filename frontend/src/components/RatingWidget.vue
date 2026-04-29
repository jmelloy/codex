<template>
  <div class="flex flex-col gap-2">
    <!-- Thumbs -->
    <div class="flex gap-3 items-center">
      <button
        @click="setRating(1)"
        :class="[
          'text-2xl transition-all hover:scale-125',
          size === 'lg' ? 'text-3xl' : '',
          currentRating === 1 ? 'opacity-100 drop-shadow-lg' : 'opacity-50 hover:opacity-80',
        ]"
        title="Thumbs up"
      >👍</button>
      <button
        @click="setRating(-1)"
        :class="[
          'text-2xl transition-all hover:scale-125',
          size === 'lg' ? 'text-3xl' : '',
          currentRating === -1 ? 'opacity-100 drop-shadow-lg' : 'opacity-50 hover:opacity-80',
        ]"
        title="Thumbs down (hide)"
      >👎</button>
      <button
        v-if="currentRating !== 0"
        @click="setRating(0)"
        class="text-xs text-gray-500 hover:text-gray-300 ml-2"
        title="Clear rating"
      >✕</button>
    </div>

    <!-- Stars (2-6 mapped to 1-5 display) -->
    <div class="flex gap-0.5">
      <button
        v-for="star in 5"
        :key="star"
        @click="setRating(star + 1)"
        :class="[
          'transition-all hover:scale-125',
          size === 'lg' ? 'text-2xl' : 'text-lg',
          currentRating >= star + 1 ? 'text-yellow-400' : 'text-gray-600 hover:text-yellow-300',
        ]"
      >★</button>
    </div>

    <!-- Label -->
    <p v-if="size === 'lg'" class="text-sm text-gray-400">
      <span v-if="currentRating === -1" class="text-red-400">Hidden (thumbs down)</span>
      <span v-else-if="currentRating === 0" class="text-gray-500">Unrated</span>
      <span v-else-if="currentRating === 1" class="text-green-400">Thumbs up</span>
      <span v-else class="text-yellow-400">{{ currentRating - 1 }} Star{{ currentRating - 1 !== 1 ? 's' : '' }}</span>
    </p>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  imageId: { type: Number, required: true },
  rating: { type: Number, default: 0 },
  size: { type: String, default: 'sm' }, // 'sm' | 'lg'
})

const emit = defineEmits(['rate'])
const currentRating = ref(props.rating)

watch(
  () => props.rating,
  (v) => { currentRating.value = v }
)

function setRating(r) {
  // Toggle off if same rating
  const newRating = currentRating.value === r ? 0 : r
  currentRating.value = newRating
  emit('rate', newRating)
}
</script>
