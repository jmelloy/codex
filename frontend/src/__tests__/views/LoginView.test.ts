import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createRouter, createWebHistory } from 'vue-router'
import { setActivePinia, createPinia } from 'pinia'
import LoginView from '../../views/LoginView.vue'

// Create a mock router for testing
const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: { template: 'Home' } },
    { path: '/login', component: LoginView },
    { path: '/register', component: { template: 'Register' } }
  ]
})

describe('LoginView', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
  })

  it('renders login form', () => {
    const wrapper = mount(LoginView, {
      global: {
        plugins: [router]
      }
    })
    
    expect(wrapper.find('h1').text()).toContain('Codex')
    expect(wrapper.find('.subtitle').text()).toContain('Laboratory Journal System')
    expect(wrapper.find('#username').exists()).toBe(true)
    expect(wrapper.find('#password').exists()).toBe(true)
  })

  it('displays username and password inputs', () => {
    const wrapper = mount(LoginView, {
      global: {
        plugins: [router]
      }
    })
    
    const usernameInput = wrapper.find('#username')
    const passwordInput = wrapper.find('#password')
    
    expect(usernameInput.attributes('type')).toBe('text')
    expect(passwordInput.attributes('type')).toBe('password')
    expect(usernameInput.attributes('required')).toBeDefined()
    expect(passwordInput.attributes('required')).toBeDefined()
  })

  it('displays login button', () => {
    const wrapper = mount(LoginView, {
      global: {
        plugins: [router]
      }
    })
    
    const button = wrapper.find('button[type="submit"]')
    expect(button.exists()).toBe(true)
    expect(button.text()).toBe('Login')
  })

  it('displays link to register page', () => {
    const wrapper = mount(LoginView, {
      global: {
        plugins: [router]
      }
    })
    
    const registerLink = wrapper.find('.register-link a')
    expect(registerLink.exists()).toBe(true)
    expect(registerLink.attributes('href')).toBe('/register')
  })

  it('binds username and password inputs to component state', async () => {
    const wrapper = mount(LoginView, {
      global: {
        plugins: [router]
      }
    })
    
    const usernameInput = wrapper.find('#username')
    const passwordInput = wrapper.find('#password')
    
    await usernameInput.setValue('testuser')
    await passwordInput.setValue('testpassword')
    
    expect(usernameInput.element.value).toBe('testuser')
    expect(passwordInput.element.value).toBe('testpassword')
  })

  it('shows loading state when loading', async () => {
    const wrapper = mount(LoginView, {
      global: {
        plugins: [router]
      }
    })
    
    // Access store via useAuthStore
    const { useAuthStore } = await import('../../stores/auth')
    const authStore = useAuthStore()
    authStore.loading = true
    
    await wrapper.vm.$nextTick()
    
    const button = wrapper.find('button[type="submit"]')
    // Button text should change when loading
    expect(button.text()).toContain('Logging in')
  })

  it('displays error message when auth store has error', async () => {
    const wrapper = mount(LoginView, {
      global: {
        plugins: [router]
      }
    })
    
    // Access store via useAuthStore
    const { useAuthStore } = await import('../../stores/auth')
    const authStore = useAuthStore()
    authStore.error = 'Invalid credentials'
    
    await wrapper.vm.$nextTick()
    
    expect(wrapper.find('.error').text()).toBe('Invalid credentials')
  })

  it('does not display error when no error exists', () => {
    const wrapper = mount(LoginView, {
      global: {
        plugins: [router]
      }
    })
    
    expect(wrapper.find('.error').exists()).toBe(false)
  })
})
