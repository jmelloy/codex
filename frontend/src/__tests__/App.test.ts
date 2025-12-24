import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import App from '../App.vue'

describe('App', () => {
  it('renders without crashing', () => {
    const wrapper = mount(App, {
      global: {
        stubs: {
          'router-view': true
        }
      }
    })
    expect(wrapper.exists()).toBe(true)
  })

  it('has router-view component', () => {
    const wrapper = mount(App, {
      global: {
        stubs: {
          'router-view': true
        }
      }
    })
    expect(wrapper.findComponent({ name: 'router-view' }).exists()).toBe(true)
  })
})
