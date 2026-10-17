import { describe, it, expect } from "vitest"
import { mount } from "@vue/test-utils"
import MdxBlockRenderer from "../../components/blocks/MdxBlockRenderer.vue"

describe("MdxBlockRenderer", () => {
  it("renders MDX markdown constructs as real elements", () => {
    const wrapper = mount(MdxBlockRenderer, {
      props: { content: "# Title\n\nSome **bold** text." },
    })
    expect(wrapper.find("h1").text()).toBe("Title")
    expect(wrapper.find("strong").text()).toBe("bold")
  })

  it("shows an empty-state message for blank content", () => {
    const wrapper = mount(MdxBlockRenderer, { props: { content: "" } })
    expect(wrapper.text()).toContain("No content to display")
  })

  it("renders a registered dedicated component (Calendar)", () => {
    const wrapper = mount(MdxBlockRenderer, {
      props: { content: '<Calendar date="2026-01-01" />' },
    })
    expect(wrapper.find(".calendar-block").exists()).toBe(true)
  })

  it("shows an unauthorized placeholder for an unknown component", () => {
    const wrapper = mount(MdxBlockRenderer, {
      props: { content: "<NotARealComponent />" },
    })
    expect(wrapper.find(".mdx-unauthorized-component").exists()).toBe(true)
  })
})
