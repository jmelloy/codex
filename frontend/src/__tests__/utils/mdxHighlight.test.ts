import { describe, it, expect } from "vitest"
import { highlightMdx } from "../../utils/mdxHighlight"

function text(html: string) {
  const d = document.createElement("div")
  d.innerHTML = html
  return d.textContent
}

describe("highlightMdx", () => {
  it("preserves source text (plus trailing newline)", () => {
    const src =
      '# Title\n<Calendar date="2026-01-01" />\n```js\nlet a = <b>\n```\n**bold** `x` [l](u) {1}'
    expect(text(highlightMdx(src))).toBe(src + "\n")
  })
  it("tags components and attributes", () => {
    const html = highlightMdx('<Weather location="NYC" />')
    expect(html).toContain("mdx-tok-tag")
    expect(html).toContain("mdx-tok-attr")
    expect(html).toContain("mdx-tok-string")
  })
  it("escapes html", () => {
    expect(highlightMdx("<script>")).not.toContain("<script>")
  })
})
