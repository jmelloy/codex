import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import Modal from '../../components/Modal.vue'

describe('Modal', () => {
  it('renders when modelValue is true', () => {
    const wrapper = mount(Modal, {
      props: {
        modelValue: true
      }
    })
    
    expect(wrapper.find('.modal').exists()).toBe(true)
  })

  it('does not render when modelValue is false', () => {
    const wrapper = mount(Modal, {
      props: {
        modelValue: false
      }
    })
    
    expect(wrapper.find('.modal').exists()).toBe(false)
  })

  it('displays title when provided', () => {
    const wrapper = mount(Modal, {
      props: {
        modelValue: true,
        title: 'Test Modal Title'
      }
    })
    
    const heading = wrapper.find('h3')
    expect(heading.exists()).toBe(true)
    expect(heading.text()).toBe('Test Modal Title')
  })

  it('does not display title when not provided', () => {
    const wrapper = mount(Modal, {
      props: {
        modelValue: true
      }
    })
    
    expect(wrapper.find('h3').exists()).toBe(false)
  })

  it('renders slot content', () => {
    const wrapper = mount(Modal, {
      props: {
        modelValue: true
      },
      slots: {
        default: '<p>Modal content</p>'
      }
    })
    
    expect(wrapper.html()).toContain('Modal content')
  })

  it('displays custom confirm text', () => {
    const wrapper = mount(Modal, {
      props: {
        modelValue: true,
        confirmText: 'Save Changes'
      }
    })
    
    const confirmButton = wrapper.find('.btn-primary')
    expect(confirmButton.text()).toBe('Save Changes')
  })

  it('displays custom cancel text', () => {
    const wrapper = mount(Modal, {
      props: {
        modelValue: true,
        cancelText: 'Go Back'
      }
    })
    
    const buttons = wrapper.findAll('button')
    expect(buttons[0].text()).toBe('Go Back')
  })

  it('displays default confirm and cancel text', () => {
    const wrapper = mount(Modal, {
      props: {
        modelValue: true
      }
    })
    
    const buttons = wrapper.findAll('button')
    expect(buttons[0].text()).toBe('Cancel')
    expect(buttons[1].text()).toBe('Confirm')
  })

  it('hides actions when hideActions is true', () => {
    const wrapper = mount(Modal, {
      props: {
        modelValue: true,
        hideActions: true
      }
    })
    
    expect(wrapper.find('.modal-actions').exists()).toBe(false)
  })

  it('shows actions by default', () => {
    const wrapper = mount(Modal, {
      props: {
        modelValue: true
      }
    })
    
    expect(wrapper.find('.modal-actions').exists()).toBe(true)
  })

  it('emits update:modelValue and cancel when clicking outside modal', async () => {
    const wrapper = mount(Modal, {
      props: {
        modelValue: true
      }
    })
    
    await wrapper.find('.modal').trigger('click')
    
    expect(wrapper.emitted('update:modelValue')).toBeTruthy()
    expect(wrapper.emitted('update:modelValue')![0]).toEqual([false])
    expect(wrapper.emitted('cancel')).toBeTruthy()
  })

  it('emits update:modelValue and cancel when clicking cancel button', async () => {
    const wrapper = mount(Modal, {
      props: {
        modelValue: true
      }
    })
    
    const buttons = wrapper.findAll('button')
    await buttons[0].trigger('click')
    
    expect(wrapper.emitted('update:modelValue')).toBeTruthy()
    expect(wrapper.emitted('update:modelValue')![0]).toEqual([false])
    expect(wrapper.emitted('cancel')).toBeTruthy()
  })

  it('emits confirm when clicking confirm button', async () => {
    const wrapper = mount(Modal, {
      props: {
        modelValue: true
      }
    })
    
    const confirmButton = wrapper.find('.btn-primary')
    await confirmButton.trigger('click')
    
    expect(wrapper.emitted('confirm')).toBeTruthy()
  })

  it('does not emit update:modelValue when clicking confirm button', async () => {
    const wrapper = mount(Modal, {
      props: {
        modelValue: true
      }
    })
    
    const confirmButton = wrapper.find('.btn-primary')
    await confirmButton.trigger('click')
    
    // Should only emit confirm, not update:modelValue
    // Parent component should close modal after handling confirm
    expect(wrapper.emitted('confirm')).toBeTruthy()
    expect(wrapper.emitted('update:modelValue')).toBeFalsy()
  })

  it('does not close modal when clicking inside modal content', async () => {
    const wrapper = mount(Modal, {
      props: {
        modelValue: true
      }
    })
    
    await wrapper.find('.modal-content').trigger('click')
    
    // Should not emit update:modelValue when clicking inside content
    expect(wrapper.emitted('update:modelValue')).toBeFalsy()
  })
})
