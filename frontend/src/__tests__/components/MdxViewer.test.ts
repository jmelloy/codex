import { describe, it, expect, beforeEach } from "vitest"
import { mount } from "@vue/test-utils"
import { setActivePinia, createPinia } from "pinia"
import MdxViewer from "../../components/MdxViewer.vue"

describe("MdxViewer", () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it("renders MDX content", () => {
    const wrapper = mount(MdxViewer, { props: { content: "# Test content" } })
    expect(wrapper.find("h1").text()).toBe("Test content")
  })

  it("renders legacy Markdown content with format md", () => {
    const wrapper = mount(MdxViewer, {
      props: { content: "| a | b |\n|---|---|\n| 1 | 2 |", format: "md" },
    })
    expect(wrapper.findAll("td").map((td) => td.text())).toEqual(["1", "2"])
  })
})
