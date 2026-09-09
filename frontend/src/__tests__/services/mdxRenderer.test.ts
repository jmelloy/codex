import { describe, it, expect } from "vitest"
import { mount } from "@vue/test-utils"
import { defineComponent, h, type Component } from "vue"
import { compileMdx, flattenChildrenToText, MdxCompileError } from "../../services/mdxRenderer"

function renderMdx(
  source: string,
  resolve: (name: string) => Component | undefined = () => undefined,
) {
  const vnode = compileMdx(source, resolve)
  const Wrapper = defineComponent({
    render() {
      return vnode
    },
  })
  return mount(Wrapper)
}

describe("compileMdx", () => {
  it("renders headings", () => {
    const wrapper = renderMdx("# Hello world")
    expect(wrapper.html()).toContain("<h1>Hello world</h1>")
  })

  it("renders bold and italic as real elements", () => {
    const wrapper = renderMdx("This is **bold** and *italic* text.")
    expect(wrapper.html()).toContain("<strong>bold</strong>")
    expect(wrapper.html()).toContain("<em>italic</em>")
  })

  it("renders unordered lists", () => {
    const wrapper = renderMdx("- one\n- two")
    expect(wrapper.findAll("li")).toHaveLength(2)
    expect(wrapper.html()).toContain("one")
    expect(wrapper.html()).toContain("two")
  })

  it("renders links with resolved hrefs", () => {
    const wrapper = renderMdx("[docs](https://example.com)")
    const link = wrapper.find("a")
    expect(link.attributes("href")).toBe("https://example.com")
    expect(link.text()).toBe("docs")
  })

  it("translates React-style className to Vue class for fenced code", () => {
    const wrapper = renderMdx("```python\nprint(1)\n```")
    const code = wrapper.find("code")
    expect(code.attributes("class")).toBe("language-python")
    expect(code.attributes("classname")).toBeUndefined()
  })

  it("renders a registered component via the resolve callback", () => {
    const Stub: Component = {
      props: ["date"],
      setup(props: any) {
        return () => h("div", { class: "stub-calendar" }, `date=${props.date}`)
      },
    }
    const wrapper = renderMdx('Hi <Calendar date="2026-01-01" />', (name) =>
      name === "Calendar" ? Stub : undefined,
    )
    expect(wrapper.find(".stub-calendar").text()).toBe("date=2026-01-01")
  })

  it("falls back to a visible placeholder for an unauthorized component", () => {
    const wrapper = renderMdx('<EvilComponent src="x" />')
    expect(wrapper.find(".mdx-unauthorized-component").exists()).toBe(true)
    expect(wrapper.text()).toContain("EvilComponent")
  })

  it("falls back to a placeholder for an allowlisted component with no resolver registered", () => {
    const wrapper = renderMdx('<Calendar date="2026-01-01" />', () => undefined)
    expect(wrapper.find(".mdx-unauthorized-component").exists()).toBe(true)
  })

  it("throws MdxCompileError for invalid MDX syntax", () => {
    expect(() => compileMdx("<Unclosed>", () => undefined)).toThrow(MdxCompileError)
  })

  it("rejects JS expressions embedded in MDX content", () => {
    expect(() => compileMdx("Hello {1 + 1}", () => undefined)).toThrow(MdxCompileError)
  })

  it("rejects ESM import statements", () => {
    expect(() => compileMdx('import x from "evil"\n\nHello', () => undefined)).toThrow(MdxCompileError)
  })

  it("rejects ESM export statements", () => {
    expect(() => compileMdx("export const x = 1\n\nHello", () => undefined)).toThrow(MdxCompileError)
  })

  it("rejects JS expressions used as a component attribute value", () => {
    expect(() => compileMdx('<Calendar date={window.location} />', () => undefined)).toThrow(
      MdxCompileError,
    )
  })

  it("rejects spread attributes on a component", () => {
    expect(() => compileMdx("<Calendar {...evilProps} />", () => undefined)).toThrow(MdxCompileError)
  })

  it("still renders plain-string component attributes after JS-expression validation", () => {
    const wrapper = renderMdx('<Calendar date="2026-01-01" />', (name) =>
      name === "Calendar" ? { setup: () => () => null } : undefined,
    )
    expect(wrapper.find(".mdx-unauthorized-component").exists()).toBe(false)
  })
})

describe("flattenChildrenToText", () => {
  it("returns plain strings unchanged", () => {
    expect(flattenChildrenToText("hello")).toBe("hello")
  })

  it("joins arrays of strings", () => {
    expect(flattenChildrenToText(["a", "b", "c"])).toBe("abc")
  })

  it("returns empty string for null/undefined", () => {
    expect(flattenChildrenToText(null)).toBe("")
    expect(flattenChildrenToText(undefined)).toBe("")
  })

  it("recurses into vnode-shaped children", () => {
    expect(flattenChildrenToText({ children: ["nested ", { children: "text" }] })).toBe(
      "nested text",
    )
  })
})
