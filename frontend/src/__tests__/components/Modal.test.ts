import { describe, it, expect, beforeEach, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import Modal from '../../components/Modal.vue'

describe('Modal', () => {
  let wrapper: any

  beforeEach(() => {
    // Create a target element for the teleport
    const el = document.createElement('div')
    el.id = 'modal-root'
    document.body.appendChild(el)
  })

  afterEach(() => {
    // Clean up
    if (wrapper) {
      wrapper.unmount()
    }
    const modalRoot = document.getElementById('modal-root')
    if (modalRoot) {
      document.body.removeChild(modalRoot)
    }
    // Clean up any teleported content
    const backdrop = document.querySelector('.modal-backdrop')
    if (backdrop) {
      backdrop.remove()
    }
  })

  it('renders when modelValue is true', () => {
    wrapper = mount(Modal, {
      props: {
        modelValue: true
      },
      attachTo: document.body
    })
    
    expect(document.querySelector('.modal-backdrop')).toBeTruthy()
  })

  it('does not render when modelValue is false', () => {
    wrapper = mount(Modal, {
      props: {
        modelValue: false
      },
      attachTo: document.body
    })
    
    expect(document.querySelector('.modal-backdrop')).toBeFalsy()
  })

  it('displays title when provided', () => {
    wrapper = mount(Modal, {
      props: {
        modelValue: true,
        title: 'Test Modal Title'
      },
      attachTo: document.body
    })
    
    const heading = document.querySelector('h3')
    expect(heading).toBeTruthy()
    expect(heading?.textContent).toBe('Test Modal Title')
  })

  it('does not display title when not provided', () => {
    wrapper = mount(Modal, {
      props: {
        modelValue: true
      },
      attachTo: document.body
    })
    
    const heading = document.querySelector('h3')
    expect(heading).toBeFalsy()
  })

  it('renders slot content', () => {
    wrapper = mount(Modal, {
      props: {
        modelValue: true
      },
      slots: {
        default: '<p>Modal content</p>'
      },
      attachTo: document.body
    })
    
    const modalContent = document.querySelector('.modal-content')
    expect(modalContent?.innerHTML).toContain('Modal content')
  })

  it('displays custom confirm text', () => {
    wrapper = mount(Modal, {
      props: {
        modelValue: true,
        confirmText: 'Save Changes'
      },
      attachTo: document.body
    })
    
    // Find button in the teleported content
    const buttons = Array.from(document.querySelectorAll('.modal-actions button'))
    const confirmButton = buttons.find((btn: any) => btn.textContent?.includes('Save Changes'))
    expect(confirmButton?.textContent).toBe('Save Changes')
  })

  it('displays custom cancel text', () => {
    wrapper = mount(Modal, {
      props: {
        modelValue: true,
        cancelText: 'Go Back'
      },
      attachTo: document.body
    })
    
    const buttons = document.querySelectorAll('button')
    expect(buttons[0]?.textContent).toBe('Go Back')
  })

  it('displays default confirm and cancel text', () => {
    wrapper = mount(Modal, {
      props: {
        modelValue: true
      },
      attachTo: document.body
    })
    
    const buttons = document.querySelectorAll('button')
    expect(buttons[0]?.textContent).toBe('Cancel')
    expect(buttons[1]?.textContent).toBe('Confirm')
  })

  it('hides actions when hideActions is true', () => {
    wrapper = mount(Modal, {
      props: {
        modelValue: true,
        hideActions: true
      },
      attachTo: document.body
    })
    
    const actions = document.querySelector('.modal-actions')
    expect(actions).toBeFalsy()
  })

  it('shows actions by default', () => {
    wrapper = mount(Modal, {
      props: {
        modelValue: true
      },
      attachTo: document.body
    })
    
    const actions = document.querySelector('.modal-actions')
    expect(actions).toBeTruthy()
  })

  it('emits update:modelValue and cancel when clicking outside modal', async () => {
    wrapper = mount(Modal, {
      props: {
        modelValue: true
      },
      attachTo: document.body
    })
    
    const backdrop = document.querySelector('.modal-backdrop') as HTMLElement
    backdrop.click()
    
    await wrapper.vm.$nextTick()
    
    expect(wrapper.emitted('update:modelValue')).toBeTruthy()
    expect(wrapper.emitted('update:modelValue')![0]).toEqual([false])
    expect(wrapper.emitted('cancel')).toBeTruthy()
  })

  it('emits update:modelValue and cancel when clicking cancel button', async () => {
    wrapper = mount(Modal, {
      props: {
        modelValue: true
      },
      attachTo: document.body
    })
    
    const buttons = document.querySelectorAll('button')
    ;(buttons[0] as HTMLElement).click()
    
    await wrapper.vm.$nextTick()
    
    expect(wrapper.emitted('update:modelValue')).toBeTruthy()
    expect(wrapper.emitted('update:modelValue')![0]).toEqual([false])
    expect(wrapper.emitted('cancel')).toBeTruthy()
  })

  it('emits confirm when clicking confirm button', async () => {
    wrapper = mount(Modal, {
      props: {
        modelValue: true
      },
      attachTo: document.body
    })
    
    // Find confirm button in the teleported content
    const buttons = Array.from(document.querySelectorAll('.modal-actions button'))
    const confirmButton = buttons.find((btn: any) => btn.textContent?.includes('Confirm')) as HTMLElement
    if (confirmButton) {
      confirmButton.click()
      await wrapper.vm.$nextTick()
    }
    
    expect(wrapper.emitted('confirm')).toBeTruthy()
  })

  it('does not emit update:modelValue when clicking confirm button', async () => {
    wrapper = mount(Modal, {
      props: {
        modelValue: true
      },
      attachTo: document.body
    })
    
    // Find confirm button in the teleported content
    const buttons = Array.from(document.querySelectorAll('.modal-actions button'))
    const confirmButton = buttons.find((btn: any) => btn.textContent?.includes('Confirm')) as HTMLElement
    if (confirmButton) {
      confirmButton.click()
      await wrapper.vm.$nextTick()
    }
    
    // Should only emit confirm, not update:modelValue
    // Parent component should close modal after handling confirm
    expect(wrapper.emitted('confirm')).toBeTruthy()
    expect(wrapper.emitted('update:modelValue')).toBeFalsy()
  })

  it('does not close modal when clicking inside modal content', async () => {
    wrapper = mount(Modal, {
      props: {
        modelValue: true
      },
      attachTo: document.body
    })
    
    const modalContent = document.querySelector('.modal-content') as HTMLElement
    modalContent.click()
    
    await wrapper.vm.$nextTick()
    
    // Should not emit update:modelValue when clicking inside content
    expect(wrapper.emitted('update:modelValue')).toBeFalsy()
  })
})
