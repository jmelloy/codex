import { describe, it, expect } from "vitest"
import {
  ALLOWED_COMPONENT_NAMES,
  MDX_COMPONENT_REGISTRY,
  extractComponentNames,
  findUnauthorizedComponents,
} from "../../services/mdxComponentRegistry"

describe("mdxComponentRegistry", () => {
  it("registry keys match the allowlist", () => {
    expect(ALLOWED_COMPONENT_NAMES).toEqual(new Set(Object.keys(MDX_COMPONENT_REGISTRY)))
  })

  it("registry matches the documented backend component set", () => {
    expect(ALLOWED_COMPONENT_NAMES).toEqual(
      new Set([
        "Calendar",
        "CodeBlock",
        "Weather",
        "LinkPreview",
        "GitHubIssues",
        "GitHubPulls",
        "GitHubRepo",
        "ApiBlock",
        "DatabaseBlock",
      ]),
    )
  })

  describe("extractComponentNames", () => {
    it("finds capitalized self-closing and paired tags", () => {
      const names = extractComponentNames(
        'Text <Calendar/> more <Weather x="1"></Weather> <p>html</p>',
      )
      expect(names).toEqual(new Set(["Calendar", "Weather"]))
    })

    it("ignores lowercase host elements", () => {
      const names = extractComponentNames("<div><span>hi</span></div>")
      expect(names.size).toBe(0)
    })
  })

  describe("findUnauthorizedComponents", () => {
    it("excludes allowlisted components", () => {
      expect(findUnauthorizedComponents("<Calendar/>")).toEqual(new Set())
    })

    it("flags unknown components", () => {
      expect(findUnauthorizedComponents("<Calendar/><EvilComponent/>")).toEqual(
        new Set(["EvilComponent"]),
      )
    })
  })
})
