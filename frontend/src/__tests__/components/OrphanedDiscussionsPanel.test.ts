import { describe, it, expect, beforeEach, afterEach, vi, type Mock } from "vitest"
import { mount } from "@vue/test-utils"
import { setActivePinia, createPinia } from "pinia"
import OrphanedDiscussionsPanel from "../../components/settings/OrphanedDiscussionsPanel.vue"
import { useWorkspaceStore } from "../../stores/workspace"
import { orphanedDiscussionsService } from "../../services/orphanedDiscussions"
import { principalService } from "../../services/comments"

vi.mock("../../services/orphanedDiscussions", () => ({
  orphanedDiscussionsService: {
    list: vi.fn(),
    get: vi.fn(),
    restore: vi.fn(),
    archive: vi.fn(),
    delete: vi.fn(),
    bulkAction: vi.fn(),
    auditLog: vi.fn(),
  },
}))

vi.mock("../../services/comments", () => ({
  principalService: {
    list: vi.fn(),
  },
}))

const mockList = orphanedDiscussionsService.list as Mock
const mockArchive = orphanedDiscussionsService.archive as Mock
const mockDelete = orphanedDiscussionsService.delete as Mock
const mockBulkAction = orphanedDiscussionsService.bulkAction as Mock
const mockAuditLog = orphanedDiscussionsService.auditLog as Mock
const mockPrincipalList = principalService.list as Mock

const blockDeletedThread = {
  thread_id: 1,
  workspace_id: 1,
  notebook_id: 1,
  notebook_name: "Test Notebook",
  block_id: "01ABC",
  reason: "block_deleted" as const,
  root: {
    id: 1,
    author_id: 2,
    author_username: "jane",
    body: "Please take a look at this",
    created_at: "2024-01-01T00:00:00Z",
    deleted_at: null,
  },
  replies: [],
  reply_count: 2,
  last_activity_at: "2024-01-02T00:00:00Z",
  archived_at: null,
  archived_by_id: null,
  archived_by_username: null,
}

const rootDeletedThread = {
  ...blockDeletedThread,
  thread_id: 2,
  reason: "root_deleted" as const,
  root: { ...blockDeletedThread.root, id: 2, body: "Original question" },
}

let wrapper: any

function mountPanel(workspaceId = 1) {
  setActivePinia(createPinia())
  const workspaceStore = useWorkspaceStore()
  workspaceStore.workspaces = [
    { id: 1, slug: "my-workspace", name: "My Workspace", path: "/p", owner_id: 1, created_at: "", updated_at: "" },
  ]
  wrapper = mount(OrphanedDiscussionsPanel, {
    props: { workspaceId },
    attachTo: document.body,
  })
  return wrapper
}

afterEach(() => {
  wrapper?.unmount()
})

describe("OrphanedDiscussionsPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockPrincipalList.mockResolvedValue([{ id: 2, username: "jane" }])
  })

  it("loads and displays orphaned threads with their reason", async () => {
    mockList.mockResolvedValue([blockDeletedThread])
    mountPanel()
    await new Promise((resolve) => setTimeout(resolve, 0))
    await wrapper.vm.$nextTick()

    expect(mockList).toHaveBeenCalledWith("my-workspace", {
      author_id: undefined,
      start_date: undefined,
      end_date: undefined,
      include_archived: false,
    })
    const text = wrapper.text()
    expect(text).toContain("Please take a look at this")
    expect(text).toContain("Block deleted")
    expect(text).toContain("jane")
  })

  it("shows a forbidden message when the user lacks admin access", async () => {
    mockList.mockRejectedValue({ response: { status: 403 } })
    mountPanel()
    await new Promise((resolve) => setTimeout(resolve, 0))
    await wrapper.vm.$nextTick()

    expect(wrapper.text()).toContain("need admin access")
  })

  it("shows an empty state when there are no orphaned discussions", async () => {
    mockList.mockResolvedValue([])
    mountPanel()
    await new Promise((resolve) => setTimeout(resolve, 0))
    await wrapper.vm.$nextTick()

    expect(wrapper.text()).toContain("No orphaned discussions found")
  })

  it("archives a thread and removes it from the default list", async () => {
    mockList.mockResolvedValue([blockDeletedThread])
    mockArchive.mockResolvedValue({ ...blockDeletedThread, archived_at: "2024-01-03T00:00:00Z" })
    mountPanel()
    await new Promise((resolve) => setTimeout(resolve, 0))
    await wrapper.vm.$nextTick()

    const archiveBtn = wrapper.findAll("button").find((b: any) => b.text() === "Archive")
    await archiveBtn.trigger("click")
    await new Promise((resolve) => setTimeout(resolve, 0))
    await wrapper.vm.$nextTick()

    expect(mockArchive).toHaveBeenCalledWith("my-workspace", 1)
    expect(wrapper.text()).toContain("No orphaned discussions found")
  })

  it("permanently deletes a thread after confirmation", async () => {
    vi.stubGlobal("confirm", vi.fn(() => true))
    mockList.mockResolvedValue([blockDeletedThread])
    mockDelete.mockResolvedValue(undefined)
    mountPanel()
    await new Promise((resolve) => setTimeout(resolve, 0))
    await wrapper.vm.$nextTick()

    const deleteBtn = wrapper.findAll("button").find((b: any) => b.text() === "Delete")
    await deleteBtn.trigger("click")
    await new Promise((resolve) => setTimeout(resolve, 0))
    await wrapper.vm.$nextTick()

    expect(mockDelete).toHaveBeenCalledWith("my-workspace", 1)
    expect(wrapper.text()).toContain("No orphaned discussions found")
    vi.unstubAllGlobals()
  })

  it("bulk-archives selected threads", async () => {
    mockList.mockResolvedValue([blockDeletedThread, rootDeletedThread])
    mockBulkAction.mockResolvedValue([
      { thread_id: 1, success: true },
      { thread_id: 2, success: true },
    ])
    mountPanel()
    await new Promise((resolve) => setTimeout(resolve, 0))
    await wrapper.vm.$nextTick()

    // Index 0 is the "Include archived" filter checkbox; the thread-row checkboxes follow it.
    const checkboxes = wrapper.findAll('input[type="checkbox"]')
    await checkboxes[1].setValue(true)
    await checkboxes[2].setValue(true)
    await wrapper.vm.$nextTick()

    expect(wrapper.text()).toContain("2 selected")

    mockList.mockResolvedValue([])
    const bulkArchiveBtn = wrapper.findAll("button").find((b: any) => b.text() === "Archive" && !b.classes().includes("danger-btn"))
    await bulkArchiveBtn.trigger("click")
    await new Promise((resolve) => setTimeout(resolve, 0))
    await wrapper.vm.$nextTick()

    expect(mockBulkAction).toHaveBeenCalledWith("my-workspace", [1, 2], "archive")
  })

  it("switches to the audit log tab and loads entries", async () => {
    mockList.mockResolvedValue([])
    mockAuditLog.mockResolvedValue([
      { id: 1, kind: "comment.orphan_archived", actor_id: 2, actor_username: "jane", subject: {}, created_at: "2024-01-01T00:00:00Z" },
    ])
    mountPanel()
    await new Promise((resolve) => setTimeout(resolve, 0))
    await wrapper.vm.$nextTick()

    const auditTabBtn = wrapper.findAll("button").find((b: any) => b.text() === "Audit Log")
    await auditTabBtn.trigger("click")
    await new Promise((resolve) => setTimeout(resolve, 0))
    await wrapper.vm.$nextTick()

    expect(mockAuditLog).toHaveBeenCalledWith("my-workspace")
    expect(wrapper.text()).toContain("archived")
    expect(wrapper.text()).toContain("jane")
  })
})
