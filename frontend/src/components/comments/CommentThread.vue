<template>
  <div class="comment-thread-panel">
    <div class="comment-thread-header">
      <h3 class="comment-thread-title">Comments</h3>
      <button class="comment-thread-close" title="Close" @click="$emit('close')">&#x2715;</button>
    </div>

    <div class="comment-thread-body">
      <div v-if="loading" class="comment-thread-status">Loading comments&hellip;</div>
      <div v-else-if="error" class="comment-thread-status comment-thread-error">{{ error }}</div>
      <div v-else-if="threads.length === 0" class="comment-thread-status">No comments yet</div>

      <div
        v-for="thread in threads"
        :key="thread.root.id"
        class="comment-thread"
        :class="{ resolved: !!thread.root.resolved_at }"
      >
        <div class="comment-item">
          <span class="comment-avatar" aria-hidden="true">{{ initials(thread.root.author_username) }}</span>
          <div class="comment-item-body">
            <div class="comment-item-header">
              <span class="comment-author">{{ thread.root.author_username || "Unknown" }}</span>
              <span class="comment-time">{{ formatTime(thread.root.created_at) }}</span>
            </div>
            <CommentComposer
              v-if="editingId === thread.root.id"
              :principals="principals"
              :initial-body="thread.root.body"
              submit-label="Save"
              show-cancel
              @submit="(body) => saveEdit(thread.root, body)"
              @cancel="editingId = null"
            />
            <p v-else class="comment-body">{{ thread.root.body }}</p>
            <div v-if="editingId !== thread.root.id" class="comment-item-actions">
              <button v-if="canEdit(thread.root)" class="comment-inline-btn" @click="editingId = thread.root.id">
                Edit
              </button>
              <button v-if="canDelete(thread.root)" class="comment-inline-btn" @click="removeComment(thread.root)">
                Delete
              </button>
            </div>
          </div>
        </div>

        <div v-if="thread.root.resolved_at" class="comment-resolved-banner">Resolved</div>

        <div v-if="thread.replies.length > 0" class="comment-replies">
          <div v-for="reply in thread.replies" :key="reply.id" class="comment-item comment-reply">
            <span class="comment-avatar" aria-hidden="true">{{ initials(reply.author_username) }}</span>
            <div class="comment-item-body">
              <div class="comment-item-header">
                <span class="comment-author">{{ reply.author_username || "Unknown" }}</span>
                <span class="comment-time">{{ formatTime(reply.created_at) }}</span>
              </div>
              <CommentComposer
                v-if="editingId === reply.id"
                :principals="principals"
                :initial-body="reply.body"
                submit-label="Save"
                show-cancel
                @submit="(body) => saveEdit(reply, body)"
                @cancel="editingId = null"
              />
              <p v-else class="comment-body">{{ reply.body }}</p>
              <div v-if="editingId !== reply.id" class="comment-item-actions">
                <button v-if="canEdit(reply)" class="comment-inline-btn" @click="editingId = reply.id">Edit</button>
                <button v-if="canDelete(reply)" class="comment-inline-btn" @click="removeComment(reply)">
                  Delete
                </button>
              </div>
            </div>
          </div>
        </div>

        <div v-if="canComment" class="comment-thread-actions">
          <button
            v-if="!thread.root.resolved_at"
            class="comment-resolve-btn"
            @click="resolveThread(thread.root)"
          >
            Resolve
          </button>
          <CommentComposer
            :principals="principals"
            placeholder="Reply..."
            submit-label="Reply"
            show-cancel
            @submit="(body) => postReply(thread.root, body)"
          />
        </div>
      </div>
    </div>

    <div v-if="canComment" class="comment-thread-new">
      <CommentComposer :principals="principals" @submit="postNew" />
    </div>
    <div v-else class="comment-thread-readonly-note">
      You have read-only access to this workspace and can't post comments.
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from "vue"
import type { Comment } from "../../services/comments"
import { useCommentsStore } from "../../stores/comments"
import { useAuthStore } from "../../stores/auth"
import CommentComposer from "./CommentComposer.vue"

const props = defineProps<{
  workspaceId: string
  notebookId: string
  blockId: string
}>()

const emit = defineEmits<{
  close: []
}>()

const commentsStore = useCommentsStore()
const authStore = useAuthStore()
const principals = computed(() => commentsStore.principals)
const canComment = computed(() => commentsStore.canComment)

const comments = computed(() => commentsStore.comments)
const loading = computed(() => commentsStore.loading)
const error = computed(() => commentsStore.error)

// Comment id currently being edited inline, or null.
const editingId = ref<number | null>(null)

interface ThreadGroup {
  root: Comment
  replies: Comment[]
}

const threads = computed<ThreadGroup[]>(() => {
  const repliesByRoot = new Map<number, Comment[]>()
  for (const comment of comments.value) {
    if (comment.thread_id === null) continue
    const list = repliesByRoot.get(comment.thread_id) ?? []
    list.push(comment)
    repliesByRoot.set(comment.thread_id, list)
  }
  return comments.value
    .filter((c) => c.thread_id === null)
    .map((root) => ({ root, replies: repliesByRoot.get(root.id) ?? [] }))
})

function load() {
  commentsStore.fetchComments(props.workspaceId, props.notebookId, props.blockId)
}

async function postNew(body: string) {
  await commentsStore.createComment(props.workspaceId, props.notebookId, props.blockId, body)
}

async function postReply(root: Comment, body: string) {
  await commentsStore.createComment(props.workspaceId, props.notebookId, props.blockId, body, root.id)
}

async function resolveThread(root: Comment) {
  await commentsStore.resolveComment(root.id)
}

async function saveEdit(comment: Comment, body: string) {
  await commentsStore.updateComment(comment.id, body)
  editingId.value = null
}

async function removeComment(comment: Comment) {
  await commentsStore.deleteComment(comment.id)
}

// Only the comment's author may edit it (mirrors the backend's PATCH /comments/{id} check).
function canEdit(comment: Comment): boolean {
  return canComment.value && comment.author_id === authStore.user?.id
}

// The author or a workspace admin may delete a comment (mirrors DELETE /comments/{id}).
function canDelete(comment: Comment): boolean {
  if (commentsStore.myPermissionLevel === "admin") return true
  return canEdit(comment)
}

function initials(username?: string | null): string {
  if (!username) return "?"
  return username.slice(0, 2).toUpperCase()
}

function formatTime(iso: string): string {
  try {
    return new Date(iso).toLocaleString()
  } catch {
    return iso
  }
}

watch(() => [props.workspaceId, props.notebookId, props.blockId], load)
onMounted(load)
</script>

<style scoped>
.comment-thread-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--color-bg-primary, #fff);
  color: var(--color-text-primary, #333);
}

.comment-thread-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid var(--color-border-light, #e0e0e0);
}

.comment-thread-title {
  margin: 0;
  font-size: 0.9375rem;
  font-weight: 600;
}

.comment-thread-close {
  border: none;
  background: transparent;
  color: var(--color-text-tertiary, #999);
  cursor: pointer;
  font-size: 0.8125rem;
  padding: 4px;
  border-radius: 4px;
}

.comment-thread-close:hover {
  background: var(--color-bg-hover, #f5f5f5);
  color: var(--color-text-secondary, #666);
}

.comment-thread-body {
  flex: 1;
  overflow-y: auto;
  padding: 12px 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.comment-thread-status {
  color: var(--color-text-tertiary, #999);
  font-size: 0.8125rem;
  padding: 8px 0;
}

.comment-thread-error {
  color: var(--color-error, #dc2626);
}

.comment-thread {
  padding-bottom: 12px;
  border-bottom: 1px solid var(--color-border-light, #eee);
}

.comment-thread:last-child {
  border-bottom: none;
}

.comment-thread.resolved {
  opacity: 0.7;
}

.comment-item {
  display: flex;
  gap: 8px;
}

.comment-avatar {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: var(--notebook-accent, #2563eb);
  color: white;
  font-size: 0.625rem;
  font-weight: 700;
}

.comment-item-body {
  flex: 1;
  min-width: 0;
}

.comment-item-header {
  display: flex;
  align-items: baseline;
  gap: 6px;
  margin-bottom: 2px;
}

.comment-item-actions {
  display: flex;
  gap: 10px;
  margin-top: 2px;
}

.comment-inline-btn {
  border: none;
  background: transparent;
  padding: 0;
  color: var(--color-text-tertiary, #999);
  font-size: 0.6875rem;
  cursor: pointer;
}

.comment-inline-btn:hover {
  color: var(--notebook-accent, #2563eb);
  text-decoration: underline;
}

.comment-author {
  font-weight: 600;
  font-size: 0.8125rem;
}

.comment-time {
  font-size: 0.6875rem;
  color: var(--color-text-tertiary, #999);
}

.comment-body {
  margin: 0;
  font-size: 0.875rem;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
}

.comment-resolved-banner {
  display: inline-block;
  margin-top: 6px;
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 0.6875rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  background: var(--color-success-bg, #f0fdf4);
  color: var(--color-success, #16a34a);
}

.comment-replies {
  margin-top: 10px;
  padding-left: 14px;
  border-left: 2px solid var(--color-border-light, #eee);
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.comment-thread-actions {
  margin-top: 10px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.comment-resolve-btn {
  align-self: flex-start;
  padding: 4px 10px;
  border: 1px solid var(--color-border-light, #e0e0e0);
  border-radius: 6px;
  background: transparent;
  color: var(--color-text-secondary, #666);
  font-size: 0.75rem;
  cursor: pointer;
}

.comment-resolve-btn:hover {
  background: var(--color-bg-hover, #f5f5f5);
}

.comment-thread-new {
  padding: 12px 16px;
  border-top: 1px solid var(--color-border-light, #e0e0e0);
}

.comment-thread-readonly-note {
  padding: 10px 16px;
  border-top: 1px solid var(--color-border-light, #e0e0e0);
  font-size: 0.75rem;
  color: var(--color-text-tertiary, #999);
}
</style>
