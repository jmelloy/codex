import { defineStore } from "pinia"
import { ref, computed } from "vue"
import { commentService, principalService, permissionService, type Principal } from "../services/comments"
import type { PermissionLevel } from "../services/collaborators"

export const useCommentsStore = defineStore("comments", () => {
  // Comment counts per block, for the current notebook (block_id -> count)
  const commentCounts = ref<Map<string, number>>(new Map())
  // Workspace-visible principals, for @mention autocomplete
  const principals = ref<Principal[]>([])
  // The current user's effective permission level on the current workspace
  const myPermissionLevel = ref<PermissionLevel | null>(null)

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

  function reset() {
    commentCounts.value = new Map()
    principals.value = []
    myPermissionLevel.value = null
  }

  return {
    commentCounts,
    principals,
    myPermissionLevel,
    canComment,
    getCount,
    setCount,
    incrementCount,
    fetchCounts,
    fetchPrincipals,
    fetchMyPermission,
    reset,
  }
})
