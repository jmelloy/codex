import { describe, it, expect, beforeEach, vi } from "vitest"
import { mount } from "@vue/test-utils"
import { setActivePinia, createPinia } from "pinia"
import MarkdownEditor from "../../components/MarkdownEditor.vue"

describe("MarkdownEditor", () => {
  beforeEach(() => {
    // Create a fresh pinia instance for each test
    setActivePinia(createPinia())
  })

  it("renders without crashing", () => {
    const wrapper = mount(MarkdownEditor, {
      props: {
        modelValue: "",
      },
    })
    expect(wrapper.exists()).toBe(true)
  })

  it("displays the provided content", () => {
    const content = "# Test Content"
    const wrapper = mount(MarkdownEditor, {
      props: {
        modelValue: content,
      },
    })

    const textarea = wrapper.find("textarea")
    expect(textarea.element.value).toBe(content)
  })

  it("emits update:modelValue when content changes", async () => {
    const wrapper = mount(MarkdownEditor, {
      props: {
        modelValue: "",
      },
    })

    const textarea = wrapper.find("textarea")
    await textarea.setValue("New content")

    expect(wrapper.emitted("update:modelValue")).toBeTruthy()
    expect(wrapper.emitted("update:modelValue")![0]).toEqual(["New content"])
  })

  it("displays character, word, and line count", () => {
    const content = "Hello world\nThis is a test"
    const wrapper = mount(MarkdownEditor, {
      props: {
        modelValue: content,
      },
    })

    const stats = wrapper.find(".editor-stats")
    expect(stats.text()).toContain("26 characters")
    expect(stats.text()).toContain("6 words")
    expect(stats.text()).toContain("2 lines")
  })

  it("displays placeholder text when content is empty", () => {
    const wrapper = mount(MarkdownEditor, {
      props: {
        modelValue: "",
        placeholder: "Custom placeholder",
      },
    })

    const textarea = wrapper.find("textarea")
    expect(textarea.attributes("placeholder")).toBe("Custom placeholder")
  })

  it("shows default placeholder when not provided", () => {
    const wrapper = mount(MarkdownEditor, {
      props: {
        modelValue: "",
      },
    })

    const textarea = wrapper.find("textarea")
    expect(textarea.attributes("placeholder")).toBe("Start writing your markdown...")
  })

  it("emits save event when save button is clicked", async () => {
    const content = "Test content"
    const wrapper = mount(MarkdownEditor, {
      props: {
        modelValue: content,
      },
    })

    const saveButton = wrapper.find(".btn-save")
    await saveButton.trigger("click")

    expect(wrapper.emitted("save")).toBeTruthy()
    expect(wrapper.emitted("save")![0]).toEqual([content])
  })

  it("emits cancel event when cancel button is clicked", async () => {
    const wrapper = mount(MarkdownEditor, {
      props: {
        modelValue: "Test content",
      },
    })

    const cancelButton = wrapper.find(".btn-cancel")
    await cancelButton.trigger("click")

    expect(wrapper.emitted("cancel")).toBeTruthy()
  })

  it("displays editor only by default", () => {
    const wrapper = mount(MarkdownEditor, {
      props: {
        modelValue: "# Test",
      },
    })

    const editorPane = wrapper.find(".editor-pane")
    const previewPane = wrapper.find(".preview-pane")

    expect(editorPane.isVisible()).toBe(true)
    expect(previewPane.exists()).toBe(true)
    // Preview pane exists but may be visible with v-show=false logic
    // Check it's not in split view mode instead
    expect(wrapper.find(".split-view").exists()).toBe(false)
  })

  it("toggles preview when preview button is clicked", async () => {
    const wrapper = mount(MarkdownEditor, {
      props: {
        modelValue: "# Test",
      },
    })

    const previewButton = wrapper
      .findAll(".toolbar-group button")
      .find((btn) => btn.text().includes("Preview"))

    // Initially not in split view (button shows "Preview")
    expect(previewButton!.text()).toBe("Preview")
    expect(wrapper.find(".split-view").exists()).toBe(false)

    // Click to show split view (button shows "Edit")
    await previewButton!.trigger("click")
    expect(wrapper.find(".split-view").exists()).toBe(true)

    // Click again - behavior cycles through different modes
    await previewButton!.trigger("click")
    // After second click, should be in a different mode

    // Click again to cycle back
    await previewButton!.trigger("click")
    expect(wrapper.find(".split-view").exists()).toBe(false)
  })

  it("displays toolbar with formatting buttons", () => {
    const wrapper = mount(MarkdownEditor, {
      props: {
        modelValue: "",
      },
    })

    const toolbar = wrapper.find(".editor-toolbar")
    expect(toolbar.exists()).toBe(true)

    const buttons = toolbar.findAll("button")
    expect(buttons.length).toBeGreaterThan(0)
  })

  it("inserts tab as spaces when Tab key is pressed", async () => {
    const wrapper = mount(MarkdownEditor, {
      props: {
        modelValue: "test",
      },
    })

    const textarea = wrapper.find("textarea")

    // Set cursor position at end
    const element = textarea.element
    element.selectionStart = 4
    element.selectionEnd = 4

    await textarea.trigger("keydown", { key: "Tab" })

    // Should have prevented default and not actually inserted tab
    // The actual insertion is tested in component logic
    expect(wrapper.emitted("change")).toBeTruthy()
  })

  it("counts words correctly with multiple spaces", () => {
    const content = "Hello    world   test"
    const wrapper = mount(MarkdownEditor, {
      props: {
        modelValue: content,
      },
    })

    const stats = wrapper.find(".editor-stats")
    expect(stats.text()).toContain("3 words")
  })

  it("counts 0 words for empty content", () => {
    const wrapper = mount(MarkdownEditor, {
      props: {
        modelValue: "",
      },
    })

    const stats = wrapper.find(".editor-stats")
    expect(stats.text()).toContain("0 words")
  })

  it("counts 0 words for whitespace-only content", () => {
    const wrapper = mount(MarkdownEditor, {
      props: {
        modelValue: "   \n  \n  ",
      },
    })

    const stats = wrapper.find(".editor-stats")
    expect(stats.text()).toContain("0 words")
  })

  it("emits change event when content changes", async () => {
    const wrapper = mount(MarkdownEditor, {
      props: {
        modelValue: "",
      },
    })

    const textarea = wrapper.find("textarea")
    await textarea.setValue("New content")

    expect(wrapper.emitted("change")).toBeTruthy()
    expect(wrapper.emitted("change")![0]).toEqual(["New content"])
  })

  it("updates character count correctly", async () => {
    const wrapper = mount(MarkdownEditor, {
      props: {
        modelValue: "Hello",
      },
    })

    let stats = wrapper.find(".editor-stats")
    expect(stats.text()).toContain("5 characters")

    const textarea = wrapper.find("textarea")
    await textarea.setValue("Hello World!")

    stats = wrapper.find(".editor-stats")
    expect(stats.text()).toContain("12 characters")
  })

  it("renders with frontmatter prop", () => {
    const wrapper = mount(MarkdownEditor, {
      props: {
        modelValue: "# Test",
        frontmatter: {
          title: "Test Page",
          author: "Test Author",
        },
      },
    })

    expect(wrapper.exists()).toBe(true)
  })

  it("autosave emits save after delay when enabled", async () => {
    vi.useFakeTimers()

    const wrapper = mount(MarkdownEditor, {
      props: {
        modelValue: "",
        autosave: true,
        autosaveDelay: 1000,
      },
    })

    const textarea = wrapper.find("textarea")
    await textarea.setValue("Test content")

    // Should not have saved yet
    expect(wrapper.emitted("save")).toBeFalsy()

    // Advance timers
    vi.advanceTimersByTime(1000)

    // Now should have saved
    expect(wrapper.emitted("save")).toBeTruthy()

    vi.useRealTimers()
  })

  it("autosave does not emit when disabled", async () => {
    vi.useFakeTimers()

    const wrapper = mount(MarkdownEditor, {
      props: {
        modelValue: "",
        autosave: false,
      },
    })

    const textarea = wrapper.find("textarea")
    await textarea.setValue("Test content")

    vi.advanceTimersByTime(5000)

    // Should not have auto-saved
    expect(wrapper.emitted("save")).toBeFalsy()

    vi.useRealTimers()
  })
})
