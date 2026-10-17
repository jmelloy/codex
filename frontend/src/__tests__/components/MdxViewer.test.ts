import { describe, it, expect, beforeEach } from "vitest"
import { mount } from "@vue/test-utils"
import { setActivePinia, createPinia } from "pinia"
import MdxViewer from "../../components/MdxViewer.vue"

describe("MdxViewer", () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it("emits copy event when copy button is clicked", async () => {
    Object.defineProperty(navigator, "clipboard", {
      value: {
        writeText: async () => {},
      },
      writable: true,
      configurable: true,
    })

    const wrapper = mount(MdxViewer, {
      props: {
        content: "# Test content",
        showToolbar: true,
      },
    })

    const copyButton = wrapper.find(".btn-copy")
    await copyButton.trigger("click")
    await Promise.resolve()

    expect(wrapper.emitted("copy")).toBeTruthy()
  })
})
