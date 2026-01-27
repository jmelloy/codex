import { describe, it, expect, beforeEach } from "vitest"
import { mount } from "@vue/test-utils"
import { setActivePinia, createPinia } from "pinia"
import MarkdownViewer from "../../components/MarkdownViewer.vue"

describe("MarkdownViewer", () => {
  beforeEach(() => {
    // Create a fresh pinia instance for each test
    setActivePinia(createPinia())
  })

  it("renders markdown content properly", () => {
    const markdownContent = "# Hello World\n\nThis is a **test**."
    const wrapper = mount(MarkdownViewer, {
      props: {
        content: markdownContent,
        showToolbar: false,
      },
    })

    const html = wrapper.find(".markdown-content").html()
    expect(html).toContain("<h1")
    expect(html).toContain("Hello World")
    expect(html).toContain("<strong>")
    expect(html).toContain("test")
  })

  it("displays empty content message when no content provided", () => {
    const wrapper = mount(MarkdownViewer, {
      props: {
        content: "",
        showToolbar: false,
      },
    })

    expect(wrapper.find(".markdown-content").text()).toContain("No content to display")
  })

  it("renders code blocks with syntax highlighting", () => {
    const markdownWithCode = "```javascript\nconst x = 42;\n```"
    const wrapper = mount(MarkdownViewer, {
      props: {
        content: markdownWithCode,
        showToolbar: false,
      },
    })

    const html = wrapper.find(".markdown-content").html()
    expect(html).toContain("<pre>")
    expect(html).toContain("language-javascript")
    // Syntax highlighting wraps keywords in spans, so check for hljs class
    expect(html).toContain("hljs")
    // Check that the code content is present (may be split across highlight spans)
    expect(wrapper.find(".markdown-content").text()).toContain("const x = 42")
  })

  it("shows toolbar when showToolbar is true", () => {
    const wrapper = mount(MarkdownViewer, {
      props: {
        content: "# Test",
        showToolbar: true,
      },
    })

    expect(wrapper.find(".markdown-toolbar").exists()).toBe(true)
  })

  it("hides toolbar when showToolbar is false", () => {
    const wrapper = mount(MarkdownViewer, {
      props: {
        content: "# Test",
        showToolbar: false,
      },
    })

    expect(wrapper.find(".markdown-toolbar").exists()).toBe(false)
  })

  it("emits copy event when copy button is clicked", async () => {
    // Mock clipboard API
    const mockWriteText = async () => {}
    Object.defineProperty(navigator, "clipboard", {
      value: {
        writeText: mockWriteText,
      },
      writable: true,
      configurable: true,
    })

    const wrapper = mount(MarkdownViewer, {
      props: {
        content: "Test content",
        showToolbar: true,
      },
    })

    const copyButton = wrapper.find(".btn-copy")
    await copyButton.trigger("click")

    expect(wrapper.emitted("copy")).toBeTruthy()
  })

  it("resolves image URLs by filename when workspace and notebook context provided", () => {
    const markdownWithImage = "![Test Image](test-image.png)"
    const wrapper = mount(MarkdownViewer, {
      props: {
        content: markdownWithImage,
        showToolbar: false,
        workspaceId: 1,
        notebookId: 2,
      },
    })

    const html = wrapper.find(".markdown-content").html()
    expect(html).toContain("<img")
    // HTML entities are escaped in the output
    expect(html).toContain(
      'src="/api/v1/files/by-path/content?path=test-image.png&amp;workspace_id=1&amp;notebook_id=2"'
    )
    expect(html).toContain('alt="Test Image"')
  })

  it("resolves link URLs by filename when workspace and notebook context provided", () => {
    const markdownWithLink = "[Read More](document.md)"
    const wrapper = mount(MarkdownViewer, {
      props: {
        content: markdownWithLink,
        showToolbar: false,
        workspaceId: 1,
        notebookId: 2,
      },
    })

    const html = wrapper.find(".markdown-content").html()
    expect(html).toContain("<a")
    // HTML entities are escaped in the output
    expect(html).toContain(
      'href="/api/v1/files/by-path/content?path=document.md&amp;workspace_id=1&amp;notebook_id=2"'
    )
    expect(html).toContain("Read More")
  })

  it("does not modify absolute URLs in images", () => {
    const markdownWithAbsoluteImage = "![External](https://example.com/image.png)"
    const wrapper = mount(MarkdownViewer, {
      props: {
        content: markdownWithAbsoluteImage,
        showToolbar: false,
        workspaceId: 1,
        notebookId: 2,
      },
    })

    const html = wrapper.find(".markdown-content").html()
    expect(html).toContain('src="https://example.com/image.png"')
  })

  it("does not modify external URLs in links", () => {
    const markdownWithExternalLink = "[External Link](https://example.com)"
    const wrapper = mount(MarkdownViewer, {
      props: {
        content: markdownWithExternalLink,
        showToolbar: false,
        workspaceId: 1,
        notebookId: 2,
      },
    })

    const html = wrapper.find(".markdown-content").html()
    expect(html).toContain('href="https://example.com"')
  })

  it("leaves images unchanged when no workspace/notebook context provided", () => {
    const markdownWithImage = "![Test Image](test-image.png)"
    const wrapper = mount(MarkdownViewer, {
      props: {
        content: markdownWithImage,
        showToolbar: false,
      },
    })

    const html = wrapper.find(".markdown-content").html()
    expect(html).toContain("<img")
    expect(html).toContain('src="test-image.png"')
  })

  it("handles images with relative paths", () => {
    const markdownWithRelativeImage = "![Test Image](./images/test.png)"
    const wrapper = mount(MarkdownViewer, {
      props: {
        content: markdownWithRelativeImage,
        showToolbar: false,
        workspaceId: 1,
        notebookId: 2,
      },
    })

    const html = wrapper.find(".markdown-content").html()
    expect(html).toContain("<img")
    // The path is URL-encoded and HTML entities are escaped
    expect(html).toContain(
      'src="/api/v1/files/by-path/content?path=.%2Fimages%2Ftest.png&amp;workspace_id=1&amp;notebook_id=2"'
    )
  })

  it("handles multiple images in the same markdown", () => {
    const markdownWithMultipleImages = "![Image 1](img1.png)\n\n![Image 2](img2.jpg)"
    const wrapper = mount(MarkdownViewer, {
      props: {
        content: markdownWithMultipleImages,
        showToolbar: false,
        workspaceId: 1,
        notebookId: 2,
      },
    })

    const html = wrapper.find(".markdown-content").html()
    // HTML entities are escaped in the output
    expect(html).toContain(
      'src="/api/v1/files/by-path/content?path=img1.png&amp;workspace_id=1&amp;notebook_id=2"'
    )
    expect(html).toContain(
      'src="/api/v1/files/by-path/content?path=img2.jpg&amp;workspace_id=1&amp;notebook_id=2"'
    )
  })
})
