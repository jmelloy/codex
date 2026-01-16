import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import FilePropertiesPanel from '../../components/FilePropertiesPanel.vue'

// Mock file data
const mockFile = {
  id: 1,
  path: '/test/path',
  filename: 'test-file.md',
  title: 'Test File',
  description: 'Test description',
  file_type: 'markdown',
  size: 1024,
  created_at: '2024-01-15T12:00:00Z',
  updated_at: '2024-01-16T12:00:00Z',
  frontmatter: {
    tags: ['test', 'example']
  },
  content: '# Test Content'
}

describe('FilePropertiesPanel', () => {
  it('renders without crashing', () => {
    const wrapper = mount(FilePropertiesPanel, {
      props: {
        file: null
      }
    })
    expect(wrapper.exists()).toBe(true)
  })

  it('displays empty state when no file is provided', () => {
    const wrapper = mount(FilePropertiesPanel, {
      props: {
        file: null
      }
    })
    
    expect(wrapper.find('.empty-state').exists()).toBe(true)
    expect(wrapper.text()).toContain('No file selected')
  })

  it('displays file properties when file is provided', () => {
    const wrapper = mount(FilePropertiesPanel, {
      props: {
        file: mockFile
      }
    })
    
    expect(wrapper.find('.panel-content').exists()).toBe(true)
    expect(wrapper.find('.empty-state').exists()).toBe(false)
  })

  it('displays file title in input', () => {
    const wrapper = mount(FilePropertiesPanel, {
      props: {
        file: mockFile
      }
    })
    
    const titleInput = wrapper.find('.property-input')
    expect(titleInput.element.value).toBe('Test File')
  })

  it('displays file description in textarea', () => {
    const wrapper = mount(FilePropertiesPanel, {
      props: {
        file: mockFile
      }
    })
    
    const descriptionTextarea = wrapper.find('.property-textarea')
    expect(descriptionTextarea.element.value).toBe('Test description')
  })

  it('displays file path', () => {
    const wrapper = mount(FilePropertiesPanel, {
      props: {
        file: mockFile
      }
    })
    
    const html = wrapper.html()
    expect(html).toContain('/test/path')
  })

  it('displays filename', () => {
    const wrapper = mount(FilePropertiesPanel, {
      props: {
        file: mockFile
      }
    })
    
    expect(wrapper.text()).toContain('test-file.md')
  })

  it('displays file type', () => {
    const wrapper = mount(FilePropertiesPanel, {
      props: {
        file: mockFile
      }
    })
    
    expect(wrapper.text()).toContain('markdown')
  })

  it('formats file size correctly', () => {
    const wrapper = mount(FilePropertiesPanel, {
      props: {
        file: mockFile
      }
    })
    
    expect(wrapper.text()).toContain('1 KB')
  })

  it('formats file size for bytes', () => {
    const smallFile = { ...mockFile, size: 500 }
    const wrapper = mount(FilePropertiesPanel, {
      props: {
        file: smallFile
      }
    })
    
    expect(wrapper.text()).toContain('500 B')
  })

  it('formats file size for megabytes', () => {
    const largeFile = { ...mockFile, size: 5242880 } // 5 MB
    const wrapper = mount(FilePropertiesPanel, {
      props: {
        file: largeFile
      }
    })
    
    expect(wrapper.text()).toContain('5 MB')
  })

  it('displays created date', () => {
    const wrapper = mount(FilePropertiesPanel, {
      props: {
        file: mockFile
      }
    })
    
    expect(wrapper.text()).toContain('Created')
    // The date format may vary by locale, just check it exists
    expect(wrapper.text()).toMatch(/Jan|January/)
  })

  it('displays updated date', () => {
    const wrapper = mount(FilePropertiesPanel, {
      props: {
        file: mockFile
      }
    })
    
    expect(wrapper.text()).toContain('Modified')
    expect(wrapper.text()).toMatch(/Jan|January/)
  })

  it('displays tags when present', () => {
    const wrapper = mount(FilePropertiesPanel, {
      props: {
        file: mockFile
      }
    })
    
    expect(wrapper.text()).toContain('test')
    expect(wrapper.text()).toContain('example')
  })

  it('does not display tags section when no tags', () => {
    const fileWithoutTags = { ...mockFile, frontmatter: {} }
    const wrapper = mount(FilePropertiesPanel, {
      props: {
        file: fileWithoutTags
      }
    })
    
    expect(wrapper.findAll('.tag').length).toBe(0)
  })

  it('emits close event when close button clicked', async () => {
    const wrapper = mount(FilePropertiesPanel, {
      props: {
        file: mockFile
      }
    })
    
    const closeButton = wrapper.find('.btn-close')
    await closeButton.trigger('click')
    
    expect(wrapper.emitted('close')).toBeTruthy()
  })

  it('emits updateTitle when title is changed and blurred', async () => {
    const wrapper = mount(FilePropertiesPanel, {
      props: {
        file: mockFile
      }
    })
    
    const titleInput = wrapper.find('.property-input')
    await titleInput.setValue('New Title')
    await titleInput.trigger('blur')
    
    expect(wrapper.emitted('updateTitle')).toBeTruthy()
    expect(wrapper.emitted('updateTitle')![0]).toEqual(['New Title'])
  })

  it('emits updateTitle when title is changed and enter is pressed', async () => {
    const wrapper = mount(FilePropertiesPanel, {
      props: {
        file: mockFile
      }
    })
    
    const titleInput = wrapper.find('.property-input')
    await titleInput.setValue('New Title')
    await titleInput.trigger('keyup.enter')
    
    expect(wrapper.emitted('updateTitle')).toBeTruthy()
    expect(wrapper.emitted('updateTitle')![0]).toEqual(['New Title'])
  })

  it('emits updateDescription when description is changed and blurred', async () => {
    const wrapper = mount(FilePropertiesPanel, {
      props: {
        file: mockFile
      }
    })
    
    const descriptionTextarea = wrapper.find('.property-textarea')
    await descriptionTextarea.setValue('New description')
    await descriptionTextarea.trigger('blur')
    
    expect(wrapper.emitted('updateDescription')).toBeTruthy()
    expect(wrapper.emitted('updateDescription')![0]).toEqual(['New description'])
  })

  it('does not emit updateTitle if value unchanged', async () => {
    const wrapper = mount(FilePropertiesPanel, {
      props: {
        file: mockFile
      }
    })
    
    const titleInput = wrapper.find('.property-input')
    // Keep the same value
    await titleInput.setValue('Test File')
    await titleInput.trigger('blur')
    
    expect(wrapper.emitted('updateTitle')).toBeFalsy()
  })

  it('displays delete button', () => {
    const wrapper = mount(FilePropertiesPanel, {
      props: {
        file: mockFile
      }
    })
    
    const deleteButton = wrapper.find('.btn-delete')
    expect(deleteButton.exists()).toBe(true)
    expect(deleteButton.text()).toContain('Delete')
  })

  it('emits delete event when delete is confirmed', async () => {
    // Mock window.confirm to return true
    window.confirm = vi.fn(() => true)
    
    const wrapper = mount(FilePropertiesPanel, {
      props: {
        file: mockFile
      }
    })
    
    const deleteButton = wrapper.find('.btn-delete')
    await deleteButton.trigger('click')
    
    expect(window.confirm).toHaveBeenCalled()
    expect(wrapper.emitted('delete')).toBeTruthy()
  })

  it('does not emit delete event when delete is cancelled', async () => {
    // Mock window.confirm to return false
    window.confirm = vi.fn(() => false)
    
    const wrapper = mount(FilePropertiesPanel, {
      props: {
        file: mockFile
      }
    })
    
    const deleteButton = wrapper.find('.btn-delete')
    await deleteButton.trigger('click')
    
    expect(window.confirm).toHaveBeenCalled()
    expect(wrapper.emitted('delete')).toBeFalsy()
  })

  it('updates editable fields when file prop changes', async () => {
    const wrapper = mount(FilePropertiesPanel, {
      props: {
        file: mockFile
      }
    })
    
    const newFile = { ...mockFile, title: 'Updated Title', description: 'Updated description' }
    await wrapper.setProps({ file: newFile })
    
    const titleInput = wrapper.find('.property-input')
    const descriptionTextarea = wrapper.find('.property-textarea')
    
    expect(titleInput.element.value).toBe('Updated Title')
    expect(descriptionTextarea.element.value).toBe('Updated description')
  })

  it('handles file with no title gracefully', () => {
    const fileWithoutTitle = { ...mockFile, title: null }
    const wrapper = mount(FilePropertiesPanel, {
      props: {
        file: fileWithoutTitle
      }
    })
    
    const titleInput = wrapper.find('.property-input')
    expect(titleInput.element.value).toBe('')
  })

  it('handles file with no description gracefully', () => {
    const fileWithoutDescription = { ...mockFile, description: null }
    const wrapper = mount(FilePropertiesPanel, {
      props: {
        file: fileWithoutDescription
      }
    })
    
    const descriptionTextarea = wrapper.find('.property-textarea')
    expect(descriptionTextarea.element.value).toBe('')
  })
})
