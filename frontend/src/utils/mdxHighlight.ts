/**
 * Lightweight MDX syntax highlighter for the block editor.
 *
 * Produces escaped HTML (spans with `mdx-tok-*` classes) that is rendered in a
 * mirror layer behind a transparent <textarea>, so all native textarea
 * behaviour (selection, IME, undo) is preserved. Output text content is always
 * identical to the input, which keeps the layers aligned.
 */

function escapeHtml(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
}

const span = (cls: string, text: string) =>
  `<span class="mdx-tok-${cls}">${escapeHtml(text)}</span>`

// Capitalized component tags, e.g. `<Calendar date="x" />` or `</Calendar>`.
const JSX_TAG_RE = /<\/?[A-Z][A-Za-z0-9]*(?:"[^"]*"|'[^']*'|[^<>"'])*>/g
const JSX_PARTS_RE = /^(<\/?)([A-Za-z0-9]+)((?:.|\n)*?)(\/?>)$/
const ATTR_RE = /([A-Za-z_:][\w:.-]*)(=)?("[^"]*"|'[^']*')?/g

function highlightJsxTag(tag: string): string {
  const m = JSX_PARTS_RE.exec(tag)
  if (!m) return span("tag", tag)
  const [, open, name, attrs, close] = m
  let attrHtml = ""
  let last = 0
  for (const a of attrs.matchAll(ATTR_RE)) {
    if (!a[0]) continue
    const idx = a.index ?? 0
    attrHtml += escapeHtml(attrs.slice(last, idx))
    attrHtml += span("attr", a[1])
    if (a[2]) attrHtml += escapeHtml(a[2])
    if (a[3]) attrHtml += span("string", a[3])
    last = idx + a[0].length
  }
  attrHtml += escapeHtml(attrs.slice(last))
  return span("punct", open) + span("tag", name) + attrHtml + span("punct", close)
}

function highlightInline(line: string): string {
  // Tokenize in one pass so replacements never overlap.
  const re = new RegExp(
    [
      "(`[^`\\n]*`)", // 1 inline code
      "(\\*\\*[^*\\n]+\\*\\*)", // 2 bold
      "(\\[[^\\]\\n]*\\]\\([^)\\n]*\\))", // 3 link
      "(" + JSX_TAG_RE.source + ")", // 4 jsx tag
      "(\\{[^{}\\n]*\\})", // 5 expression
    ].join("|"),
    "g",
  )
  let out = ""
  let last = 0
  for (const m of line.matchAll(re)) {
    const idx = m.index ?? 0
    out += escapeHtml(line.slice(last, idx))
    if (m[1]) out += span("code", m[1])
    else if (m[2]) out += span("bold", m[2])
    else if (m[3]) out += span("link", m[3])
    else if (m[4]) out += highlightJsxTag(m[4])
    else out += span("expr", m[5])
    last = idx + m[0].length
  }
  return out + escapeHtml(line.slice(last))
}

/** Convert MDX source to highlighted HTML; textContent equals `source`. */
export function highlightMdx(source: string): string {
  let inFence = false
  const lines = source.split("\n").map((line) => {
    if (/^\s*(```|~~~)/.test(line)) {
      inFence = !inFence
      return span("fence", line)
    }
    if (inFence) return span("code", line)
    if (/^\s*(import|export)\s/.test(line)) return span("expr", line)
    const heading = /^(#{1,6}\s)(.*)$/.exec(line)
    if (heading) return span("heading", heading[1] + heading[2])
    if (/^\s*>/.test(line)) return span("quote", line)
    return highlightInline(line)
  })
  // Trailing newline keeps the mirror's height in sync with the textarea.
  return lines.join("\n") + "\n"
}
