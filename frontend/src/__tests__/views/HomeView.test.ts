import { describe, it, expect, beforeEach, vi } from "vitest"
import { mount, flushPromises } from "@vue/test-utils"
import { createRouter, createWebHistory } from "vue-router"
import { setActivePinia, createPinia } from "pinia"
import HomeView from "../../views/HomeView.vue"
import { useWorkspaceStore } from "../../stores/workspace"

// Mock the services
vi.mock("../../services/codex", () => ({
  workspaceService: {
    list: vi.fn(),
  },
  notebookService: {
    list: vi.fn(),
  },
  fileService: {},
  folderService: {},
}))

// Create a mock router for testing
const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", component: HomeView },
    { path: "/login", component: { template: "Login" } },
  ],
})

describe("HomeView", () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it("automatically selects first workspace when workspaces are loaded", async () => {
    const { workspaceService } = await import("../../services/codex")
    
    // Mock workspaces
    const mockWorkspaces = [
      { id: 1, name: "Workspace 1", owner_id: 1, created_at: new Date().toISOString() },
      { id: 2, name: "Workspace 2", owner_id: 1, created_at: new Date().toISOString() },
    ]
    
    vi.mocked(workspaceService.list).mockResolvedValue(mockWorkspaces)
    
    const wrapper = mount(HomeView, {
      global: {
        plugins: [router],
        stubs: {
          // Stub child components to simplify test
          SearchBar: { template: "<div></div>" },
        },
      },
    })
    
    // Wait for async operations to complete
    await flushPromises()
    
    const workspaceStore = useWorkspaceStore()
    
    // Verify that workspaces were fetched
    expect(workspaceService.list).toHaveBeenCalled()
    
    // Verify that the first workspace was automatically selected
    expect(workspaceStore.currentWorkspace).toBeTruthy()
    expect(workspaceStore.currentWorkspace?.id).toBe(1)
    expect(workspaceStore.currentWorkspace?.name).toBe("Workspace 1")
  })

  it("does not select workspace when no workspaces exist", async () => {
    const { workspaceService } = await import("../../services/codex")
    
    // Mock empty workspaces
    vi.mocked(workspaceService.list).mockResolvedValue([])
    
    const wrapper = mount(HomeView, {
      global: {
        plugins: [router],
        stubs: {
          SearchBar: { template: "<div></div>" },
        },
      },
    })
    
    // Wait for async operations to complete
    await flushPromises()
    
    const workspaceStore = useWorkspaceStore()
    
    // Verify that no workspace was selected
    expect(workspaceStore.currentWorkspace).toBeNull()
  })

  it("does not override existing workspace selection", async () => {
    const { workspaceService } = await import("../../services/codex")
    
    // Mock workspaces
    const mockWorkspaces = [
      { id: 1, name: "Workspace 1", owner_id: 1, created_at: new Date().toISOString() },
      { id: 2, name: "Workspace 2", owner_id: 1, created_at: new Date().toISOString() },
    ]
    
    vi.mocked(workspaceService.list).mockResolvedValue(mockWorkspaces)
    
    const workspaceStore = useWorkspaceStore()
    // Pre-select the second workspace
    workspaceStore.currentWorkspace = mockWorkspaces[1]
    
    const wrapper = mount(HomeView, {
      global: {
        plugins: [router],
        stubs: {
          SearchBar: { template: "<div></div>" },
        },
      },
    })
    
    // Wait for async operations to complete
    await flushPromises()
    
    // Verify that the pre-selected workspace was not changed
    expect(workspaceStore.currentWorkspace?.id).toBe(2)
    expect(workspaceStore.currentWorkspace?.name).toBe("Workspace 2")
  })

  it("automatically selects first notebook after workspace is selected", async () => {
    const { workspaceService, notebookService } = await import("../../services/codex")
    
    // Mock workspaces
    const mockWorkspaces = [
      { id: 1, name: "Workspace 1", owner_id: 1, created_at: new Date().toISOString() },
    ]
    
    // Mock notebooks
    const mockNotebooks = [
      { id: 1, name: "Notebook 1", path: "/notebook1", workspace_id: 1, created_at: new Date().toISOString(), updated_at: new Date().toISOString() },
      { id: 2, name: "Notebook 2", path: "/notebook2", workspace_id: 1, created_at: new Date().toISOString(), updated_at: new Date().toISOString() },
    ]
    
    vi.mocked(workspaceService.list).mockResolvedValue(mockWorkspaces)
    vi.mocked(notebookService.list).mockResolvedValue(mockNotebooks)
    
    const wrapper = mount(HomeView, {
      global: {
        plugins: [router],
        stubs: {
          SearchBar: { template: "<div></div>" },
        },
      },
    })
    
    // Wait for async operations to complete
    await flushPromises()
    
    const workspaceStore = useWorkspaceStore()
    
    // Verify that the first notebook was automatically expanded
    expect(workspaceStore.expandedNotebooks.has(1)).toBe(true)
    expect(workspaceStore.currentNotebook?.id).toBe(1)
    expect(workspaceStore.currentNotebook?.name).toBe("Notebook 1")
  })
})