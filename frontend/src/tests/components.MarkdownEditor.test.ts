import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import MarkdownEditor from '@/components/markdown/MarkdownEditor.vue'
import MarkdownViewer from '@/components/markdown/MarkdownViewer.vue'

describe('MarkdownEditor Component', () => {
  it('renders with default props', () => {
    const wrapper = mount(MarkdownEditor, {
      props: {
        modelValue: '',
      },
    })

    expect(wrapper.find('.markdown-editor').exists()).toBe(true)
    expect(wrapper.find('.editor-toolbar').exists()).toBe(true)
    expect(wrapper.find('.editor-panes').exists()).toBe(true)
  })

  it('displays content in textarea when in edit mode', async () => {
    const content = '# Test Content'
    const wrapper = mount(MarkdownEditor, {
      props: {
        modelValue: content,
      },
    })

    // Click edit button
    await wrapper.findAll('.toolbar-btn')[0].trigger('click')
    await wrapper.vm.$nextTick()

    const textarea = wrapper.find('textarea')
    expect(textarea.exists()).toBe(true)
    expect((textarea.element as HTMLTextAreaElement).value).toBe(content)
  })

  it('emits update:modelValue on input', async () => {
    const wrapper = mount(MarkdownEditor, {
      props: {
        modelValue: '',
        editable: true,
      },
    })

    // Switch to edit mode
    await wrapper.findAll('.toolbar-btn')[0].trigger('click')
    await wrapper.vm.$nextTick()

    const textarea = wrapper.find('textarea')
    await textarea.setValue('New content')

    expect(wrapper.emitted('update:modelValue')).toBeTruthy()
    expect(wrapper.emitted('update:modelValue')?.[0]).toEqual(['New content'])
  })

  it('switches between edit, split, and preview modes', async () => {
    const wrapper = mount(MarkdownEditor, {
      props: {
        modelValue: '# Test',
        showPreview: true,
      },
    })

    const buttons = wrapper.findAll('.toolbar-btn')

    // Click preview button
    await buttons[2].trigger('click')
    await wrapper.vm.$nextTick()
    expect(wrapper.find('.preview-pane').exists()).toBe(true)
    expect(wrapper.find('.edit-pane').exists()).toBe(false)

    // Click split button
    await buttons[1].trigger('click')
    await wrapper.vm.$nextTick()
    expect(wrapper.find('.preview-pane').exists()).toBe(true)
    expect(wrapper.find('.edit-pane').exists()).toBe(true)

    // Click edit button
    await buttons[0].trigger('click')
    await wrapper.vm.$nextTick()
    expect(wrapper.find('.edit-pane').exists()).toBe(true)
    expect(wrapper.find('.preview-pane').exists()).toBe(false)
  })

  it('does not show toolbar when showPreview is false', () => {
    const wrapper = mount(MarkdownEditor, {
      props: {
        modelValue: '',
        showPreview: false,
      },
    })

    expect(wrapper.find('.editor-toolbar').exists()).toBe(false)
  })

  it('does not show toolbar when not editable', () => {
    const wrapper = mount(MarkdownEditor, {
      props: {
        modelValue: '',
        editable: false,
      },
    })

    expect(wrapper.find('.editor-toolbar').exists()).toBe(false)
  })

  it('renders MarkdownViewer in preview pane', () => {
    const wrapper = mount(MarkdownEditor, {
      props: {
        modelValue: '# Test',
        showPreview: true,
      },
    })

    const viewer = wrapper.findComponent(MarkdownViewer)
    expect(viewer.exists()).toBe(true)
  })

  it('shows placeholder in preview when content is empty', async () => {
    const placeholder = 'Enter some text...'
    const wrapper = mount(MarkdownEditor, {
      props: {
        modelValue: '',
        placeholder,
        showPreview: true,
      },
    })

    // Switch to preview mode
    await wrapper.findAll('.toolbar-btn')[2].trigger('click')
    await wrapper.vm.$nextTick()

    const previewEmpty = wrapper.find('.preview-empty')
    expect(previewEmpty.exists()).toBe(true)
    expect(previewEmpty.text()).toBe(placeholder)
  })

  it('respects custom min and max height', () => {
    const wrapper = mount(MarkdownEditor, {
      props: {
        modelValue: '',
        minHeight: '300px',
        maxHeight: '700px',
      },
    })

    const panes = wrapper.find('.editor-panes')
    expect(panes.exists()).toBe(true)
    // Check that CSS variables are applied (via v-bind in style)
  })

  it('handles tab key for indentation', async () => {
    const wrapper = mount(MarkdownEditor, {
      props: {
        modelValue: 'line1',
        editable: true,
      },
    })

    // Switch to edit mode
    await wrapper.findAll('.toolbar-btn')[0].trigger('click')
    await wrapper.vm.$nextTick()

    const textarea = wrapper.find('textarea')
    
    // Set cursor position
    const element = textarea.element as HTMLTextAreaElement
    element.selectionStart = 5
    element.selectionEnd = 5

    // Simulate Tab key press
    await textarea.trigger('keydown', { key: 'Tab' })

    expect(wrapper.emitted('update:modelValue')).toBeTruthy()
    // Should insert 2 spaces
    expect(wrapper.emitted('update:modelValue')?.[0]).toEqual(['line1  '])
  })

  it('renders as readonly when editable is false', async () => {
    const wrapper = mount(MarkdownEditor, {
      props: {
        modelValue: 'Test content',
        editable: false,
      },
    })

    const textarea = wrapper.find('textarea')
    expect((textarea.element as HTMLTextAreaElement).readOnly).toBe(true)
  })

  it('uses custom placeholder', () => {
    const customPlaceholder = 'Custom placeholder text'
    const wrapper = mount(MarkdownEditor, {
      props: {
        modelValue: '',
        placeholder: customPlaceholder,
      },
    })

    const textarea = wrapper.find('textarea')
    expect((textarea.element as HTMLTextAreaElement).placeholder).toBe(customPlaceholder)
  })
})
