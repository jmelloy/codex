import { describe, it, expect } from "vitest"
import {
  ALLOWED_COMPONENT_NAMES,
  MDX_COMPONENT_REGISTRY,
  extractComponentNames,
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

})

import { validateComponentProps } from "../../services/mdxComponentRegistry"

describe("validateComponentProps", () => {
  it("accepts valid props", () => {
    expect(validateComponentProps("Calendar", { date: "2026-01-01" })).toEqual([])
    expect(validateComponentProps("GitHubIssues", { repo: "a/b", limit: "5" })).toEqual([])
  })
  it("flags missing required props", () => {
    expect(validateComponentProps("LinkPreview", {})).toEqual(['missing required prop "url"'])
  })
  it("flags unknown props and bad types", () => {
    expect(validateComponentProps("Calendar", { bogus: "x" })).toEqual(['unknown prop "bogus"'])
    expect(validateComponentProps("GitHubIssues", { limit: "abc" })).toEqual(['prop "limit" must be a number'])
  })
  it("ignores children and unregistered components", () => {
    expect(validateComponentProps("CodeBlock", { children: "x" })).toEqual([])
    expect(validateComponentProps("Nope", { a: 1 })).toEqual([])
  })
})
