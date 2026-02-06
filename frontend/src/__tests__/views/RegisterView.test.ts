import { describe, it, expect, beforeEach } from "vitest"
import { mount } from "@vue/test-utils"
import { createRouter, createWebHistory } from "vue-router"
import { setActivePinia, createPinia } from "pinia"
import RegisterView from "../../views/RegisterView.vue"

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", component: { template: "Home" } },
    { path: "/login", component: { template: "Login" } },
    { path: "/register", component: RegisterView },
  ],
})

function mountRegister() {
  return mount(RegisterView, { global: { plugins: [router] } })
}

describe("RegisterView", () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
  })

  it("renders registration form with all required elements", () => {
    const wrapper = mountRegister()

    expect(wrapper.find("h1").text()).toBe("Register")
    for (const id of ["#username", "#email", "#password", "#confirmPassword"]) {
      expect(wrapper.find(id).exists()).toBe(true)
      expect(wrapper.find(id).attributes("required")).toBeDefined()
    }
    expect(wrapper.find('button[type="submit"]').text()).toBe("Register")
    expect(wrapper.find(".login-link a").attributes("href")).toBe("/login")
  })

  it("has correct input types and validation constraints", () => {
    const wrapper = mountRegister()

    expect(wrapper.find("#username").attributes("type")).toBe("text")
    expect(wrapper.find("#email").attributes("type")).toBe("email")
    expect(wrapper.find("#password").attributes("type")).toBe("password")
    expect(wrapper.find("#confirmPassword").attributes("type")).toBe("password")
    expect(wrapper.find("#username").attributes("minlength")).toBe("3")
    expect(wrapper.find("#username").attributes("maxlength")).toBe("50")
    expect(wrapper.find("#password").attributes("minlength")).toBe("8")
  })

  it("binds form inputs to component state via v-model", async () => {
    const wrapper = mountRegister()

    await wrapper.find("#username").setValue("testuser")
    await wrapper.find("#email").setValue("test@example.com")
    await wrapper.find("#password").setValue("password123")
    await wrapper.find("#confirmPassword").setValue("password123")

    expect(wrapper.find("#username").element.value).toBe("testuser")
    expect(wrapper.find("#email").element.value).toBe("test@example.com")
    expect(wrapper.find("#password").element.value).toBe("password123")
    expect(wrapper.find("#confirmPassword").element.value).toBe("password123")
  })

  it("does not display error message initially", () => {
    expect(mountRegister().find(".error-message").exists()).toBe(false)
  })
})
