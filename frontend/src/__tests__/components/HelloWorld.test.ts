import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import HelloWorld from '../../components/HelloWorld.vue'

describe('HelloWorld', () => {
  it('renders properly', () => {
    const wrapper = mount(HelloWorld, { props: { msg: 'Hello Vitest' } })
    expect(wrapper.text()).toContain('Hello Vitest')
  })

  it('increments count when button is clicked', async () => {
    const wrapper = mount(HelloWorld, { props: { msg: 'Test' } })
    const button = wrapper.find('button')
    
    expect(button.text()).toContain('count is 0')
    
    await button.trigger('click')
    expect(button.text()).toContain('count is 1')
    
    await button.trigger('click')
    expect(button.text()).toContain('count is 2')
  })

  it('passes msg prop to component', () => {
    const testMessage = 'Test Message'
    const wrapper = mount(HelloWorld, { props: { msg: testMessage } })
    expect(wrapper.find('h1').text()).toBe(testMessage)
  })
})
