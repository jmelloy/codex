/** Prop schemas for MDX components that validate their input. Components not listed here validate themselves. */
import type { PropSchema } from "./mdxPropValidation"

export const EMBED_PROVIDERS = ["youtube", "vimeo", "loom", "codepen"] as const
export const CHART_TYPES = ["bar", "line", "pie"] as const

export const MDX_COMPONENT_SCHEMAS: Record<string, PropSchema> = {
  Calendar: {
    date: { type: "string", maxLength: 64 },
    start: { type: "string", maxLength: 64 },
    end: { type: "string", maxLength: 64 },
  },
  Todo: {
    items: { type: "json", description: 'JSON array of {"text": string, "done": boolean}' },
  },
  Table: {
    columns: { type: "json", description: "JSON array of column headings" },
    rows: { type: "json", required: true, description: "JSON array of row arrays" },
    caption: { type: "string", maxLength: 200 },
  },
  ImageGallery: {
    images: { type: "json", required: true, description: 'JSON array of {"src": string, "alt"?: string, "caption"?: string}' },
    columns: { type: "number", default: 3, min: 1, max: 6 },
  },
  Chart: {
    type: { type: "enum", values: CHART_TYPES, default: "bar" },
    data: { type: "json", required: true, description: 'JSON array of {"label": string, "value": number}' },
    title: { type: "string", maxLength: 200 },
    height: { type: "number", default: 240, min: 80, max: 800 },
  },
  LiveData: {
    src: { type: "url", required: true },
    path: { type: "string", maxLength: 200, description: "Dot path into the JSON response" },
    label: { type: "string", maxLength: 200 },
    interval: { type: "number", default: 30, min: 5, max: 3600, description: "Refresh seconds" },
    format: { type: "enum", values: ["text", "number", "json"], default: "text" },
  },
  Embed: {
    provider: { type: "enum", required: true, values: EMBED_PROVIDERS },
    id: { type: "string", required: true, maxLength: 100 },
    title: { type: "string", maxLength: 200 },
    height: { type: "number", default: 360, min: 100, max: 1000 },
  },
}
