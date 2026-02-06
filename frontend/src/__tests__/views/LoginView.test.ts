import { describe, it, expect, beforeEach, vi } from "vitest"
import { mount } from "@vue/test-utils"
import { createRouter, createWebHistory } from "vue-router"
import { setActivePinia, createPinia } from "pinia"
import LoginView from "../../views/LoginView.vue"

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", component: { template: "Home" } },
    { path: "/login", component: LoginView },
    { path: "/register", component: { template: "Register" } },
  ],
})

function mountLogin() {
  return mount(LoginView, { global: { plugins: [router] } })
}

describe("LoginView", () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
  })

  it("renders login form with all elements", () => {
    const wrapper = mountLogin()

    expect(wrapper.find("h1").text()).toContain("Codex")
    expect(wrapper.find(".subtitle").text()).toContain("Laboratory Journal System")
    expect(wrapper.find("#username").exists()).toBe(true)
    expect(wrapper.find("#password").exists()).toBe(true)
    expect(wrapper.find("#username").attributes("type")).toBe("text")
    expect(wrapper.find("#password").attributes("type")).toBe("password")
    expect(wrapper.find("#username").attributes("required")).toBeDefined()
    expect(wrapper.find("#password").attributes("required")).toBeDefined()
    expect(wrapper.find('button[type="submit"]').text()).toBe("Login")
    expect(wrapper.find(".register-link a").attributes("href")).toBe("/register")
  })

  it("binds inputs to component state via v-model", async () => {
    const wrapper = mountLogin()
    await wrapper.find("#username").setValue("testuser")
    await wrapper.find("#password").setValue("testpassword")

    expect(wrapper.find("#username").element.value).toBe("testuser")
    expect(wrapper.find("#password").element.value).toBe("testpassword")
  })

  it("shows loading state and error messages from store", async () => {
    const wrapper = mountLogin()
    const { useAuthStore } = await import("../../stores/auth")
    const authStore = useAuthStore()

    // Loading
    authStore.loading = true
    await wrapper.vm.$nextTick()
    expect(wrapper.find('button[type="submit"]').text()).toContain("Logging in")

    // Error
    authStore.loading = false
    authStore.error = "Invalid credentials"
    await wrapper.vm.$nextTick()
    expect(wrapper.find(".error").text()).toBe("Invalid credentials")
  })

  it("does not display error when no error exists", () => {
    expect(mountLogin().find(".error").exists()).toBe(false)
  })
})
