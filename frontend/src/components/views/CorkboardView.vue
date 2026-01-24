<template>
  <div class="corkboard-view relative bg-[#d4a76a] min-h-screen p-8" :style="corkboardBg">
    <!-- Header -->
    <div class="mb-6 bg-white/90 backdrop-blur rounded-lg p-4 shadow-md inline-block">
      <h2 class="text-2xl font-semibold text-text-primary">{{ definition?.title }}</h2>
      <p v-if="definition?.description" class="text-text-secondary mt-1">
        {{ definition.description }}
      </p>
    </div>

    <!-- Swimlanes Layout -->
    <div v-if="config.layout === 'swimlanes'" class="space-y-6">
      <div v-for="(group, groupKey) in groupedCards" :key="groupKey" class="swimlane">
        <div class="mb-3 bg-white/80 backdrop-blur rounded px-3 py-2 inline-block shadow">
          <h3 class="font-semibold text-text-primary text-lg">
            {{ formatGroupName(groupKey) }}
          </h3>
          <span class="text-sm text-text-secondary ml-2">{{ group.length }} items</span>
        </div>

        <div class="flex flex-wrap gap-4">
          <div
            v-for="card in group"
            :key="card.id"
            class="notecard"
            :class="cardStyleClass"
            :draggable="config.draggable !== false"
            @dragstart="handleDragStart($event, card)"
            @click="handleCardClick(card)"
          >
            <NoteCard :file="card" :config="config" />
          </div>
        </div>
      </div>
    </div>

    <!-- Freeform Layout -->
    <div
      v-else
      ref="canvas"
      class="freeform-canvas relative min-h-[800px]"
      @dragover.prevent
      @drop="handleDrop"
    >
      <div
        v-for="card in positionedCards"
        :key="card.id"
        class="notecard absolute"
        :class="cardStyleClass"
        :style="{
          left: getCardPosition(card).x + 'px',
          top: getCardPosition(card).y + 'px',
        }"
        :draggable="config.draggable !== false"
        @dragstart="handleDragStart($event, card)"
        @click="handleCardClick(card)"
      >
        <NoteCard :file="card" :config="config" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import type { CorkboardConfig, ViewDefinition } from '@/services/viewParser';
import type { QueryResult } from '@/services/queryService';
import type { FileMetadata } from '@/services/codex';
import NoteCard from './NoteCard.vue';

const props = defineProps<{
  data: QueryResult | null;
  config: CorkboardConfig;
  definition?: ViewDefinition;
  workspaceId: number;
}>();

const emit = defineEmits<{
  (e: 'update', event: { fileId: number; updates: Record<string, any> }): void;
  (e: 'refresh'): void;
}>();

const draggedCard = ref<FileMetadata | null>(null);
const canvas = ref<HTMLElement | null>(null);

// Cork background pattern
const corkboardBg = computed(() => ({
  backgroundImage: `
    radial-gradient(circle at 20% 30%, rgba(139, 90, 43, 0.1) 0%, transparent 50%),
    radial-gradient(circle at 80% 70%, rgba(139, 90, 43, 0.1) 0%, transparent 50%),
    radial-gradient(circle at 40% 80%, rgba(139, 90, 43, 0.1) 0%, transparent 50%)
  `,
}));

// Card style class
const cardStyleClass = computed(() => {
  return props.config.card_style === 'sticky' ? 'sticky-note' : 'note-card';
});

// Get all cards
const allCards = computed(() => props.data?.files || []);

// Grouped cards (for swimlanes layout)
const groupedCards = computed(() => {
  if (props.config.layout !== 'swimlanes' || !props.config.group_by) {
    return { default: allCards.value };
  }

  const groups: Record<string, FileMetadata[]> = {};

  allCards.value.forEach((card) => {
    let groupKey = 'Uncategorized';

    if (props.config.group_by?.startsWith('properties.')) {
      const propKey = props.config.group_by.split('.')[1] ?? '';
      groupKey = card.properties?.[propKey] || 'Uncategorized';
    } else if (props.config.group_by && card.properties?.[props.config.group_by]) {
      groupKey = card.properties[props.config.group_by];
    }

    if (!groups[groupKey]) {
      groups[groupKey] = [];
    }
    groups[groupKey]!.push(card);
  });

  return groups;
});

// Positioned cards (for freeform layout)
const positionedCards = computed(() => allCards.value);

// Get card position (from properties or auto-layout)
const getCardPosition = (card: FileMetadata): { x: number; y: number } => {
  // Check if card has saved position
  if (card.properties?.corkboard_position) {
    return card.properties.corkboard_position;
  }

  // Auto-layout: distribute cards in a grid
  const index = positionedCards.value.indexOf(card);
  const cols = 4;
  const col = index % cols;
  const row = Math.floor(index / cols);

  return {
    x: col * 300 + 20,
    y: row * 250 + 20,
  };
};

// Format group name
const formatGroupName = (groupKey: string): string => {
  // Capitalize first letter and replace underscores with spaces
  return groupKey
    .toString()
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (l) => l.toUpperCase());
};

// Drag and drop handlers
const handleDragStart = (event: DragEvent, card: FileMetadata) => {
  draggedCard.value = card;
  if (event.dataTransfer) {
    event.dataTransfer.effectAllowed = 'move';
    event.dataTransfer.setData('text/plain', String(card.id));
  }
};

const handleDrop = (event: DragEvent) => {
  event.preventDefault();

  if (!draggedCard.value || props.config.layout !== 'freeform') return;

  // Calculate drop position relative to canvas
  const canvasRect = canvas.value?.getBoundingClientRect();
  if (!canvasRect) return;

  const x = event.clientX - canvasRect.left;
  const y = event.clientY - canvasRect.top;

  // Update card position
  emit('update', {
    fileId: draggedCard.value.id,
    updates: {
      corkboard_position: { x, y },
    },
  });

  draggedCard.value = null;
};

// Handle card click
const handleCardClick = (card: FileMetadata) => {
  if (props.config.editable !== false) {
    console.log('Card clicked:', card);
    // TODO: Open edit modal or navigate to file
  }
};
</script>

<style scoped>
.corkboard-view {
  background-color: #d4a76a;
}

.notecard {
  transition: all 0.2s;
}

.notecard:hover {
  transform: rotate(0deg) !important;
  z-index: 10;
}

.note-card {
  width: 250px;
  background: linear-gradient(135deg, #fff9e6 0%, #fff4d6 100%);
  box-shadow: 2px 4px 8px rgba(0, 0, 0, 0.15), 0 0 0 1px rgba(0, 0, 0, 0.05);
  border-radius: 2px;
  transform: rotate(-1deg);
  cursor: pointer;
}

.note-card:nth-child(even) {
  transform: rotate(1deg);
}

.note-card:nth-child(3n) {
  transform: rotate(-0.5deg);
}

.sticky-note {
  width: 200px;
  background: linear-gradient(135deg, #fff740 0%, #ffd900 100%);
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  border-radius: 0 0 2px 2px;
  transform: rotate(-2deg);
  cursor: pointer;
  position: relative;
}

.sticky-note::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 30px;
  background: rgba(0, 0, 0, 0.05);
  border-radius: 2px 2px 0 0;
}

.sticky-note:nth-child(even) {
  background: linear-gradient(135deg, #ff7eb9 0%, #ff65a3 100%);
  transform: rotate(2deg);
}

.sticky-note:nth-child(3n) {
  background: linear-gradient(135deg, #7afcff 0%, #4dd5ff 100%);
  transform: rotate(-1deg);
}

.swimlane {
  padding: 1rem;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 8px;
}
</style>
