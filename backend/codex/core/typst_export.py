"""MDX -> Typst transformation and PDF export.

This is a best-effort text-based transformer, not a full Markdown/MDX AST
compiler: it is intentionally line/regex based rather than parsing MDX into a
real AST, matching the transformer sketched in issue #599 ("Handle custom
components (fallback to simplified representation)"). It covers the subset
of Markdown formatting blocks actually produce (headings, lists, blockquotes,
fenced code, links, images, bold/italic) and renders unrecognized MDX
components as a labeled fallback box rather than attempting to execute them,
since Typst has no JS runtime to render interactive components into.

Compilation to PDF bytes is delegated to the ``typst`` package (PyO3 bindings
around the Rust typst compiler), so no external Typst CLI install is required.
"""

from __future__ import annotations

import re
import tempfile
from pathlib import Path
from typing import Any

import typst

from codex.core.mdx import MDX_COMPONENT_REGISTRY

# Characters with syntactic meaning in Typst markup mode that must be escaped
# when they appear in literal text (i.e. text we are not deliberately emitting
# as Typst syntax ourselves).
_TYPST_MARKUP_ESCAPE_RE = re.compile(r"[\\#$@_*`<>\[\]]")

# Fenced code blocks are extracted before any other processing so their
# contents are never mistaken for headings/lists/components and never escaped
# (Typst raw blocks use the same triple-backtick syntax as Markdown, so the
# fenced text can be re-emitted almost verbatim).
_FENCE_RE = re.compile(r"^```([^\n`]*)\n(.*?)^```[ \t]*$", re.DOTALL | re.MULTILINE)

# Self-closing (`<Name .../>`) or paired (`<Name>...</Name>`) capitalized JSX
# tags — the same convention codex.core.mdx.extract_component_names uses to
# recognize MDX components as opposed to lowercase host HTML elements.
_COMPONENT_RE = re.compile(
    r"<(?P<name>[A-Z][A-Za-z0-9]*)(?P<attrs>[^>]*?)(?:/>|>(?P<children>.*?)</(?P=name)>)",
    re.DOTALL,
)

_ATTR_RE = re.compile(r'([A-Za-z_][A-Za-z0-9_-]*)\s*=\s*\{?"([^"]*)"\}?')

# Inline formatting, checked in priority order so e.g. inline code protects its
# contents from bold/italic/link substitution.
_INLINE_RE = re.compile(
    r"`(?P<code>[^`]+)`"
    r"|!\[(?P<imgalt>[^\]]*)\]\((?P<imgurl>[^)\s]+)\)"
    r"|\[(?P<linktext>[^\]]*)\]\((?P<linkurl>[^)\s]+)\)"
    r"|\*\*(?P<boldstar>[^*]+)\*\*"
    r"|__(?P<boldunder>[^_]+)__"
    r"|\*(?P<italicstar>[^*]+)\*"
    r"|_(?P<italicunder>[^_]+)_"
)

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
_ULIST_RE = re.compile(r"^[-*+]\s+(.*)$")
_OLIST_RE = re.compile(r"^\d+\.\s+(.*)$")
_QUOTE_RE = re.compile(r"^>\s?(.*)$")
_HR_RE = re.compile(r"^(-{3,}|\*{3,}|_{3,})$")


class TypstCompileError(RuntimeError):
    """Raised when the Typst compiler fails to produce a PDF."""


def escape_typst_text(text: str) -> str:
    """Escape characters that are syntactically significant in Typst markup mode."""
    return _TYPST_MARKUP_ESCAPE_RE.sub(lambda m: "\\" + m.group(0), text)


def escape_typst_string_literal(text: str) -> str:
    """Escape a value for embedding inside a Typst double-quoted string literal."""
    return text.replace("\\", "\\\\").replace('"', '\\"')


def _convert_inline(text: str) -> str:
    """Convert inline Markdown spans (code/links/images/bold/italic) to Typst markup."""
    out: list[str] = []
    pos = 0
    for m in _INLINE_RE.finditer(text):
        out.append(escape_typst_text(text[pos : m.start()]))
        if m.group("code") is not None:
            out.append(f"`{m.group('code')}`")
        elif m.group("imgalt") is not None:
            alt = escape_typst_text(m.group("imgalt"))
            url = escape_typst_text(m.group("imgurl"))
            out.append(f"_[Image: {alt or url}]_")
        elif m.group("linktext") is not None:
            url = escape_typst_string_literal(m.group("linkurl"))
            out.append(f'#link("{url}")[{escape_typst_text(m.group("linktext"))}]')
        elif m.group("boldstar") is not None:
            out.append(f"*{escape_typst_text(m.group('boldstar'))}*")
        elif m.group("boldunder") is not None:
            out.append(f"*{escape_typst_text(m.group('boldunder'))}*")
        elif m.group("italicstar") is not None:
            out.append(f"_{escape_typst_text(m.group('italicstar'))}_")
        elif m.group("italicunder") is not None:
            out.append(f"_{escape_typst_text(m.group('italicunder'))}_")
        pos = m.end()
    out.append(escape_typst_text(text[pos:]))
    return "".join(out)


def _parse_component_attrs(attrs_str: str) -> dict[str, str]:
    return {m.group(1): m.group(2) for m in _ATTR_RE.finditer(attrs_str)}


def fallback_box(heading: str, subheading: str | None = None, details: dict[str, str] | None = None) -> str:
    """A bordered Typst block used as the PDF stand-in for content that can't render statically."""
    lines = [f"*{escape_typst_text(heading)}*"]
    if subheading:
        lines.append(f"#linebreak() _{escape_typst_text(subheading)}_")
    for key, value in (details or {}).items():
        lines.append(f"#linebreak() {escape_typst_text(key)}: {escape_typst_text(value)}")
    body = " ".join(lines)
    return f"#block(stroke: 0.5pt, inset: 8pt, radius: 4pt, fill: luma(245))[{body}]"


def _component_fallback(name: str, attrs: dict[str, str]) -> str:
    description = MDX_COMPONENT_REGISTRY.get(name, "Unrecognized component — not rendered in PDF export")
    return fallback_box(f"{name} component", description, attrs)


def _stash_components(content: str) -> tuple[str, list[str]]:
    """Replace MDX component tags with a placeholder holding their Typst fallback box.

    The fallback box is itself Typst markup (``#block(...)[...]``), so it must
    survive `_convert_inline()`'s per-character escaping of `#`/`[`/`]` later
    in `mdx_to_typst()` — stashed the same way fenced code blocks are, and
    restored verbatim after line-by-line inline conversion runs.
    """
    directives: list[str] = []

    def _stash(m: re.Match[str]) -> str:
        directives.append(_component_fallback(m.group("name"), _parse_component_attrs(m.group("attrs") or "")))
        return f"\x00COMPONENT{len(directives) - 1}\x00"

    return _COMPONENT_RE.sub(_stash, content), directives


def _restore_components(content: str, directives: list[str]) -> str:
    for i, directive in enumerate(directives):
        content = content.replace(f"\x00COMPONENT{i}\x00", directive)
    return content


def _extract_fences(content: str) -> tuple[str, list[str]]:
    """Pull fenced code blocks out into placeholders so they survive untouched."""
    fences: list[str] = []

    def _stash(m: re.Match[str]) -> str:
        lang = m.group(1).strip()
        code = m.group(2)
        if code.endswith("\n"):
            code = code[:-1]
        fences.append(f"```{lang}\n{code}\n```")
        return f"\x00FENCE{len(fences) - 1}\x00"

    return _FENCE_RE.sub(_stash, content), fences


def _restore_fences(content: str, fences: list[str]) -> str:
    for i, fence in enumerate(fences):
        content = content.replace(f"\x00FENCE{i}\x00", fence)
    return content


def mdx_to_typst(content: str) -> str:
    """Convert an MDX/Markdown block body into a Typst markup fragment.

    Fenced code blocks pass through unchanged (raw blocks share syntax), MDX
    component tags become a labeled fallback box (see module docstring), and
    the remaining Markdown constructs — headings, ordered/unordered lists,
    blockquotes, horizontal rules, and inline bold/italic/code/links/images —
    are mapped to their Typst equivalents. Anything else is treated as plain
    text and escaped.
    """
    without_fences, fences = _extract_fences(content)
    without_components, component_directives = _stash_components(without_fences)

    out_lines: list[str] = []
    quote_buffer: list[str] = []

    def _flush_quote() -> None:
        if quote_buffer:
            joined = " ".join(quote_buffer)
            out_lines.append(f"#quote(block: true)[{joined}]")
            quote_buffer.clear()

    for line in without_components.split("\n"):
        stripped = line.strip()

        quote_match = _QUOTE_RE.match(stripped)
        if quote_match:
            quote_buffer.append(_convert_inline(quote_match.group(1)))
            continue
        _flush_quote()

        if not stripped:
            out_lines.append("")
            continue

        heading_match = _HEADING_RE.match(stripped)
        if heading_match:
            level = len(heading_match.group(1))
            out_lines.append(f"{'=' * level} {_convert_inline(heading_match.group(2))}")
            continue

        if _HR_RE.match(stripped):
            out_lines.append("#line(length: 100%)")
            continue

        ulist_match = _ULIST_RE.match(stripped)
        if ulist_match:
            out_lines.append(f"- {_convert_inline(ulist_match.group(1))}")
            continue

        olist_match = _OLIST_RE.match(stripped)
        if olist_match:
            out_lines.append(f"+ {_convert_inline(olist_match.group(1))}")
            continue

        if stripped.startswith("\x00FENCE"):
            out_lines.append(stripped)
            continue

        out_lines.append(_convert_inline(line))

    _flush_quote()
    result = _restore_fences("\n".join(out_lines), fences)
    return _restore_components(result, component_directives)


def render_typst_document(body: str, title: str | None = None) -> str:
    """Wrap a Typst markup body with page setup and an optional document title."""
    header = ["#set page(margin: 1in)"]
    if title:
        header.append(f'#set document(title: "{escape_typst_string_literal(title)}")')
        header.append(f"= {_convert_inline(title)}")
    return "\n".join(header) + "\n\n" + body


def compile_typst_to_pdf(typst_source: str) -> bytes:
    """Compile Typst markup source to PDF bytes using the embedded Rust compiler."""
    with tempfile.TemporaryDirectory() as tmpdir:
        typ_path = Path(tmpdir) / "export.typ"
        typ_path.write_text(typst_source, encoding="utf-8")
        try:
            result = typst.compile(str(typ_path), format="pdf")
        except Exception as exc:  # typst raises its own TypstError subclasses
            raise TypstCompileError(str(exc)) from exc
        if not isinstance(result, bytes):
            raise TypstCompileError(f"Unexpected typst.compile() result type: {type(result)!r}")
        return result


def export_content_to_pdf(content: str, title: str | None = None) -> bytes:
    """Convert MDX/Markdown body text directly to PDF bytes."""
    typst_source = render_typst_document(mdx_to_typst(content), title=title)
    return compile_typst_to_pdf(typst_source)


def leaf_block_to_typst(block: Any, notebook_path: Path) -> str:
    """Render a single non-page block's contribution to a Typst document body.

    Prose blocks (mdx/legacy/markdown) are transformed via mdx_to_typst().
    Everything else (image/file/database/api/embed) has no static PDF
    rendering, so it gets the same labeled fallback box as an unauthorized
    MDX component.
    """
    from codex.core.blocks import get_block_content
    from codex.db.models.notebook import PROSE_CONTENT_FORMATS

    if block.content_format in PROSE_CONTENT_FORMATS:
        raw = get_block_content(notebook_path, block) or ""
        rendered = block.render(raw)
        return mdx_to_typst(rendered["content"])

    details = {}
    if block.filename:
        details["file"] = block.filename
    return fallback_box(
        block.title or block.block_type,
        f"{block.block_type} block — not rendered in PDF export",
        details,
    )


def export_block_to_pdf(notebook_path: Path, notebook_id: int, block: Any, nb_session: Any) -> bytes:
    """Export a single block or a whole page (with its children) to PDF bytes.

    Page blocks have no file content of their own (they're backed by a
    ``.codex-page.json`` folder, see codex.core.blocks) — for those, every
    child block is rendered in order and concatenated into one document.
    """
    from codex.core.blocks import BLOCK_TYPE_PAGE, get_block_children

    if block.block_type == BLOCK_TYPE_PAGE:
        children = get_block_children(notebook_id, block.block_id, nb_session)
        body = "\n\n".join(leaf_block_to_typst(child, notebook_path) for child in children)
        typst_source = render_typst_document(body, title=block.title)
    else:
        body = leaf_block_to_typst(block, notebook_path)
        typst_source = render_typst_document(body, title=block.title)

    return compile_typst_to_pdf(typst_source)
