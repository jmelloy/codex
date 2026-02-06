import { describe, it, expect } from "vitest"
import {
  getDisplayType,
  isTextType,
  isImageType,
  isVideoType,
  isAudioType,
} from "../../utils/contentType"

describe("contentType utilities", () => {
  describe("getDisplayType", () => {
    it.each([
      ["application/x-codex-view", "view"],
      // images
      ["image/jpeg", "image"],
      ["image/png", "image"],
      ["image/gif", "image"],
      ["image/webp", "image"],
      ["image/svg+xml", "image"],
      // video
      ["video/mp4", "video"],
      ["video/webm", "video"],
      ["video/ogg", "video"],
      // audio
      ["audio/mpeg", "audio"],
      ["audio/wav", "audio"],
      ["audio/ogg", "audio"],
      // text/structured
      ["text/markdown", "markdown"],
      ["markdown", "markdown"],
      ["text/html", "html"],
      ["application/json", "json"],
      ["application/xml", "xml"],
      ["text/xml", "xml"],
      ["application/pdf", "pdf"],
      // code
      ["text/x-python", "code"],
      ["text/x-java", "code"],
      ["text/plain", "code"],
      ["application/javascript", "code"],
      ["application/typescript", "code"],
      ["text/css", "code"],
      ["text/python", "code"],
      ["application/x-java", "code"],
      ["text/x-c++", "code"],
      // generic text
      ["text/csv", "text"],
      ["text/rtf", "text"],
      // binary
      ["application/octet-stream", "binary"],
      ["application/zip", "binary"],
      ["unknown/type", "binary"],
    ])("returns '%s' → '%s'", (mime, expected) => {
      expect(getDisplayType(mime)).toBe(expected)
    })
  })

  describe("isTextType", () => {
    it.each([
      ["text/plain", true],
      ["text/markdown", true],
      ["text/html", true],
      ["text/css", true],
      ["application/json", true],
      ["application/xml", true],
      ["application/x-codex-view", true],
      ["image/png", false],
      ["video/mp4", false],
      ["audio/mpeg", false],
      ["application/pdf", false],
      ["application/zip", false],
    ])("isTextType('%s') → %s", (mime, expected) => {
      expect(isTextType(mime)).toBe(expected)
    })
  })

  describe("isImageType", () => {
    it.each([
      ["image/jpeg", true],
      ["image/png", true],
      ["image/gif", true],
      ["image/webp", true],
      ["image/svg+xml", true],
      ["text/plain", false],
      ["video/mp4", false],
      ["application/pdf", false],
    ])("isImageType('%s') → %s", (mime, expected) => {
      expect(isImageType(mime)).toBe(expected)
    })
  })

  describe("isVideoType", () => {
    it.each([
      ["video/mp4", true],
      ["video/webm", true],
      ["video/ogg", true],
      ["video/quicktime", true],
      ["text/plain", false],
      ["image/png", false],
      ["audio/mpeg", false],
    ])("isVideoType('%s') → %s", (mime, expected) => {
      expect(isVideoType(mime)).toBe(expected)
    })
  })

  describe("isAudioType", () => {
    it.each([
      ["audio/mpeg", true],
      ["audio/wav", true],
      ["audio/ogg", true],
      ["audio/flac", true],
      ["text/plain", false],
      ["image/png", false],
      ["video/mp4", false],
    ])("isAudioType('%s') → %s", (mime, expected) => {
      expect(isAudioType(mime)).toBe(expected)
    })
  })
})
