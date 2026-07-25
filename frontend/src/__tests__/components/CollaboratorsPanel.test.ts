import { describe, it, expect, beforeEach, afterEach, vi, type Mock } from "vitest"
import { mount } from "@vue/test-utils"
import { setActivePinia, createPinia } from "pinia"
import CollaboratorsPanel from "../../components/settings/CollaboratorsPanel.vue"
import { useWorkspaceStore } from "../../stores/workspace"
import { collaboratorService } from "../../services/collaborators"

vi.mock("../../services/collaborators", () => ({
  collaboratorService: {
    list: vi.fn(),
    invite: vi.fn(),
    updateLevel: vi.fn(),
    revoke: vi.fn(),
  },
}))

const mockList = collaboratorService.list as Mock
const mockInvite = collaboratorService.invite as Mock
const mockUpdateLevel = collaboratorService.updateLevel as Mock
const mockRevoke = collaboratorService.revoke as Mock

const owner = {
  user_id: 1,
  username: "owner",
  email: "owner@example.com",
  permission_level: "admin" as const,
  is_owner: true,
  created_at: "2024-01-01T00:00:00Z",
}

const collaborator = {
  user_id: 2,
  username: "jane",
  email: "jane@example.com",
  permission_level: "write" as const,
  is_owner: false,
  created_at: "2024-01-01T00:00:00Z",
}

let wrapper: any

function mountPanel(workspaceId = 1) {
  setActivePinia(createPinia())
  const workspaceStore = useWorkspaceStore()
  workspaceStore.workspaces = [
    { id: 1, slug: "my-workspace", name: "My Workspace", path: "/p", owner_id: 1, created_at: "", updated_at: "" },
  ]
  wrapper = mount(CollaboratorsPanel, {
    props: { workspaceId },
    attachTo: document.body,
  })
  return wrapper
}

afterEach(() => {
  wrapper?.unmount()
})

describe("CollaboratorsPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("loads and displays collaborators, marking the owner separately", async () => {
    mockList.mockResolvedValue([owner, collaborator])
    mountPanel()
    await new Promise((resolve) => setTimeout(resolve, 0))
    await wrapper.vm.$nextTick()

    expect(mockList).toHaveBeenCalledWith("my-workspace")
    const text = wrapper.text()
    expect(text).toContain("owner")
    expect(text).toContain("jane")
    expect(text).toContain("Owner")
  })

  it("shows a forbidden message when the user lacks admin access", async () => {
    mockList.mockRejectedValue({ response: { status: 403 } })
    mountPanel()
    await new Promise((resolve) => setTimeout(resolve, 0))
    await wrapper.vm.$nextTick()

    expect(wrapper.text()).toContain("need admin access")
  })

  it("invites a collaborator and adds them to the list", async () => {
    mockList.mockResolvedValue([owner])
    mockInvite.mockResolvedValue(collaborator)
    mountPanel()
    await new Promise((resolve) => setTimeout(resolve, 0))
    await wrapper.vm.$nextTick()

    ;(wrapper.find("button.create-btn").element as HTMLElement).click()
    await wrapper.vm.$nextTick()

    const input = wrapper.find('input[type="text"]')
    await input.setValue("jane")

    ;(document.querySelector(".btn-primary") as HTMLElement).click()
    await new Promise((resolve) => setTimeout(resolve, 0))
    await wrapper.vm.$nextTick()

    expect(mockInvite).toHaveBeenCalledWith("my-workspace", "jane", "read")
    expect(wrapper.text()).toContain("jane")
  })

  it("updates a collaborator's permission level", async () => {
    mockList.mockResolvedValue([owner, collaborator])
    mockUpdateLevel.mockResolvedValue({ ...collaborator, permission_level: "admin" })
    mountPanel()
    await new Promise((resolve) => setTimeout(resolve, 0))
    await wrapper.vm.$nextTick()

    const select = wrapper.find("select.level-select")
    await select.setValue("admin")

    expect(mockUpdateLevel).toHaveBeenCalledWith("my-workspace", 2, "admin")
  })

  it("removes a collaborator", async () => {
    mockList.mockResolvedValue([owner, collaborator])
    mockRevoke.mockResolvedValue(undefined)
    mountPanel()
    await new Promise((resolve) => setTimeout(resolve, 0))
    await wrapper.vm.$nextTick()

    ;(wrapper.find("button.remove-btn").element as HTMLElement).click()
    await new Promise((resolve) => setTimeout(resolve, 0))
    await wrapper.vm.$nextTick()

    expect(mockRevoke).toHaveBeenCalledWith("my-workspace", 2)
    expect(wrapper.text()).not.toContain("jane")
  })
})
