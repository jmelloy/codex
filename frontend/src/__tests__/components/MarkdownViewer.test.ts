import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import MarkdownViewer from '../../components/MarkdownViewer.vue'

describe('MarkdownViewer', () => {
  beforeEach(() => {
    // Create a fresh pinia instance for each test
    setActivePinia(createPinia())
  })

  it('renders markdown content properly', () => {
    const markdownContent = '# Hello World\n\nThis is a **test**.'
    const wrapper = mount(MarkdownViewer, { 
      props: { 
        content: markdownContent,
        showToolbar: false 
      } 
    })
    
    const html = wrapper.find('.markdown-content').html()
    expect(html).toContain('<h1')
    expect(html).toContain('Hello World')
    expect(html).toContain('<strong>')
    expect(html).toContain('test')
  })

  it('displays empty content message when no content provided', () => {
    const wrapper = mount(MarkdownViewer, { 
      props: { 
        content: '',
        showToolbar: false 
      } 
    })
    
    expect(wrapper.find('.markdown-content').text()).toContain('No content to display')
  })

  it('renders code blocks with syntax highlighting', () => {
    const markdownWithCode = '```javascript\nconst x = 42;\n```'
    const wrapper = mount(MarkdownViewer, { 
      props: { 
        content: markdownWithCode,
        showToolbar: false 
      } 
    })
    
    const html = wrapper.find('.markdown-content').html()
    expect(html).toContain('<pre>')
    expect(html).toContain('language-javascript')
    expect(html).toContain('const x')
  })

  it('shows toolbar when showToolbar is true', () => {
    const wrapper = mount(MarkdownViewer, { 
      props: { 
        content: '# Test',
        showToolbar: true 
      } 
    })
    
    expect(wrapper.find('.markdown-toolbar').exists()).toBe(true)
  })

  it('hides toolbar when showToolbar is false', () => {
    const wrapper = mount(MarkdownViewer, { 
      props: { 
        content: '# Test',
        showToolbar: false 
      } 
    })
    
    expect(wrapper.find('.markdown-toolbar').exists()).toBe(false)
  })

  it('emits copy event when copy button is clicked', async () => {
    // Mock clipboard API
    const mockWriteText = async () => {}
    Object.defineProperty(navigator, 'clipboard', {
      value: {
        writeText: mockWriteText
      },
      writable: true,
      configurable: true
    })

    const wrapper = mount(MarkdownViewer, { 
      props: { 
        content: 'Test content',
        showToolbar: true 
      } 
    })
    
    const copyButton = wrapper.find('.btn-copy')
    await copyButton.trigger('click')
    
    expect(wrapper.emitted('copy')).toBeTruthy()
  })
})
