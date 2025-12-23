import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import MarkdownViewer from '@/components/markdown/MarkdownViewer.vue'

describe('MarkdownViewer Component', () => {
  it('renders basic markdown content', () => {
    const wrapper = mount(MarkdownViewer, {
      props: {
        content: '# Hello World\n\nThis is a **test**.',
      },
    })

    const html = wrapper.html()
    expect(html).toContain('<h1')
    expect(html).toContain('Hello World')
    expect(html).toContain('<strong>')
    expect(html).toContain('test')
  })

  it('renders empty string when content is empty', () => {
    const wrapper = mount(MarkdownViewer, {
      props: {
        content: '',
      },
    })

    const viewer = wrapper.find('.markdown-viewer')
    expect(viewer.exists()).toBe(true)
    expect(viewer.text()).toBe('')
  })

  it('renders code blocks correctly', () => {
    const wrapper = mount(MarkdownViewer, {
      props: {
        content: '```python\nprint("hello")\n```',
      },
    })

    const html = wrapper.html()
    expect(html).toContain('<pre>')
    expect(html).toContain('class="language-python"')
    expect(html).toContain('print')
  })

  it('renders inline code correctly', () => {
    const wrapper = mount(MarkdownViewer, {
      props: {
        content: 'Use `console.log()` to debug.',
      },
    })

    const html = wrapper.html()
    expect(html).toContain('<code>')
    expect(html).toContain('console.log')
  })

  it('renders lists correctly', () => {
    const wrapper = mount(MarkdownViewer, {
      props: {
        content: '- Item 1\n- Item 2\n- Item 3',
      },
    })

    const html = wrapper.html()
    expect(html).toContain('<ul>')
    expect(html).toContain('<li>')
    expect(html).toContain('Item 1')
    expect(html).toContain('Item 2')
  })

  it('renders links correctly', () => {
    const wrapper = mount(MarkdownViewer, {
      props: {
        content: '[GitHub](https://github.com)',
      },
    })

    const html = wrapper.html()
    expect(html).toContain('<a')
    expect(html).toContain('href="https://github.com"')
    expect(html).toContain('GitHub')
  })

  it('sanitizes dangerous HTML', () => {
    const wrapper = mount(MarkdownViewer, {
      props: {
        content: '<script>alert("xss")</script>',
      },
    })

    const html = wrapper.html()
    // DOMPurify should remove script tags
    expect(html).not.toContain('<script>')
    expect(html).not.toContain('alert')
  })

  it('accepts custom class prop', () => {
    const wrapper = mount(MarkdownViewer, {
      props: {
        content: 'Hello',
        class: 'custom-class',
      },
    })

    const viewer = wrapper.find('.markdown-viewer')
    expect(viewer.classes()).toContain('custom-class')
  })

  it('renders blockquotes correctly', () => {
    const wrapper = mount(MarkdownViewer, {
      props: {
        content: '> This is a quote',
      },
    })

    const html = wrapper.html()
    expect(html).toContain('<blockquote>')
    expect(html).toContain('This is a quote')
  })

  it('renders horizontal rules correctly', () => {
    const wrapper = mount(MarkdownViewer, {
      props: {
        content: 'Text before\n\n---\n\nText after',
      },
    })

    const html = wrapper.html()
    expect(html).toContain('<hr')
  })
})
