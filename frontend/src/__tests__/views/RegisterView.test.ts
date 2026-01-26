import { describe, it, expect, beforeEach } from "vitest"
import { mount } from "@vue/test-utils"
import { createRouter, createWebHistory } from "vue-router"
import { setActivePinia, createPinia } from "pinia"
import RegisterView from "../../views/RegisterView.vue"

// Create a mock router for testing
const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", component: { template: "Home" } },
    { path: "/login", component: { template: "Login" } },
    { path: "/register", component: RegisterView },
  ],
})

describe("RegisterView", () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
  })

  it("renders registration form", () => {
    const wrapper = mount(RegisterView, {
      global: {
        plugins: [router],
      },
    })

    expect(wrapper.find("h1").text()).toBe("Register")
    expect(wrapper.find("#username").exists()).toBe(true)
    expect(wrapper.find("#email").exists()).toBe(true)
    expect(wrapper.find("#password").exists()).toBe(true)
    expect(wrapper.find("#confirmPassword").exists()).toBe(true)
  })

  it("displays all required input fields", () => {
    const wrapper = mount(RegisterView, {
      global: {
        plugins: [router],
      },
    })

    const usernameInput = wrapper.find("#username")
    const emailInput = wrapper.find("#email")
    const passwordInput = wrapper.find("#password")
    const confirmPasswordInput = wrapper.find("#confirmPassword")

    expect(usernameInput.attributes("required")).toBeDefined()
    expect(emailInput.attributes("required")).toBeDefined()
    expect(passwordInput.attributes("required")).toBeDefined()
    expect(confirmPasswordInput.attributes("required")).toBeDefined()
  })

  it("displays register button", () => {
    const wrapper = mount(RegisterView, {
      global: {
        plugins: [router],
      },
    })

    const button = wrapper.find('button[type="submit"]')
    expect(button.exists()).toBe(true)
    expect(button.text()).toBe("Register")
  })

  it("displays link to login page", () => {
    const wrapper = mount(RegisterView, {
      global: {
        plugins: [router],
      },
    })

    const loginLink = wrapper.find(".login-link a")
    expect(loginLink.exists()).toBe(true)
    expect(loginLink.attributes("href")).toBe("/login")
  })

  it("binds form inputs to component state", async () => {
    const wrapper = mount(RegisterView, {
      global: {
        plugins: [router],
      },
    })

    const usernameInput = wrapper.find("#username")
    const emailInput = wrapper.find("#email")
    const passwordInput = wrapper.find("#password")
    const confirmPasswordInput = wrapper.find("#confirmPassword")

    await usernameInput.setValue("testuser")
    await emailInput.setValue("test@example.com")
    await passwordInput.setValue("password123")
    await confirmPasswordInput.setValue("password123")

    expect(usernameInput.element.value).toBe("testuser")
    expect(emailInput.element.value).toBe("test@example.com")
    expect(passwordInput.element.value).toBe("password123")
    expect(confirmPasswordInput.element.value).toBe("password123")
  })

  it("has correct input types", () => {
    const wrapper = mount(RegisterView, {
      global: {
        plugins: [router],
      },
    })

    expect(wrapper.find("#username").attributes("type")).toBe("text")
    expect(wrapper.find("#email").attributes("type")).toBe("email")
    expect(wrapper.find("#password").attributes("type")).toBe("password")
    expect(wrapper.find("#confirmPassword").attributes("type")).toBe("password")
  })

  it("has validation constraints on inputs", () => {
    const wrapper = mount(RegisterView, {
      global: {
        plugins: [router],
      },
    })

    const usernameInput = wrapper.find("#username")
    const passwordInput = wrapper.find("#password")

    expect(usernameInput.attributes("minlength")).toBe("3")
    expect(usernameInput.attributes("maxlength")).toBe("50")
    expect(passwordInput.attributes("minlength")).toBe("8")
  })

  it("does not display error message initially", () => {
    const wrapper = mount(RegisterView, {
      global: {
        plugins: [router],
      },
    })

    expect(wrapper.find(".error-message").exists()).toBe(false)
  })
})
