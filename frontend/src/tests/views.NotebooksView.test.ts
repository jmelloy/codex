import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createRouter, createMemoryHistory } from 'vue-router'
import NotebooksView from '@/views/NotebooksView.vue'
import { useNotebooksStore } from '@/stores/notebooks'

// Mock the API module
vi.mock('@/api', () => ({
  notebooksApi: {
    list: vi.fn().mockResolvedValue([]),
    get: vi.fn(),
    create: vi.fn(),
  },
}))

// Create a mock router
const createMockRouter = () => {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/notebooks', component: NotebooksView },
      { 
        path: '/notebooks/:id', 
        component: { template: '<div>Notebook Detail</div>' } 
      },
    ],
  })
}

describe('NotebooksView', () => {
  let router: ReturnType<typeof createMockRouter>
  let pinia: ReturnType<typeof createPinia>

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
    router = createMockRouter()
    vi.clearAllMocks()
  })

  it('renders page header with title', async () => {
    const wrapper = mount(NotebooksView, {
      global: {
        plugins: [pinia, router],
      },
    })

    await router.isReady()

    expect(wrapper.find('.page-header h1').text()).toBe('Notebooks')
    expect(wrapper.find('.btn-primary').text()).toBe('+ New Notebook')
  })

  it('displays loading state', async () => {
    const wrapper = mount(NotebooksView, {
      global: {
        plugins: [pinia, router],
      },
    })

    const store = useNotebooksStore()
    store.loading = true

    await wrapper.vm.$nextTick()

    expect(wrapper.find('.loading').exists()).toBe(true)
    expect(wrapper.find('.loading').text()).toBe('Loading notebooks...')
  })

  it('displays error state', async () => {
    const wrapper = mount(NotebooksView, {
      global: {
        plugins: [pinia, router],
      },
    })

    const store = useNotebooksStore()
    store.loading = false
    store.error = 'Failed to load notebooks'

    await wrapper.vm.$nextTick()

    expect(wrapper.find('.error').exists()).toBe(true)
    expect(wrapper.find('.error').text()).toBe('Failed to load notebooks')
  })

  it('displays empty state when no notebooks', async () => {
    const wrapper = mount(NotebooksView, {
      global: {
        plugins: [pinia, router],
      },
    })

    const store = useNotebooksStore()
    store.loading = false
    store.error = null

    await wrapper.vm.$nextTick()

    expect(wrapper.find('.empty').exists()).toBe(true)
    expect(wrapper.text()).toContain('No notebooks yet')
  })

  it('displays notebooks grid when notebooks exist', async () => {
    const wrapper = mount(NotebooksView, {
      global: {
        plugins: [pinia, router],
      },
    })

    const store = useNotebooksStore()
    store.loading = false
    store.error = null
    store.notebooks.set('1', {
      id: '1',
      title: 'Test Notebook',
      description: 'A test notebook',
      tags: ['test', 'sample'],
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
      settings: {},
    })

    await wrapper.vm.$nextTick()

    expect(wrapper.find('.notebooks-grid').exists()).toBe(true)
    expect(wrapper.find('.notebook-card h3').text()).toBe('Test Notebook')
    expect(wrapper.find('.description').text()).toBe('A test notebook')
    expect(wrapper.findAll('.tag')).toHaveLength(2)
  })

  it('opens modal when create button is clicked', async () => {
    const wrapper = mount(NotebooksView, {
      global: {
        plugins: [pinia, router],
      },
    })

    await router.isReady()

    expect(wrapper.find('.modal-overlay').exists()).toBe(false)

    await wrapper.find('.btn-primary').trigger('click')
    await wrapper.vm.$nextTick()

    expect(wrapper.find('.modal-overlay').exists()).toBe(true)
    expect(wrapper.find('.modal h2').text()).toBe('Create New Notebook')
  })

  it('closes modal when closeModal is called', async () => {
    const wrapper = mount(NotebooksView, {
      global: {
        plugins: [pinia, router],
      },
    })

    await router.isReady()

    // Open modal
    await wrapper.find('.btn-primary').trigger('click')
    await wrapper.vm.$nextTick()

    expect(wrapper.find('.modal-overlay').exists()).toBe(true)

    // Access component instance to call closeModal
    const vm = wrapper.vm as any
    vm.closeModal()
    await wrapper.vm.$nextTick()

    expect(wrapper.find('.modal-overlay').exists()).toBe(false)
  })

  it('creates notebook and navigates on successful submission', async () => {
    const mockNotebook = {
      id: 'new-id',
      title: 'New Notebook',
      description: 'New description',
      tags: ['tag1'],
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
      settings: {},
    }

    const store = useNotebooksStore()
    vi.spyOn(store, 'createNotebook').mockResolvedValue(mockNotebook)

    const wrapper = mount(NotebooksView, {
      global: {
        plugins: [pinia, router],
      },
    })

    await router.isReady()

    // Open modal
    await wrapper.find('.btn-primary').trigger('click')
    await wrapper.vm.$nextTick()

    // Set form values
    const vm = wrapper.vm as any
    vm.newNotebook = {
      title: 'New Notebook',
      description: 'New description',
      tags: 'tag1, tag2',
    }

    // Submit form
    await vm.handleCreateNotebook()
    await flushPromises()

    expect(store.createNotebook).toHaveBeenCalledWith(
      'New Notebook',
      'New description',
      ['tag1', 'tag2']
    )

    // Check navigation
    expect(router.currentRoute.value.path).toBe('/notebooks/new-id')
  })

  it('does not create notebook if title is empty', async () => {
    const store = useNotebooksStore()
    const createSpy = vi.spyOn(store, 'createNotebook')

    const wrapper = mount(NotebooksView, {
      global: {
        plugins: [pinia, router],
      },
    })

    await router.isReady()

    const vm = wrapper.vm as any
    vm.newNotebook = {
      title: '   ', // Empty/whitespace title
      description: 'Description',
      tags: '',
    }

    await vm.handleCreateNotebook()
    await flushPromises()

    expect(createSpy).not.toHaveBeenCalled()
  })

  it('parses tags correctly from comma-separated string', async () => {
    const mockNotebook = {
      id: 'new-id',
      title: 'New Notebook',
      description: '',
      tags: [],
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
      settings: {},
    }

    const store = useNotebooksStore()
    vi.spyOn(store, 'createNotebook').mockResolvedValue(mockNotebook)

    const wrapper = mount(NotebooksView, {
      global: {
        plugins: [pinia, router],
      },
    })

    const vm = wrapper.vm as any
    vm.newNotebook = {
      title: 'Test',
      description: '',
      tags: 'tag1, tag2,  tag3  , , tag4',
    }

    await vm.handleCreateNotebook()
    await flushPromises()

    expect(store.createNotebook).toHaveBeenCalledWith(
      'Test',
      '',
      ['tag1', 'tag2', 'tag3', 'tag4']
    )
  })
})
