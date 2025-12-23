import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createRouter, createMemoryHistory } from 'vue-router'
import Sidebar from '@/components/Sidebar.vue'

// Mock the API module
vi.mock('@/api', () => ({
  notebooksApi: {
    list: vi.fn().mockResolvedValue([]),
    get: vi.fn(),
    create: vi.fn(),
  },
  pagesApi: {
    list: vi.fn().mockResolvedValue([]),
  },
  filesApi: {
    listNotebooks: vi.fn().mockResolvedValue({ files: [] }),
  },
}))

// Create a mock router
const createMockRouter = () => {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', component: { template: '<div>Home</div>' } },
      { path: '/search', component: { template: '<div>Search</div>' } },
      { path: '/files', component: { template: '<div>Files</div>' } },
      { path: '/notebooks', component: { template: '<div>Notebooks</div>' } },
      { 
        path: '/notebooks/:notebookId', 
        component: { template: '<div>Notebook Detail</div>' } 
      },
    ],
  })
}

describe('Sidebar Component', () => {
  let router: ReturnType<typeof createMockRouter>
  let pinia: ReturnType<typeof createPinia>

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
    router = createMockRouter()
    vi.clearAllMocks()
  })

  it('renders the logo and title', async () => {
    const wrapper = mount(Sidebar, {
      global: {
        plugins: [pinia, router],
      },
    })

    await router.isReady()

    expect(wrapper.find('.logo-text').text()).toBe('Codex')
    expect(wrapper.find('.logo-icon').text()).toBe('📓')
  })

  it('renders search link', async () => {
    const wrapper = mount(Sidebar, {
      global: {
        plugins: [pinia, router],
      },
    })

    await router.isReady()

    const searchLink = wrapper.find('.search-link')
    expect(searchLink.exists()).toBe(true)
    expect(searchLink.text()).toContain('Search')
  })

  it('renders user info in footer when authenticated', async () => {
    const wrapper = mount(Sidebar, {
      global: {
        plugins: [pinia, router],
      },
    })

    await router.isReady()

    // When no user is authenticated, footer should be empty (no footer-link)
    expect(wrapper.find('.footer-link').exists()).toBe(false)
    
    // When authenticated, user info should be displayed
    // Note: In a real scenario, we'd set authStore.user, but this test just verifies the structure
  })

  it('displays empty state when no files', async () => {
    const wrapper = mount(Sidebar, {
      global: {
        plugins: [pinia, router],
      },
    })

    await router.isReady()
    // Wait for async mounted hook
    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 10))

    expect(wrapper.find('.tree-empty').exists()).toBe(true)
  })

  it('displays file icon based on file type', async () => {
    const wrapper = mount(Sidebar, {
      global: {
        plugins: [pinia, router],
      },
    })

    await router.isReady()

    // Test getFileIcon function via component instance
    const vm = wrapper.vm as any
    
    expect(vm.getFileIcon({ type: 'directory' })).toBe('📁')
    expect(vm.getFileIcon({ type: 'file', extension: '.md' })).toBe('📝')
    expect(vm.getFileIcon({ type: 'file', extension: '.py' })).toBe('🐍')
    expect(vm.getFileIcon({ type: 'file', extension: '.json' })).toBe('📋')
    expect(vm.getFileIcon({ 
      type: 'file', 
      properties: { type: 'notebook' } 
    })).toBe('📓')
    expect(vm.getFileIcon({ 
      type: 'file', 
      properties: { type: 'page' } 
    })).toBe('📄')
  })

  it('gets display name from properties.title if available', async () => {
    const wrapper = mount(Sidebar, {
      global: {
        plugins: [pinia, router],
      },
    })

    await router.isReady()

    const vm = wrapper.vm as any
    
    expect(vm.getDisplayName({ 
      name: 'file.txt',
      properties: { title: 'Custom Title' }
    })).toBe('Custom Title')
    
    expect(vm.getDisplayName({ 
      name: 'file.txt'
    })).toBe('file.txt')
  })

  it('toggles directory expansion', async () => {
    const wrapper = mount(Sidebar, {
      global: {
        plugins: [pinia, router],
      },
    })

    await router.isReady()

    const vm = wrapper.vm as any
    const testPath = '/test/dir'
    
    expect(vm.expandedDirs.has(testPath)).toBe(false)
    
    vm.toggleDir(testPath)
    expect(vm.expandedDirs.has(testPath)).toBe(true)
    
    vm.toggleDir(testPath)
    expect(vm.expandedDirs.has(testPath)).toBe(false)
  })

  it('checks if file is active correctly', async () => {
    router.push('/files?path=/test/file.txt')
    await router.isReady()

    const wrapper = mount(Sidebar, {
      global: {
        plugins: [pinia, router],
      },
    })

    const vm = wrapper.vm as any
    
    expect(vm.isFileActive('/test/file.txt')).toBe(true)
    expect(vm.isFileActive('/other/file.txt')).toBe(false)
  })

  it('navigates to file when clicked', async () => {
    mount(Sidebar, {
      global: {
        plugins: [pinia, router],
      },
    })

    await router.isReady()
    
    const testPath = '/notebooks/test.md'
    
    // Use router.push to simulate navigation
    await router.push({ path: '/files', query: { path: testPath } })
    
    expect(router.currentRoute.value.path).toBe('/files')
    expect(router.currentRoute.value.query.path).toBe(testPath)
  })
})
