import { describe, it, expect, beforeEach, vi, type Mock } from "vitest"
import { setActivePinia, createPinia } from "pinia"
import { useCommentsStore } from "../../stores/comments"
import { commentService, principalService, permissionService, type Comment } from "../../services/comments"
import { websocketService } from "../../services/websocket"

vi.mock("../../services/comments", () => ({
  commentService: {
    list: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
    delete: vi.fn(),
    resolve: vi.fn(),
    counts: vi.fn(),
  },
  principalService: { list: vi.fn() },
  permissionService: { getMine: vi.fn() },
}))

vi.mock("../../services/websocket", () => ({
  websocketService: { onNotification: vi.fn(() => vi.fn()) },
}))

function makeComment(overrides: Partial<Comment> = {}): Comment {
  return {
    id: 1,
    workspace_id: 1,
    notebook_id: 1,
    block_id: "blk_1",
    thread_id: null,
    author_id: 10,
    author_username: "alice",
    body: "hello",
    resolved_at: null,
    resolved_by_id: null,
    created_at: "2024-01-01T00:00:00Z",
    updated_at: "2024-01-01T00:00:00Z",
    mentions: [],
    ...overrides,
  }
}

describe("Comments Store", () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it("has correct default values", () => {
    const store = useCommentsStore()
    expect(store.commentCounts.size).toBe(0)
    expect(store.principals).toEqual([])
    expect(store.myPermissionLevel).toBeNull()
    expect(store.comments).toEqual([])
    expect(store.loading).toBe(false)
    expect(store.error).toBeNull()
    expect(store.canComment).toBe(false)
  })

  it("derives canComment from the permission level", () => {
    const store = useCommentsStore()
    for (const level of ["comment", "write", "admin"] as const) {
      store.myPermissionLevel = level
      expect(store.canComment).toBe(true)
    }
    store.myPermissionLevel = "read"
    expect(store.canComment).toBe(false)
  })

  it("fetchComments loads comments for a block, and clears on failure", async () => {
    const store = useCommentsStore()
    ;(commentService.list as Mock).mockResolvedValue([makeComment()])
    await store.fetchComments("ws", "nb", "blk_1")
    expect(store.comments).toHaveLength(1)
    expect(store.loading).toBe(false)
    expect(store.error).toBeNull()

    ;(commentService.list as Mock).mockRejectedValue({ response: { data: { detail: "nope" } } })
    await store.fetchComments("ws", "nb", "blk_1")
    expect(store.comments).toEqual([])
    expect(store.error).toBe("nope")
  })

  it("createComment appends the new comment and increments the block's count", async () => {
    const store = useCommentsStore()
    ;(commentService.create as Mock).mockResolvedValue(makeComment({ id: 2, body: "new" }))
    await store.createComment("ws", "nb", "blk_1", "new")
    expect(store.comments.map((c) => c.body)).toEqual(["new"])
    expect(store.getCount("blk_1")).toBe(1)
  })

  it("updateComment replaces the comment in place", async () => {
    const store = useCommentsStore()
    store.comments = [makeComment({ id: 1, body: "old" })]
    ;(commentService.update as Mock).mockResolvedValue(makeComment({ id: 1, body: "edited" }))
    await store.updateComment(1, "edited")
    expect(store.comments[0]!.body).toBe("edited")
  })

  it("deleteComment removes the comment and decrements the block's count", async () => {
    const store = useCommentsStore()
    store.comments = [makeComment({ id: 1, block_id: "blk_1" })]
    store.setCount("blk_1", 1)
    ;(commentService.delete as Mock).mockResolvedValue(undefined)
    await store.deleteComment(1)
    expect(store.comments).toEqual([])
    expect(store.getCount("blk_1")).toBe(0)
  })

  it("resolveComment updates the resolved comment in place", async () => {
    const store = useCommentsStore()
    store.comments = [makeComment({ id: 1 })]
    ;(commentService.resolve as Mock).mockResolvedValue(makeComment({ id: 1, resolved_at: "2024-01-02T00:00:00Z" }))
    await store.resolveComment(1)
    expect(store.comments[0]!.resolved_at).toBe("2024-01-02T00:00:00Z")
  })

  it("fetchPrincipals and fetchMyPermission populate state, and reset on failure", async () => {
    const store = useCommentsStore()
    ;(principalService.list as Mock).mockResolvedValue([{ id: 1, username: "alice" }])
    ;(permissionService.getMine as Mock).mockResolvedValue("write")
    await store.fetchPrincipals("ws")
    await store.fetchMyPermission("ws")
    expect(store.principals).toEqual([{ id: 1, username: "alice" }])
    expect(store.myPermissionLevel).toBe("write")

    ;(principalService.list as Mock).mockRejectedValue(new Error("fail"))
    await store.fetchPrincipals("ws")
    expect(store.principals).toEqual([])
  })

  it("reset clears all state", () => {
    const store = useCommentsStore()
    store.comments = [makeComment()]
    store.principals = [{ id: 1, username: "alice" }]
    store.myPermissionLevel = "write"
    store.setCount("blk_1", 3)
    store.error = "boom"

    store.reset()

    expect(store.comments).toEqual([])
    expect(store.principals).toEqual([])
    expect(store.myPermissionLevel).toBeNull()
    expect(store.commentCounts.size).toBe(0)
    expect(store.error).toBeNull()
  })

  it("init subscribes once to the WebSocket notification channel and bumps counts on comment events", () => {
    const store = useCommentsStore()
    store.init()
    store.init() // idempotent
    expect(websocketService.onNotification).toHaveBeenCalledTimes(1)

    const handler = (websocketService.onNotification as Mock).mock.calls[0][0]
    handler({ kind: "comment.created", subject: { block_id: "blk_1" } })
    expect(store.getCount("blk_1")).toBe(1)

    handler({ kind: "comment.mention", subject: { block_id: "blk_1" } })
    expect(store.getCount("blk_1")).toBe(2)

    // Unrelated notification kinds are ignored.
    handler({ kind: "permission.granted", subject: { block_id: "blk_1" } })
    expect(store.getCount("blk_1")).toBe(2)
  })

  it("teardown unsubscribes from the WebSocket channel", () => {
    const store = useCommentsStore()
    const unsubscribe = vi.fn()
    ;(websocketService.onNotification as Mock).mockReturnValue(unsubscribe)
    store.init()
    store.teardown()
    expect(unsubscribe).toHaveBeenCalled()
  })
})
