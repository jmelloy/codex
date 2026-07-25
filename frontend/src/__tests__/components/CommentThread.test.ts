import { describe, it, expect, beforeEach, afterEach, vi, type Mock } from "vitest"
import { mount } from "@vue/test-utils"
import { setActivePinia, createPinia } from "pinia"
import CommentThread from "../../components/comments/CommentThread.vue"
import { useCommentsStore } from "../../stores/comments"
import { useAuthStore } from "../../stores/auth"
import { commentService, type Comment } from "../../services/comments"

vi.mock("../../services/comments", async () => {
  const actual = await vi.importActual<typeof import("../../services/comments")>("../../services/comments")
  return {
    ...actual,
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
  }
})

vi.mock("../../services/websocket", () => ({
  websocketService: { onNotification: vi.fn(() => () => {}) },
}))

const mockList = commentService.list as Mock
const mockCreate = commentService.create as Mock
const mockUpdate = commentService.update as Mock
const mockDelete = commentService.delete as Mock
const mockResolve = commentService.resolve as Mock

function makeComment(overrides: Partial<Comment> = {}): Comment {
  return {
    id: 1,
    workspace_id: 1,
    notebook_id: 1,
    block_id: "blk_1",
    thread_id: null,
    author_id: 10,
    author_username: "alice",
    body: "root comment",
    resolved_at: null,
    resolved_by_id: null,
    created_at: "2024-01-01T00:00:00Z",
    updated_at: "2024-01-01T00:00:00Z",
    mentions: [],
    ...overrides,
  }
}

let wrapper: any

afterEach(() => {
  wrapper?.unmount()
})

async function mountThread(permissionLevel: "read" | "comment" | "write" | "admin" = "comment", userId = 99) {
  setActivePinia(createPinia())
  const commentsStore = useCommentsStore()
  commentsStore.myPermissionLevel = permissionLevel
  commentsStore.principals = [{ id: 10, username: "alice" }]
  const authStore = useAuthStore()
  authStore.user = { id: userId, username: "me" } as any

  wrapper = mount(CommentThread, {
    props: { workspaceId: "ws", notebookId: "nb", blockId: "blk_1" },
    attachTo: document.body,
  })
  await new Promise((resolve) => setTimeout(resolve, 0))
  await wrapper.vm.$nextTick()
  return wrapper
}

describe("CommentThread", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("loads and groups root comments with their replies", async () => {
    mockList.mockResolvedValue([
      makeComment({ id: 1, body: "root comment" }),
      makeComment({ id: 2, thread_id: 1, body: "a reply", author_username: "bob", author_id: 20 }),
    ])
    await mountThread()

    expect(mockList).toHaveBeenCalledWith("ws", "nb", "blk_1")
    expect(wrapper.text()).toContain("root comment")
    expect(wrapper.text()).toContain("a reply")
    expect(wrapper.findAll(".comment-thread")).toHaveLength(1)
  })

  it("shows an empty state when there are no comments", async () => {
    mockList.mockResolvedValue([])
    await mountThread()
    expect(wrapper.text()).toContain("No comments yet")
  })

  it("hides the composer and shows a readonly note for read-only users", async () => {
    mockList.mockResolvedValue([makeComment()])
    await mountThread("read")

    expect(wrapper.find(".comment-thread-new").exists()).toBe(false)
    expect(wrapper.text()).toContain("read-only access")
  })

  it("posts a new top-level comment for users with comment permission", async () => {
    mockList.mockResolvedValue([])
    mockCreate.mockResolvedValue(makeComment({ id: 5, body: "new one" }))
    await mountThread("comment")

    await wrapper.find(".comment-thread-new textarea").setValue("new one")
    await wrapper.find(".comment-thread-new button.composer-btn-primary").trigger("click")
    await wrapper.vm.$nextTick()

    expect(mockCreate).toHaveBeenCalledWith("ws", "nb", "blk_1", "new one", undefined)
    expect(wrapper.text()).toContain("new one")
    expect(useCommentsStore().getCount("blk_1")).toBe(1)
  })

  it("resolves a thread and shows the resolved banner", async () => {
    const root = makeComment({ id: 1 })
    mockList.mockResolvedValue([root])
    mockResolve.mockResolvedValue({ ...root, resolved_at: "2024-01-02T00:00:00Z", resolved_by_id: 99 })
    await mountThread("comment")

    await wrapper.find("button.comment-resolve-btn").trigger("click")
    await wrapper.vm.$nextTick()

    expect(mockResolve).toHaveBeenCalledWith(1)
    expect(wrapper.text()).toContain("Resolved")
  })

  it("only shows edit/delete to the comment's author", async () => {
    mockList.mockResolvedValue([
      makeComment({ id: 1, author_id: 10, author_username: "alice" }), // not the current user
      makeComment({ id: 2, thread_id: 1, author_id: 99, author_username: "me" }), // current user
    ])
    await mountThread("comment", 99)

    const items = wrapper.findAll(".comment-item")
    expect(items[0].find(".comment-inline-btn").exists()).toBe(false) // alice's root comment
    const replyActions = items[1].findAll(".comment-inline-btn")
    expect(replyActions.map((b: any) => b.text())).toEqual(["Edit", "Delete"])
  })

  it("lets a workspace admin delete a comment they don't own", async () => {
    mockList.mockResolvedValue([makeComment({ id: 1, author_id: 10 })])
    mockDelete.mockResolvedValue(undefined)
    await mountThread("admin", 99)

    const deleteBtn = wrapper.findAll(".comment-inline-btn").find((b: any) => b.text() === "Delete")
    expect(deleteBtn).toBeDefined()
    await deleteBtn!.trigger("click")
    await wrapper.vm.$nextTick()

    expect(mockDelete).toHaveBeenCalledWith(1)
    expect(wrapper.text()).not.toContain("root comment")
  })

  it("edits a comment's body inline", async () => {
    mockList.mockResolvedValue([makeComment({ id: 1, author_id: 99, body: "before" })])
    mockUpdate.mockResolvedValue(makeComment({ id: 1, author_id: 99, body: "after" }))
    await mountThread("comment", 99)

    await wrapper.find(".comment-inline-btn").trigger("click")
    await wrapper.vm.$nextTick()

    const editTextarea = wrapper.find(".comment-item-body textarea")
    await editTextarea.setValue("after")
    await wrapper.find(".comment-item-body button.composer-btn-primary").trigger("click")
    await new Promise((resolve) => setTimeout(resolve, 0))
    await wrapper.vm.$nextTick()

    expect(mockUpdate).toHaveBeenCalledWith(1, "after")
    expect(wrapper.text()).toContain("after")
    expect(wrapper.text()).not.toContain("before")
  })
})
