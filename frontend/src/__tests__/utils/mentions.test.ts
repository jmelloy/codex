import { describe, it, expect } from "vitest"
import { parseMentions, findActiveMentionQuery, insertMention } from "../../utils/mentions"

describe("parseMentions", () => {
  it("returns an empty array when there are no mentions", () => {
    expect(parseMentions("no mentions here")).toEqual([])
  })

  it("extracts a single handle", () => {
    expect(parseMentions("hey @jane can you take a look?")).toEqual(["jane"])
  })

  it("extracts multiple distinct handles in first-seen order", () => {
    expect(parseMentions("@bob and @alice, cc @bob")).toEqual(["bob", "alice"])
  })

  it("allows dots, hyphens, and underscores in handles", () => {
    expect(parseMentions("@jane.doe @a-b_c")).toEqual(["jane.doe", "a-b_c"])
  })

  it("does not match an email-like token as a mention", () => {
    expect(parseMentions("contact me at jane@example.com")).toEqual([])
  })

  it("does not match a bare @ with no handle", () => {
    expect(parseMentions("this is weird @ right")).toEqual([])
  })

  it("matches a mention at the very start of the text", () => {
    expect(parseMentions("@jane thanks!")).toEqual(["jane"])
  })
})

describe("findActiveMentionQuery", () => {
  it("returns null when there is no @ before the cursor", () => {
    expect(findActiveMentionQuery("hello world", 5)).toBeNull()
  })

  it("finds an in-progress mention right after the @", () => {
    const text = "hey @ja"
    expect(findActiveMentionQuery(text, text.length)).toEqual({ start: 4, end: 7, query: "ja" })
  })

  it("finds an in-progress mention with an empty query", () => {
    const text = "hey @"
    expect(findActiveMentionQuery(text, text.length)).toEqual({ start: 4, end: 5, query: "" })
  })

  it("returns null once a space ends the mention", () => {
    const text = "hey @jane "
    expect(findActiveMentionQuery(text, text.length)).toBeNull()
  })

  it("returns null when the @ is part of an email-like token", () => {
    const text = "jane@example"
    expect(findActiveMentionQuery(text, text.length)).toBeNull()
  })

  it("returns null for a cursor position outside the text bounds", () => {
    expect(findActiveMentionQuery("hello", -1)).toBeNull()
    expect(findActiveMentionQuery("hello", 100)).toBeNull()
  })

  it("finds the mention the cursor is inside, ignoring text after the cursor", () => {
    const text = "@jane and @bob"
    // Cursor placed right after "@ja" within the first handle.
    expect(findActiveMentionQuery(text, 3)).toEqual({ start: 0, end: 3, query: "ja" })
  })
})

describe("insertMention", () => {
  it("replaces the active mention query with the full handle plus a trailing space", () => {
    const text = "hey @ja"
    const query = findActiveMentionQuery(text, text.length)!
    const result = insertMention(text, query, "jane")
    expect(result.text).toBe("hey @jane ")
    expect(result.cursor).toBe(result.text.length)
  })

  it("preserves text after the mention", () => {
    const text = "hey @ja, are you free?"
    const query = { start: 4, end: 7, query: "ja" }
    const result = insertMention(text, query, "jane")
    expect(result.text).toBe("hey @jane , are you free?")
    expect(result.cursor).toBe("hey @jane ".length)
  })
})
