import { describe, it, expect, afterEach } from "vitest"
import { mount } from "@vue/test-utils"
import Modal from "../../components/Modal.vue"

let wrapper: any

function mountModal(props = {}, slots = {}) {
  wrapper = mount(Modal, {
    props: { modelValue: true, title: "Test Modal", ...props },
    slots: { default: "<p>Modal content</p>", ...slots },
    attachTo: document.body,
  })
  return wrapper
}

afterEach(() => {
  wrapper?.unmount()
  document.querySelector(".modal-backdrop")?.remove()
})

describe("Modal", () => {
  it("renders when modelValue is true, not when false", () => {
    mountModal()
    expect(document.querySelector(".modal-backdrop")).toBeTruthy()

    wrapper.unmount()
    mountModal({ modelValue: false })
    expect(document.querySelector(".modal-backdrop")).toBeFalsy()
  })

  it("displays title and slot content", () => {
    mountModal({ title: "Custom Title" })
    expect(document.querySelector("h3")?.textContent).toBe("Custom Title")
    expect(document.querySelector(".modal-content")?.innerHTML).toContain("Modal content")
  })

  it("hides title when not provided", () => {
    mountModal({ title: undefined })
    expect(document.querySelector("h3")).toBeFalsy()
  })

  it("displays custom confirm and cancel text, defaults correctly", () => {
    mountModal({ confirmText: "Save", cancelText: "Go Back" })
    expect(document.querySelector(".btn-primary")?.textContent).toBe("Save")
    const buttons = document.querySelectorAll("button")
    expect(buttons[0]?.textContent).toBe("Go Back")

    wrapper.unmount()
    mountModal()
    const defaultButtons = document.querySelectorAll("button")
    expect(defaultButtons[0]?.textContent).toBe("Cancel")
    expect(defaultButtons[1]?.textContent).toBe("Confirm")
  })

  it("hides actions when hideActions is true, shows by default", () => {
    mountModal({ hideActions: true })
    expect(document.querySelector(".modal-actions")).toBeFalsy()

    wrapper.unmount()
    mountModal()
    expect(document.querySelector(".modal-actions")).toBeTruthy()
  })

  it("emits close on backdrop click", async () => {
    mountModal()
    ;(document.querySelector(".modal-backdrop") as HTMLElement).click()
    await wrapper.vm.$nextTick()

    expect(wrapper.emitted("update:modelValue")?.[0]).toEqual([false])
    expect(wrapper.emitted("cancel")).toBeTruthy()
  })

  it("emits close on cancel button click", async () => {
    mountModal()
    ;(document.querySelectorAll("button")[0] as HTMLElement).click()
    await wrapper.vm.$nextTick()

    expect(wrapper.emitted("update:modelValue")?.[0]).toEqual([false])
    expect(wrapper.emitted("cancel")).toBeTruthy()
  })

  it("emits confirm on confirm button click", async () => {
    mountModal()
    ;(document.querySelector(".btn-primary") as HTMLElement).click()
    await wrapper.vm.$nextTick()

    expect(wrapper.emitted("confirm")).toBeTruthy()
  })

  it("does not close when clicking modal content", async () => {
    mountModal()
    ;(document.querySelector(".modal-content") as HTMLElement).click()
    await wrapper.vm.$nextTick()

    expect(wrapper.emitted("update:modelValue")).toBeFalsy()
  })
})
