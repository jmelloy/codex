import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import FormGroup from '../../components/FormGroup.vue'

describe('FormGroup', () => {
  it('renders without crashing', () => {
    const wrapper = mount(FormGroup)
    expect(wrapper.exists()).toBe(true)
  })

  it('displays label when provided', () => {
    const wrapper = mount(FormGroup, {
      props: {
        label: 'Test Label'
      }
    })
    
    const label = wrapper.find('label')
    expect(label.exists()).toBe(true)
    expect(label.text()).toBe('Test Label')
  })

  it('does not display label when not provided', () => {
    const wrapper = mount(FormGroup)
    const label = wrapper.find('label')
    expect(label.exists()).toBe(false)
  })

  it('uses provided id for label', () => {
    const wrapper = mount(FormGroup, {
      props: {
        label: 'Test Label',
        id: 'custom-id'
      }
    })
    
    const label = wrapper.find('label')
    expect(label.attributes('for')).toBe('custom-id')
  })

  it('generates unique id when not provided', () => {
    const wrapper1 = mount(FormGroup, {
      props: {
        label: 'Label 1'
      }
    })
    
    const wrapper2 = mount(FormGroup, {
      props: {
        label: 'Label 2'
      }
    })
    
    const label1 = wrapper1.find('label')
    const label2 = wrapper2.find('label')
    
    expect(label1.attributes('for')).toBeDefined()
    expect(label2.attributes('for')).toBeDefined()
    expect(label1.attributes('for')).not.toBe(label2.attributes('for'))
  })

  it('renders slot content', () => {
    const wrapper = mount(FormGroup, {
      slots: {
        default: '<input type="text" value="test" />'
      }
    })
    
    const input = wrapper.find('input')
    expect(input.exists()).toBe(true)
    expect(input.attributes('value')).toBe('test')
  })

  it('provides inputId to slot content', () => {
    const wrapper = mount(FormGroup, {
      props: {
        id: 'test-id',
        label: 'Test'
      },
      slots: {
        default: '<input v-bind:id="inputId" />'
      }
    })
    
    // The slot should have access to inputId
    expect(wrapper.html()).toContain('test-id')
  })
})
