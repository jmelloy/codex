import { describe, it, expect, vi } from "vitest"
import { mount } from "@vue/test-utils"
import FilePropertiesPanel from "../../components/FilePropertiesPanel.vue"

vi.mock("../../services/codex", () => ({
  fileService: {
    getHistory: vi.fn().mockResolvedValue({ file_id: 1, path: "/test/path", history: [] }),
    getAtCommit: vi.fn().mockResolvedValue({
      file_id: 1,
      path: "/test/path",
      commit_hash: "abc123",
      content: "# Old Content",
    }),
  },
}))

const mockFile = {
  id: 1,
  path: "/test/path",
  filename: "test-file.md",
  title: "Test File",
  description: "Test description",
  content_type: "text/markdown",
  size: 1024,
  created_at: "2024-01-15T12:00:00Z",
  updated_at: "2024-01-16T12:00:00Z",
  properties: {
    title: "Test File",
    description: "Test description",
    tags: ["test", "example"],
  },
  content: "# Test Content",
  notebook_id: 1,
}

const defaultProps = { workspaceId: 1, notebookId: 1 }

function mountPanel(file: any = mockFile) {
  return mount(FilePropertiesPanel, { props: { file, ...defaultProps } })
}

describe("FilePropertiesPanel", () => {
  it("displays empty state when no file is provided", () => {
    const wrapper = mountPanel(null)

    expect(wrapper.find(".empty-state").exists()).toBe(true)
    expect(wrapper.text()).toContain("No file selected")
  })

  it("displays file properties when file is provided", () => {
    const wrapper = mountPanel()

    expect(wrapper.find(".panel-content").exists()).toBe(true)
    expect(wrapper.find(".empty-state").exists()).toBe(false)

    // Title, description, path, filename, type, size
    expect(wrapper.find(".property-input").element.value).toBe("Test File")
    expect(wrapper.find(".property-textarea").element.value).toBe("Test description")
    expect(wrapper.html()).toContain("/test/path")
    expect(wrapper.text()).toContain("test-file.md")
    expect(wrapper.text()).toContain("markdown")
    expect(wrapper.text()).toContain("1 KB")
  })

  it.each([
    [500, "500 B"],
    [1024, "1 KB"],
    [5242880, "5 MB"],
  ])("formats file size %d as '%s'", (size, expected) => {
    const wrapper = mountPanel({ ...mockFile, size })
    expect(wrapper.text()).toContain(expected)
  })

  it("displays created and modified dates", () => {
    const wrapper = mountPanel()

    expect(wrapper.text()).toContain("Created")
    expect(wrapper.text()).toContain("Modified")
    expect(wrapper.text()).toMatch(/Jan|January/)
  })

  it("displays tags when present and hides when absent", () => {
    const wrapper = mountPanel()
    expect(wrapper.text()).toContain("test")
    expect(wrapper.text()).toContain("example")

    const noTags = mountPanel({
      ...mockFile,
      properties: { title: "Test File", description: "Test description" },
    })
    expect(noTags.findAll(".tag").length).toBe(0)
  })

  it("emits close event when close button clicked", async () => {
    const wrapper = mountPanel()
    await wrapper.find(".btn-close").trigger("click")
    expect(wrapper.emitted("close")).toBeTruthy()
  })

  it("emits updateProperties when title changed via blur or enter", async () => {
    const wrapper = mountPanel()
    const titleInput = wrapper.find(".property-input")

    await titleInput.setValue("New Title")
    await titleInput.trigger("blur")
    expect(wrapper.emitted("updateProperties")).toBeTruthy()
    expect((wrapper.emitted("updateProperties")![0][0] as any).title).toBe("New Title")

    // Reset and test enter key
    const wrapper2 = mountPanel()
    const titleInput2 = wrapper2.find(".property-input")
    await titleInput2.setValue("Enter Title")
    await titleInput2.trigger("keyup.enter")
    expect((wrapper2.emitted("updateProperties")![0][0] as any).title).toBe("Enter Title")
  })

  it("emits updateProperties when description changed", async () => {
    const wrapper = mountPanel()
    const textarea = wrapper.find(".property-textarea")

    await textarea.setValue("New description")
    await textarea.trigger("blur")

    expect((wrapper.emitted("updateProperties")![0][0] as any).description).toBe("New description")
  })

  it("does not emit updateProperties if value unchanged", async () => {
    const wrapper = mountPanel()
    const titleInput = wrapper.find(".property-input")
    await titleInput.setValue("Test File")
    await titleInput.trigger("blur")
    expect(wrapper.emitted("updateProperties")).toBeFalsy()
  })

  it("emits delete when confirmed, not when cancelled", async () => {
    window.confirm = vi.fn(() => true)
    const wrapper = mountPanel()
    await wrapper.find(".btn-delete").trigger("click")
    expect(wrapper.emitted("delete")).toBeTruthy()

    window.confirm = vi.fn(() => false)
    const wrapper2 = mountPanel()
    await wrapper2.find(".btn-delete").trigger("click")
    expect(wrapper2.emitted("delete")).toBeFalsy()
  })

  it("updates editable fields when file prop changes", async () => {
    const wrapper = mountPanel()
    const newFile = {
      ...mockFile,
      title: "Updated Title",
      description: "Updated description",
      properties: { title: "Updated Title", description: "Updated description", tags: ["test", "example"] },
    }
    await wrapper.setProps({ file: newFile })

    expect(wrapper.find(".property-input").element.value).toBe("Updated Title")
    expect(wrapper.find(".property-textarea").element.value).toBe("Updated description")
  })

  it("handles file with no title or description gracefully", () => {
    const noTitle = mountPanel({ ...mockFile, title: null, properties: { description: "Test", tags: [] } })
    expect(noTitle.find(".property-input").element.value).toBe("")

    const noDesc = mountPanel({ ...mockFile, description: null, properties: { title: "Test", tags: [] } })
    expect(noDesc.find(".property-textarea").element.value).toBe("")
  })

  it("displays Properties and History tabs, Properties shown by default", () => {
    const wrapper = mountPanel()
    const tabs = wrapper.findAll(".tab-btn")

    expect(tabs.length).toBe(2)
    expect(tabs[0].text()).toBe("Properties")
    expect(tabs[1].text()).toBe("History")
    expect(wrapper.find(".property-input").exists()).toBe(true)
    expect(wrapper.find(".history-content").exists()).toBe(false)
  })
})
