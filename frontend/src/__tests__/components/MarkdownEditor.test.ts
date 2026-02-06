import { describe, it, expect, beforeEach, vi } from "vitest"
import { mount } from "@vue/test-utils"
import { setActivePinia, createPinia } from "pinia"
import MarkdownEditor from "../../components/MarkdownEditor.vue"

function mountEditor(props = {}) {
  return mount(MarkdownEditor, { props: { modelValue: "", ...props } })
}

describe("MarkdownEditor", () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it("renders in live mode by default with mode toggle", () => {
    const wrapper = mountEditor({ modelValue: "# Test" })

    expect(wrapper.find(".live-editor-content").exists()).toBe(true)
    expect(wrapper.find("textarea").exists()).toBe(false)

    const modeToggle = wrapper.find(".mode-toggle")
    expect(modeToggle.findAll("button").map((b) => b.text())).toEqual(["Live", "Raw"])
  })

  it("shows hint text in live mode", () => {
    const wrapper = mountEditor()
    expect(wrapper.find(".live-mode-hint .hint-text").text()).toContain("Type # for headings")
  })

  it("displays content in raw mode", () => {
    const wrapper = mountEditor({ modelValue: "# Test Content", defaultMode: "raw" })
    expect(wrapper.find("textarea").element.value).toBe("# Test Content")
  })

  it("switches between live and raw modes", async () => {
    const wrapper = mountEditor({ modelValue: "# Test" })

    // Initially in live mode
    expect(wrapper.find(".live-editor-content").exists()).toBe(true)

    // Switch to raw
    await wrapper.find(".mode-toggle").findAll("button")[1].trigger("click")
    expect(wrapper.find("textarea").exists()).toBe(true)
    expect(wrapper.find(".live-editor-content").exists()).toBe(false)

    // Switch back to live
    await wrapper.find(".mode-toggle").findAll("button")[0].trigger("click")
    expect(wrapper.find(".live-editor-content").exists()).toBe(true)
  })

  it("emits update:modelValue and change on content change in raw mode", async () => {
    const wrapper = mountEditor({ defaultMode: "raw" })
    await wrapper.find("textarea").setValue("New content")

    expect(wrapper.emitted("update:modelValue")![0]).toEqual(["New content"])
    expect(wrapper.emitted("change")![0]).toEqual(["New content"])
  })

  it.each([
    ["Hello world\nThis is a test", "26 characters", "6 words", "2 lines"],
    ["Hello    world   test", null, "3 words", null],
    ["", null, "0 words", null],
    ["   \n  \n  ", null, "0 words", null],
  ])("counts stats correctly for '%s'", (content, chars, words, lines) => {
    const stats = mountEditor({ modelValue: content }).find(".editor-stats").text()
    if (chars) expect(stats).toContain(chars)
    expect(stats).toContain(words)
    if (lines) expect(stats).toContain(lines)
  })

  it("updates character count on content change in raw mode", async () => {
    const wrapper = mountEditor({ modelValue: "Hello", defaultMode: "raw" })
    expect(wrapper.find(".editor-stats").text()).toContain("5 characters")

    await wrapper.find("textarea").setValue("Hello World!")
    expect(wrapper.find(".editor-stats").text()).toContain("12 characters")
  })

  it("displays placeholder text (custom and default) in raw mode", () => {
    const custom = mountEditor({ placeholder: "Custom placeholder", defaultMode: "raw" })
    expect(custom.find("textarea").attributes("placeholder")).toBe("Custom placeholder")

    const defaultPlaceholder = mountEditor({ defaultMode: "raw" })
    expect(defaultPlaceholder.find("textarea").attributes("placeholder")).toBe("Start writing your markdown...")
  })

  it("emits save and cancel events", async () => {
    const wrapper = mountEditor({ modelValue: "Test content" })

    await wrapper.find(".btn-save").trigger("click")
    expect(wrapper.emitted("save")![0]).toEqual(["Test content"])

    await wrapper.find(".btn-cancel").trigger("click")
    expect(wrapper.emitted("cancel")).toBeTruthy()
  })

  it("toggles preview modes in raw mode", async () => {
    const wrapper = mountEditor({ modelValue: "# Test", defaultMode: "raw" })

    const previewButton = wrapper
      .findAll(".toolbar-group button")
      .find((btn) => btn.text().includes("Preview"))!

    expect(wrapper.find(".split-view").exists()).toBe(false)

    await previewButton.trigger("click")
    expect(wrapper.find(".split-view").exists()).toBe(true)

    await previewButton.trigger("click")
    await previewButton.trigger("click")
    expect(wrapper.find(".split-view").exists()).toBe(false)
  })

  it("displays toolbar with formatting buttons", () => {
    const toolbar = mountEditor().find(".editor-toolbar")
    expect(toolbar.exists()).toBe(true)
    expect(toolbar.findAll("button").length).toBeGreaterThan(0)
  })

  it("handles Tab key in raw mode", async () => {
    const wrapper = mountEditor({ modelValue: "test", defaultMode: "raw" })
    const textarea = wrapper.find("textarea")
    textarea.element.selectionStart = 4
    textarea.element.selectionEnd = 4
    await textarea.trigger("keydown", { key: "Tab" })
    expect(wrapper.emitted("change")).toBeTruthy()
  })

  it("renders with frontmatter prop", () => {
    const wrapper = mountEditor({
      modelValue: "# Test",
      frontmatter: { title: "Test Page", author: "Test Author" },
    })
    expect(wrapper.exists()).toBe(true)
  })

  it("autosave emits save after delay when enabled, not when disabled", async () => {
    vi.useFakeTimers()

    const enabled = mountEditor({ autosave: true, autosaveDelay: 1000, defaultMode: "raw" })
    await enabled.find("textarea").setValue("Test content")
    expect(enabled.emitted("save")).toBeFalsy()
    vi.advanceTimersByTime(1000)
    expect(enabled.emitted("save")).toBeTruthy()

    const disabled = mountEditor({ autosave: false, defaultMode: "raw" })
    await disabled.find("textarea").setValue("Test content")
    vi.advanceTimersByTime(5000)
    expect(disabled.emitted("save")).toBeFalsy()

    vi.useRealTimers()
  })
})
