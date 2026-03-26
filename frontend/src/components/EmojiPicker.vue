<template>
  <div class="emoji-picker" ref="pickerRef">
    <div class="emoji-picker-header">
      <input
        v-model="search"
        class="emoji-search"
        placeholder="Search emoji..."
        @input="filterEmojis"
      />
    </div>
    <div class="emoji-categories">
      <button
        v-for="cat in categories"
        :key="cat.name"
        class="category-btn"
        :class="{ active: activeCategory === cat.name }"
        @click="activeCategory = cat.name"
        :title="cat.name"
      >
        {{ cat.icon }}
      </button>
    </div>
    <div class="emoji-grid">
      <button
        v-for="emoji in displayedEmojis"
        :key="emoji"
        class="emoji-btn"
        @click="$emit('select', emoji)"
        :title="emoji"
      >
        {{ emoji }}
      </button>
      <div v-if="displayedEmojis.length === 0" class="emoji-empty">
        No matching emoji
      </div>
    </div>
    <div class="emoji-picker-footer">
      <button class="emoji-remove-btn" @click="$emit('select', '')">
        Remove icon
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from "vue"

defineEmits<{
  select: [emoji: string]
}>()

const pickerRef = ref<HTMLElement | null>(null)
const search = ref("")
const activeCategory = ref("Smileys")

const categories = [
  {
    name: "Smileys",
    icon: "😀",
    emojis: [
      "😀", "😃", "😄", "😁", "😆", "😅", "🤣", "😂", "🙂", "🙃",
      "😉", "😊", "😇", "🥰", "😍", "🤩", "😘", "😗", "😚", "😙",
      "🥲", "😋", "😛", "😜", "🤪", "😝", "🤑", "🤗", "🤭", "🤫",
      "🤔", "🫡", "🤐", "🤨", "😐", "😑", "😶", "😏", "😒", "🙄",
      "😬", "🤥", "😌", "😔", "😪", "🤤", "😴", "😷", "🤒", "🤕",
      "🤢", "🤮", "🥵", "🥶", "🥴", "😵", "🤯", "🤠", "🥳", "🥸",
      "😎", "🤓", "🧐", "😕", "🫤", "😟", "🙁", "😮", "😯", "😲",
      "😳", "🥺", "🥹", "😦", "😧", "😨", "😰", "😥", "😢", "😭",
    ],
  },
  {
    name: "People",
    icon: "👋",
    emojis: [
      "👋", "🤚", "🖐️", "✋", "🖖", "🫱", "🫲", "🫳", "🫴", "👌",
      "🤌", "🤏", "✌️", "🤞", "🫰", "🤟", "🤘", "🤙", "👈", "👉",
      "👆", "🖕", "👇", "☝️", "🫵", "👍", "👎", "✊", "👊", "🤛",
      "🤜", "👏", "🙌", "🫶", "👐", "🤲", "🤝", "🙏", "✍️", "💅",
      "🤳", "💪", "🦾", "🦿", "🦵", "🦶", "👂", "🦻", "👃", "🧠",
      "👀", "👁️", "👅", "👄", "🫦", "👶", "🧒", "👦", "👧", "🧑",
    ],
  },
  {
    name: "Nature",
    icon: "🌿",
    emojis: [
      "🐶", "🐱", "🐭", "🐹", "🐰", "🦊", "🐻", "🐼", "🐻‍❄️", "🐨",
      "🐯", "🦁", "🐮", "🐷", "🐸", "🐵", "🙈", "🙉", "🙊", "🐒",
      "🐔", "🐧", "🐦", "🐤", "🦆", "🦅", "🦉", "🦇", "🐺", "🐗",
      "🐴", "🦄", "🐝", "🪱", "🐛", "🦋", "🐌", "🐞", "🐜", "🪰",
      "🌸", "💮", "🏵️", "🌹", "🥀", "🌺", "🌻", "🌼", "🌷", "🌱",
      "🪴", "🌲", "🌳", "🌴", "🌵", "🌾", "🌿", "☘️", "🍀", "🍁",
    ],
  },
  {
    name: "Food",
    icon: "🍕",
    emojis: [
      "🍇", "🍈", "🍉", "🍊", "🍋", "🍌", "🍍", "🥭", "🍎", "🍏",
      "🍐", "🍑", "🍒", "🍓", "🫐", "🥝", "🍅", "🫒", "🥥", "🥑",
      "🍆", "🥔", "🥕", "🌽", "🌶️", "🫑", "🥒", "🥬", "🥦", "🧄",
      "🍞", "🥐", "🥖", "🫓", "🥨", "🥯", "🥞", "🧇", "🧀", "🍖",
      "🍗", "🥩", "🥓", "🍔", "🍟", "🍕", "🌭", "🥪", "🌮", "🌯",
      "🫔", "🥙", "🧆", "🥚", "🍳", "🥘", "🍲", "🫕", "🥣", "🥗",
    ],
  },
  {
    name: "Objects",
    icon: "💡",
    emojis: [
      "⌚", "📱", "💻", "⌨️", "🖥️", "🖨️", "🖱️", "🖲️", "💽", "💾",
      "💿", "📀", "🧮", "🎬", "📷", "📹", "🔍", "🔬", "🔭", "📡",
      "🕯️", "💡", "🔦", "🏮", "📔", "📕", "📖", "📗", "📘", "📙",
      "📚", "📓", "📒", "📃", "📜", "📄", "📰", "🗞️", "📑", "🔖",
      "🏷️", "✉️", "📧", "📨", "📩", "📤", "📥", "📦", "📫", "📪",
      "✏️", "✒️", "🖊️", "🖋️", "📝", "📁", "📂", "🗂️", "📅", "📆",
    ],
  },
  {
    name: "Symbols",
    icon: "⭐",
    emojis: [
      "❤️", "🧡", "💛", "💚", "💙", "💜", "🖤", "🤍", "🤎", "💔",
      "❤️‍🔥", "💕", "💞", "💓", "💗", "💖", "💘", "💝", "⭐", "🌟",
      "💫", "✨", "⚡", "🔥", "💥", "🎯", "🏆", "🥇", "🥈", "🥉",
      "⚽", "🏀", "🏈", "⚾", "🎾", "🏐", "🎮", "🎲", "🎭", "🎨",
      "🎵", "🎶", "🎤", "🎧", "🎸", "🎹", "🥁", "🎺", "🎷", "🪗",
      "✅", "❌", "⭕", "❓", "❗", "💯", "🔴", "🟠", "🟡", "🟢",
      "🔵", "🟣", "⚫", "⚪", "🟤", "🔶", "🔷", "🔸", "🔹", "🔺",
    ],
  },
  {
    name: "Travel",
    icon: "🏠",
    emojis: [
      "🏠", "🏡", "🏢", "🏣", "🏤", "🏥", "🏦", "🏨", "🏩", "🏪",
      "🏫", "🏬", "🏭", "🏯", "🏰", "💒", "🗼", "🗽", "⛪", "🕌",
      "🛕", "🕍", "⛩️", "🕋", "⛲", "⛺", "🌁", "🌃", "🏙️", "🌄",
      "🌅", "🌆", "🌇", "🌉", "🎠", "🛝", "🎡", "🎢", "🚂", "🚃",
      "🚗", "🚕", "🚙", "🚌", "🚎", "🏎️", "🚓", "🚑", "🚒", "🚐",
      "✈️", "🚀", "🛸", "🚁", "🛶", "⛵", "🚤", "🛥️", "🛳️", "⛴️",
    ],
  },
  {
    name: "Flags",
    icon: "🚩",
    emojis: [
      "🏁", "🚩", "🎌", "🏴", "🏳️", "🏳️‍🌈", "🏳️‍⚧️", "🏴‍☠️",
      "🇺🇸", "🇬🇧", "🇫🇷", "🇩🇪", "🇮🇹", "🇪🇸", "🇯🇵", "🇰🇷",
      "🇨🇳", "🇮🇳", "🇧🇷", "🇲🇽", "🇨🇦", "🇦🇺", "🇷🇺", "🇿🇦",
    ],
  },
]

const filteredEmojis = ref<string[]>([])

const displayedEmojis = computed(() => {
  if (search.value.trim()) {
    return filteredEmojis.value
  }
  const cat = categories.find((c) => c.name === activeCategory.value)
  return cat?.emojis || []
})

function filterEmojis() {
  if (!search.value.trim()) {
    filteredEmojis.value = []
    return
  }
  // Simple filter: show all emojis from all categories
  // In a real app you'd search by name, but emoji names aren't embedded here
  // Instead, show all emojis when searching (user scrolls to find)
  filteredEmojis.value = categories.flatMap((c) => c.emojis)
}

// Close on click outside
function handleClickOutside(event: MouseEvent) {
  if (pickerRef.value && !pickerRef.value.contains(event.target as Node)) {
    // Let the parent handle closing
  }
}

onMounted(() => {
  document.addEventListener("mousedown", handleClickOutside)
})

onBeforeUnmount(() => {
  document.removeEventListener("mousedown", handleClickOutside)
})
</script>

<style scoped>
.emoji-picker {
  width: 320px;
  max-height: 380px;
  background: var(--color-bg-primary, #fff);
  border: 1px solid var(--color-border-light, #e0e0e0);
  border-radius: var(--radius-md, 8px);
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.12);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  z-index: 100;
}

.emoji-picker-header {
  padding: 8px;
  border-bottom: 1px solid var(--color-border-light, #e0e0e0);
}

.emoji-search {
  width: 100%;
  padding: 6px 10px;
  border: 1px solid var(--color-border-light, #e0e0e0);
  border-radius: var(--radius-sm, 4px);
  font-size: 13px;
  background: var(--color-bg-secondary, #f5f5f5);
  color: var(--color-text-primary, #333);
  outline: none;
  box-sizing: border-box;
}

.emoji-search:focus {
  border-color: var(--color-primary, #2563eb);
}

.emoji-categories {
  display: flex;
  gap: 2px;
  padding: 4px 8px;
  border-bottom: 1px solid var(--color-border-light, #e0e0e0);
  overflow-x: auto;
}

.category-btn {
  background: none;
  border: none;
  padding: 4px 6px;
  border-radius: var(--radius-sm, 4px);
  cursor: pointer;
  font-size: 16px;
  line-height: 1;
  opacity: 0.6;
  transition: all 0.15s;
}

.category-btn:hover {
  opacity: 1;
  background: var(--color-bg-hover, #f0f0f0);
}

.category-btn.active {
  opacity: 1;
  background: var(--color-bg-active, #e8e8e8);
}

.emoji-grid {
  display: grid;
  grid-template-columns: repeat(8, 1fr);
  gap: 2px;
  padding: 8px;
  overflow-y: auto;
  flex: 1;
  min-height: 0;
}

.emoji-btn {
  background: none;
  border: none;
  padding: 4px;
  border-radius: var(--radius-sm, 4px);
  cursor: pointer;
  font-size: 20px;
  line-height: 1;
  text-align: center;
  transition: background 0.15s;
}

.emoji-btn:hover {
  background: var(--color-bg-hover, #f0f0f0);
}

.emoji-empty {
  grid-column: 1 / -1;
  text-align: center;
  padding: 16px;
  color: var(--color-text-tertiary, #999);
  font-size: 13px;
}

.emoji-picker-footer {
  padding: 6px 8px;
  border-top: 1px solid var(--color-border-light, #e0e0e0);
}

.emoji-remove-btn {
  width: 100%;
  padding: 6px;
  background: none;
  border: 1px solid var(--color-border-light, #e0e0e0);
  border-radius: var(--radius-sm, 4px);
  color: var(--color-text-secondary, #666);
  font-size: 12px;
  cursor: pointer;
  transition: all 0.15s;
}

.emoji-remove-btn:hover {
  background: var(--color-bg-hover, #f0f0f0);
  color: var(--color-error, #ef4444);
  border-color: var(--color-error, #ef4444);
}
</style>
