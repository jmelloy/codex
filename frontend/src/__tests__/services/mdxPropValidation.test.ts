import { describe, it, expect } from "vitest"
import { validateProps, isSafeUrl } from "../../services/mdxPropValidation"
import { MDX_COMPONENT_SCHEMAS } from "../../services/mdxComponentSchemas"
import { buildEmbedUrl } from "../../services/mdxEmbed"

describe("validateProps", () => {
  it("coerces, applies defaults and parses JSON", () => {
    const r = validateProps(MDX_COMPONENT_SCHEMAS.Chart, { data: '[{"label":"a","value":1}]' })
    expect(r.valid).toBe(true)
    expect(r.props.type).toBe("bar")
    expect(r.props.height).toBe(240)
    expect(r.props.data).toEqual([{ label: "a", value: 1 }])
  })

  it("reports missing, unknown, bad enum, range and JSON errors", () => {
    expect(validateProps(MDX_COMPONENT_SCHEMAS.Chart, {}).errors[0]).toMatch(/Missing required/)
    expect(validateProps(MDX_COMPONENT_SCHEMAS.Chart, { data: "[", x: "1" }).errors).toHaveLength(2)
    expect(validateProps(MDX_COMPONENT_SCHEMAS.Chart, { data: "[]", type: "radar" }).valid).toBe(false)
    expect(validateProps(MDX_COMPONENT_SCHEMAS.Chart, { data: "[]", height: "5000" }).valid).toBe(false)
  })

  it("only allows http(s) and relative URLs", () => {
    expect(isSafeUrl("https://a.com/x")).toBe(true)
    expect(isSafeUrl("/api/v1/x")).toBe(true)
    expect(isSafeUrl("//evil.com")).toBe(false)
    expect(isSafeUrl("javascript:alert(1)")).toBe(false)
    expect(validateProps(MDX_COMPONENT_SCHEMAS.LiveData, { src: "data:text/html,x" }).valid).toBe(false)
  })
})

describe("buildEmbedUrl", () => {
  it("builds provider URLs for valid ids only", () => {
    expect(buildEmbedUrl("youtube", "dQw4w9WgXcQ")).toBe("https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ")
    expect(buildEmbedUrl("youtube", "x/../evil")).toBeNull()
    expect(buildEmbedUrl("evil", "abc")).toBeNull()
  })
})
