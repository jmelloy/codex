# MDX Components

All attributes are strings (JS expressions like `{...}` are rejected). Structured data is passed as JSON strings. Props are validated before render; invalid props show an error box listing the problems.

| Component | Props |
|---|---|
| `Todo` | `items` JSON `[{"text": string, "done": boolean}]`, or children lines `[x] done` / `[ ] open` |
| `Table` | `rows` (required) JSON array of arrays; `columns` JSON array; `caption` |
| `ImageGallery` | `images` (required) JSON `[{"src": string, "alt": string, "caption": string}]`; `columns` 1-6 (default 3) |
| `Chart` | `data` (required) JSON `[{"label": string, "value": number}]`; `type` bar\|line\|pie; `title`; `height` 80-800 |
| `LiveData` | `src` (required, http(s) or `/path`); `path` dot path into JSON; `label`; `interval` seconds 5-3600; `format` text\|number\|json |
| `Embed` | `provider` youtube\|vimeo\|loom\|codepen; `id` (strict per-provider pattern); `title`; `height` |

Shapes like `{"text": string}` show the expected key and value type, not literal JSON.

Examples:

```mdx
<Chart type="bar" title="Runs" data='[{"label":"Mon","value":3},{"label":"Tue","value":5}]' />
<Embed provider="youtube" id="dQw4w9WgXcQ" />
<LiveData src="/api/v1/health" path="status" label="Status" interval="10" />
<Todo items='[{"text":"Ship","done":true},{"text":"Docs"}]' />
```

## Security model

1. **Allowlist**: only components in `MDX_COMPONENT_REGISTRY` (backend `codex/core/mdx.py`, mirrored in `mdxComponentRegistry.ts`) resolve; others render an "unauthorized" placeholder.
2. **No JS in MDX**: ESM, `{...}` expressions and expression attributes are rejected at compile time; host elements `script/iframe/style/...`, `on*` handlers and script/data URLs are rejected.
3. **Prop validation** (`mdxPropValidation.ts`, `mdxComponentSchemas.ts`): types, ranges, enums, unknown props, and http(s)/relative-only URLs.
4. **Embed**: no arbitrary URLs; only provider + strictly-matched id, rendered in a `sandbox`ed iframe with no referrer.
5. **LiveData**: http(s)/relative URLs only, `credentials: "omit"`, minimum 5s interval, prototype keys blocked in path lookup. Note: because credentials are omitted, authenticated same-origin endpoints won't work.
6. All text is rendered via Vue text interpolation (no `v-html`).
