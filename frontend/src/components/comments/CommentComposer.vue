<template>
  <div class="comment-composer">
    <div class="composer-input-wrapper">
      <textarea
        ref="textareaRef"
        v-model="body"
        class="composer-input"
        :placeholder="placeholder"
        rows="2"
        @input="onInput"
        @keydown="onKeydown"
        @click="onCaretMove"
        @keyup="onCaretMove"
      ></textarea>
      <MentionAutocomplete
        v-if="mentionQuery"
        ref="autocompleteRef"
        :principals="filteredPrincipals"
        @select="selectMention"
      />
    </div>
    <div class="composer-actions">
      <button v-if="showCancel" type="button" class="composer-btn-secondary" @click="cancel">Cancel</button>
      <button type="button" class="composer-btn-primary" :disabled="!body.trim()" @click="submit">
        {{ submitLabel }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick } from "vue"
import { findActiveMentionQuery, insertMention, type MentionQuery } from "../../utils/mentions"
import type { Principal } from "../../services/comments"
import MentionAutocomplete from "./MentionAutocomplete.vue"

const props = withDefaults(
  defineProps<{
    principals: Principal[]
    placeholder?: string
    submitLabel?: string
    showCancel?: boolean
    initialBody?: string
  }>(),
  {
    placeholder: "Write a comment...",
    submitLabel: "Comment",
    showCancel: false,
    initialBody: "",
  },
)

const emit = defineEmits<{
  submit: [body: string]
  cancel: []
}>()

const body = ref(props.initialBody)
const textareaRef = ref<HTMLTextAreaElement | null>(null)
const autocompleteRef = ref<InstanceType<typeof MentionAutocomplete> | null>(null)
const mentionQuery = ref<MentionQuery | null>(null)

const filteredPrincipals = computed(() => {
  const query = mentionQuery.value?.query.toLowerCase() ?? ""
  return props.principals.filter((p) => p.username.toLowerCase().startsWith(query)).slice(0, 8)
})

function onCaretMove() {
  const ta = textareaRef.value
  if (!ta) return
  mentionQuery.value = findActiveMentionQuery(body.value, ta.selectionStart)
}

function onInput() {
  onCaretMove()
}

function onKeydown(event: KeyboardEvent) {
  if (mentionQuery.value && filteredPrincipals.value.length > 0) {
    if (event.key === "ArrowDown") {
      event.preventDefault()
      autocompleteRef.value?.move(1)
      return
    }
    if (event.key === "ArrowUp") {
      event.preventDefault()
      autocompleteRef.value?.move(-1)
      return
    }
    if (event.key === "Enter" || event.key === "Tab") {
      event.preventDefault()
      autocompleteRef.value?.confirmActive()
      return
    }
  }
  if (event.key === "Escape" && mentionQuery.value) {
    mentionQuery.value = null
    return
  }
  if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) {
    event.preventDefault()
    submit()
  }
}

function selectMention(principal: Principal) {
  if (!mentionQuery.value) return
  const result = insertMention(body.value, mentionQuery.value, principal.username)
  body.value = result.text
  mentionQuery.value = null
  nextTick(() => {
    const ta = textareaRef.value
    if (!ta) return
    ta.focus()
    ta.selectionStart = ta.selectionEnd = result.cursor
  })
}

function submit() {
  const trimmed = body.value.trim()
  if (!trimmed) return
  emit("submit", trimmed)
  body.value = ""
  mentionQuery.value = null
}

function cancel() {
  body.value = props.initialBody
  mentionQuery.value = null
  emit("cancel")
}

function focus() {
  textareaRef.value?.focus()
}

defineExpose({ focus })
</script>

<style scoped>
.comment-composer {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.composer-input-wrapper {
  position: relative;
}

.composer-input {
  width: 100%;
  padding: 8px 10px;
  border: 1px solid var(--color-border-light, #e0e0e0);
  border-radius: 6px;
  background: var(--color-bg-primary, #fff);
  color: var(--color-text-primary, #333);
  font-family: inherit;
  font-size: 0.875rem;
  line-height: 1.5;
  resize: vertical;
  min-height: 2.5em;
}

.composer-input:focus {
  outline: none;
  border-color: var(--notebook-accent, #2563eb);
  box-shadow: 0 0 0 1px var(--notebook-accent, #2563eb);
}

.composer-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.composer-btn-primary,
.composer-btn-secondary {
  padding: 5px 12px;
  border-radius: 6px;
  font-size: 0.8125rem;
  font-weight: 500;
  cursor: pointer;
  border: none;
}

.composer-btn-primary {
  background: var(--notebook-accent, #2563eb);
  color: white;
}

.composer-btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.composer-btn-primary:not(:disabled):hover {
  background: color-mix(in srgb, var(--notebook-accent, #2563eb) 85%, black);
}

.composer-btn-secondary {
  background: transparent;
  color: var(--color-text-secondary, #666);
  border: 1px solid var(--color-border-light, #e0e0e0);
}

.composer-btn-secondary:hover {
  background: var(--color-bg-hover, #f5f5f5);
}
</style>
