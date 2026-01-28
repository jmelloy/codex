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
    it("returns 'view' for codex view files", () => {
      expect(getDisplayType("application/x-codex-view")).toBe("view")
    })

    describe("image types", () => {
      it("returns 'image' for image MIME types", () => {
        expect(getDisplayType("image/jpeg")).toBe("image")
        expect(getDisplayType("image/png")).toBe("image")
        expect(getDisplayType("image/gif")).toBe("image")
        expect(getDisplayType("image/webp")).toBe("image")
        expect(getDisplayType("image/svg+xml")).toBe("image")
      })
    })

    describe("video types", () => {
      it("returns 'video' for video MIME types", () => {
        expect(getDisplayType("video/mp4")).toBe("video")
        expect(getDisplayType("video/webm")).toBe("video")
        expect(getDisplayType("video/ogg")).toBe("video")
      })
    })

    describe("audio types", () => {
      it("returns 'audio' for audio MIME types", () => {
        expect(getDisplayType("audio/mpeg")).toBe("audio")
        expect(getDisplayType("audio/wav")).toBe("audio")
        expect(getDisplayType("audio/ogg")).toBe("audio")
      })
    })

    describe("text types", () => {
      it("returns 'markdown' for markdown content", () => {
        expect(getDisplayType("text/markdown")).toBe("markdown")
        expect(getDisplayType("markdown")).toBe("markdown")
      })

      it("returns 'html' for HTML content", () => {
        expect(getDisplayType("text/html")).toBe("html")
      })

      it("returns 'json' for JSON content", () => {
        expect(getDisplayType("application/json")).toBe("json")
      })

      it("returns 'xml' for XML content", () => {
        expect(getDisplayType("application/xml")).toBe("xml")
        expect(getDisplayType("text/xml")).toBe("xml")
      })

      it("returns 'pdf' for PDF content", () => {
        expect(getDisplayType("application/pdf")).toBe("pdf")
      })
    })

    describe("code types", () => {
      it("returns 'code' for code file types", () => {
        expect(getDisplayType("text/x-python")).toBe("code")
        expect(getDisplayType("text/x-java")).toBe("code")
        expect(getDisplayType("text/plain")).toBe("code")
        expect(getDisplayType("application/javascript")).toBe("code")
        expect(getDisplayType("application/typescript")).toBe("code")
        expect(getDisplayType("text/css")).toBe("code")
      })

      it("returns 'code' for language-specific types", () => {
        expect(getDisplayType("text/python")).toBe("code")
        expect(getDisplayType("application/x-java")).toBe("code")
        expect(getDisplayType("text/x-c++")).toBe("code")
      })
    })

    describe("generic text types", () => {
      it("returns 'text' for other text types", () => {
        expect(getDisplayType("text/csv")).toBe("text")
        expect(getDisplayType("text/rtf")).toBe("text")
      })
    })

    describe("binary types", () => {
      it("returns 'binary' for unknown types", () => {
        expect(getDisplayType("application/octet-stream")).toBe("binary")
        expect(getDisplayType("application/zip")).toBe("binary")
        expect(getDisplayType("unknown/type")).toBe("binary")
      })
    })
  })

  describe("isTextType", () => {
    it("returns true for text/* types", () => {
      expect(isTextType("text/plain")).toBe(true)
      expect(isTextType("text/markdown")).toBe(true)
      expect(isTextType("text/html")).toBe(true)
      expect(isTextType("text/css")).toBe(true)
    })

    it("returns true for JSON", () => {
      expect(isTextType("application/json")).toBe(true)
    })

    it("returns true for XML", () => {
      expect(isTextType("application/xml")).toBe(true)
    })

    it("returns true for codex view files", () => {
      expect(isTextType("application/x-codex-view")).toBe(true)
    })

    it("returns false for non-text types", () => {
      expect(isTextType("image/png")).toBe(false)
      expect(isTextType("video/mp4")).toBe(false)
      expect(isTextType("audio/mpeg")).toBe(false)
      expect(isTextType("application/pdf")).toBe(false)
      expect(isTextType("application/zip")).toBe(false)
    })
  })

  describe("isImageType", () => {
    it("returns true for image types", () => {
      expect(isImageType("image/jpeg")).toBe(true)
      expect(isImageType("image/png")).toBe(true)
      expect(isImageType("image/gif")).toBe(true)
      expect(isImageType("image/webp")).toBe(true)
      expect(isImageType("image/svg+xml")).toBe(true)
    })

    it("returns false for non-image types", () => {
      expect(isImageType("text/plain")).toBe(false)
      expect(isImageType("video/mp4")).toBe(false)
      expect(isImageType("application/pdf")).toBe(false)
    })
  })

  describe("isVideoType", () => {
    it("returns true for video types", () => {
      expect(isVideoType("video/mp4")).toBe(true)
      expect(isVideoType("video/webm")).toBe(true)
      expect(isVideoType("video/ogg")).toBe(true)
      expect(isVideoType("video/quicktime")).toBe(true)
    })

    it("returns false for non-video types", () => {
      expect(isVideoType("text/plain")).toBe(false)
      expect(isVideoType("image/png")).toBe(false)
      expect(isVideoType("audio/mpeg")).toBe(false)
    })
  })

  describe("isAudioType", () => {
    it("returns true for audio types", () => {
      expect(isAudioType("audio/mpeg")).toBe(true)
      expect(isAudioType("audio/wav")).toBe(true)
      expect(isAudioType("audio/ogg")).toBe(true)
      expect(isAudioType("audio/flac")).toBe(true)
    })

    it("returns false for non-audio types", () => {
      expect(isAudioType("text/plain")).toBe(false)
      expect(isAudioType("image/png")).toBe(false)
      expect(isAudioType("video/mp4")).toBe(false)
    })
  })
})
