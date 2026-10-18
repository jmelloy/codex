import { describe, it, expect, vi } from "vitest"
import { mount } from "@vue/test-utils"
import { createPinia, setActivePinia } from "pinia"
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

vi.mock("../../services/pluginLoader", () => ({
  isBlockTypeKnown: (type: string) => type === "weather",
  getAvailableBlockTypes: async () => [],
  loadPluginComponent: (type: string) => ({
    props: ["config"],
    template: `<div class="stub-plugin-block" :data-type="'${type}'">{{ JSON.stringify(config) }}</div>`,
  }),
}))

describe("MdxBlockRenderer legacy Markdown (format md)", () => {
  const mountMd = (content: string) =>
    mount(MdxBlockRenderer, {
      props: { content, format: "md", workspaceId: "ws", notebookId: "nb" },
    })

  it("drops raw HTML instead of injecting it", () => {
    const wrapper = mountMd(
      'hi <img src="x" onerror="alert(1)"> there\n\n<script>alert(2)</script>',
    )
    expect(wrapper.find("img").exists()).toBe(false)
    expect(wrapper.find("script").exists()).toBe(false)
    expect(wrapper.text()).toContain("hi")
  })

  it("keeps braces and JSX-looking text literal", () => {
    const wrapper = mountMd("value is {1+1} and <Foo />")
    expect(wrapper.text()).toContain("{1+1}")
    expect(wrapper.find(".mdx-unauthorized-component").exists()).toBe(false)
  })

  it("renders GFM tables and single-newline line breaks", () => {
    const wrapper = mountMd("line one\nline two\n\n| a |\n|---|\n| 1 |")
    expect(wrapper.find("br").exists()).toBe(true)
    expect(wrapper.find("td").text()).toBe("1")
  })

  it("resolves local links for in-app navigation and opens external links in a new tab", () => {
    const wrapper = mountMd("[local](notes/today.md) [ext](https://example.com)")
    const [local, ext] = wrapper.findAll("a")
    expect(local!.attributes("data-internal-link")).toBe("notes/today.md")
    expect(local!.attributes("href")).toContain("/api/v1/workspaces/ws/notebooks/nb/blocks/path/")
    expect(ext!.attributes("target")).toBe("_blank")
  })

  it("does not render javascript: links as anchors", () => {
    const wrapper = mountMd("[click](javascript:alert(1))")
    expect(wrapper.find("a").exists()).toBe(false)
    expect(wrapper.text()).toContain("click")
  })

  it("renders a plugin code fence as its block component with parsed config", () => {
    const wrapper = mountMd("```weather\nlocation: NYC\nunits: metric\n```")
    const block = wrapper.find(".stub-plugin-block")
    expect(block.attributes("data-type")).toBe("weather")
    expect(JSON.parse(block.text())).toEqual({ location: "NYC", units: "metric" })
  })

  it("renders other code fences as highlighted code", () => {
    setActivePinia(createPinia())
    const wrapper = mountMd("```python\nprint('hi')\n```")
    expect(wrapper.find(".stub-plugin-block").exists()).toBe(false)
    expect(wrapper.text()).toContain("print")
  })
})

describe("MdxBlockRenderer host element safety (format mdx)", () => {
  it.each([
    ['<img src="x" onerror="alert(1)" />', "event handler"],
    ['<a href="javascript:alert(1)">x</a>', "script or data URL"],
    ['<iframe src="https://example.com" />', "<iframe>"],
  ])("rejects %s", (content, message) => {
    const wrapper = mount(MdxBlockRenderer, { props: { content } })
    expect(wrapper.find(".error-content").text()).toContain(message)
  })

  it("allows data: image sources", () => {
    const wrapper = mount(MdxBlockRenderer, {
      props: { content: '<img src="data:image/png;base64,AAAA" alt="x" />' },
    })
    expect(wrapper.find("img").exists()).toBe(true)
  })
})
