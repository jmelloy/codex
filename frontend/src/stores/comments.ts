import { defineStore } from "pinia"
import { ref, computed } from "vue"
import { commentService, principalService, permissionService, type Comment, type Principal } from "../services/comments"
import type { PermissionLevel } from "../services/collaborators"
import { websocketService } from "../services/websocket"

// Notification kinds that indicate a block's comment count may have changed.
const COMMENT_CREATED_KINDS = new Set(["comment.created", "comment.mention"])

export const useCommentsStore = defineStore("comments", () => {
  // Comment counts per block, for the current notebook (block_id -> count)
  const commentCounts = ref<Map<string, number>>(new Map())
  // Workspace-visible principals, for @mention autocomplete
  const principals = ref<Principal[]>([])
  // The current user's effective permission level on the current workspace
  const myPermissionLevel = ref<PermissionLevel | null>(null)
  // Comments for the currently open thread panel (flat list: roots + replies)
  const comments = ref<Comment[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  let wsUnsubscribe: (() => void) | null = null

  // read/comment/write/admin — only comment level and above can post
  const canComment = computed(() => {
    const level = myPermissionLevel.value
    return level === "comment" || level === "write" || level === "admin"
  })

  function getCount(blockId: string): number {
    return commentCounts.value.get(blockId) ?? 0
  }

  function setCount(blockId: string, count: number) {
    commentCounts.value.set(blockId, count)
    // Replace the map reference so Vue's reactivity picks up the mutation
    commentCounts.value = new Map(commentCounts.value)
  }

  function incrementCount(blockId: string, delta: number) {
    setCount(blockId, Math.max(0, getCount(blockId) + delta))
  }

  async function fetchCounts(workspaceIdentifier: string, notebookIdentifier: string) {
    try {
      const counts = await commentService.counts(workspaceIdentifier, notebookIdentifier)
      commentCounts.value = new Map(counts.map((c) => [c.block_id, c.count]))
    } catch {
      // Comment counts are a nice-to-have indicator; leave the previous state on failure.
    }
  }

  async function fetchPrincipals(workspaceIdentifier: string) {
    try {
      principals.value = await principalService.list(workspaceIdentifier)
    } catch {
      principals.value = []
    }
  }

  async function fetchMyPermission(workspaceIdentifier: string) {
    try {
      myPermissionLevel.value = await permissionService.getMine(workspaceIdentifier)
    } catch {
      myPermissionLevel.value = null
    }
  }

  /** Load the comments (threads + replies) for a single block's thread panel. */
  async function fetchComments(workspaceIdentifier: string, notebookIdentifier: string, blockId: string) {
    loading.value = true
    error.value = null
    try {
      comments.value = await commentService.list(workspaceIdentifier, notebookIdentifier, blockId)
    } catch (e: any) {
      error.value = e.response?.data?.detail || "Failed to load comments"
      comments.value = []
    } finally {
      loading.value = false
    }
  }

  async function createComment(
    workspaceIdentifier: string,
    notebookIdentifier: string,
    blockId: string,
    body: string,
    threadId?: number,
  ): Promise<Comment> {
    const created = await commentService.create(workspaceIdentifier, notebookIdentifier, blockId, body, threadId)
    comments.value = [...comments.value, created]
    incrementCount(blockId, 1)
    return created
  }

  async function updateComment(commentId: number, body: string): Promise<Comment> {
    const updated = await commentService.update(commentId, body)
    const idx = comments.value.findIndex((c) => c.id === commentId)
    if (idx !== -1) comments.value[idx] = updated
    return updated
  }

  async function deleteComment(commentId: number): Promise<void> {
    const target = comments.value.find((c) => c.id === commentId)
    await commentService.delete(commentId)
    comments.value = comments.value.filter((c) => c.id !== commentId)
    if (target) incrementCount(target.block_id, -1)
  }

  async function resolveComment(commentId: number): Promise<Comment> {
    const resolved = await commentService.resolve(commentId)
    const idx = comments.value.findIndex((c) => c.id === resolved.id)
    if (idx !== -1) comments.value[idx] = resolved
    return resolved
  }

  /** Live-update per-block counts as comment notifications arrive over the WS channel. */
  function handleNotification(notification: { kind: string; subject: Record<string, any> }) {
    if (!COMMENT_CREATED_KINDS.has(notification.kind)) return
    const blockId = notification.subject?.block_id
    if (typeof blockId !== "string") return
    incrementCount(blockId, 1)
  }

  /** Wire up the live WebSocket listener for comment counts. Idempotent — safe on every mount. */
  function init() {
    if (wsUnsubscribe) return
    wsUnsubscribe = websocketService.onNotification(handleNotification)
  }

  function teardown() {
    wsUnsubscribe?.()
    wsUnsubscribe = null
  }

  function reset() {
    commentCounts.value = new Map()
    principals.value = []
    myPermissionLevel.value = null
    comments.value = []
    loading.value = false
    error.value = null
  }

  return {
    commentCounts,
    principals,
    myPermissionLevel,
    comments,
    loading,
    error,
    canComment,
    getCount,
    setCount,
    incrementCount,
    fetchCounts,
    fetchPrincipals,
    fetchMyPermission,
    fetchComments,
    createComment,
    updateComment,
    deleteComment,
    resolveComment,
    init,
    teardown,
    reset,
  }
})
