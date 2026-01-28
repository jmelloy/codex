import { describe, it, expect, beforeEach, afterEach, vi } from "vitest"
import { showToast } from "../../utils/toast"

describe("toast utility", () => {
  beforeEach(() => {
    // Clean up any existing toasts
    document.body.innerHTML = ""
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it("creates a toast element in the DOM", () => {
    showToast({ message: "Test message" })

    const toast = document.body.querySelector("div")
    expect(toast).not.toBeNull()
    expect(toast?.textContent).toBe("Test message")
  })

  it("uses success color by default", () => {
    showToast({ message: "Success message" })

    const toast = document.body.querySelector("div")
    // happy-dom may return hex or rgb depending on environment
    expect(toast?.style.background).toMatch(/(#48bb78|rgb\(72,\s*187,\s*120\))/)
  })

  it("uses error color for error type", () => {
    showToast({ message: "Error message", type: "error" })

    const toast = document.body.querySelector("div")
    expect(toast?.style.background).toMatch(/(#f56565|rgb\(245,\s*101,\s*101\))/)
  })

  it("uses info color for info type", () => {
    showToast({ message: "Info message", type: "info" })

    const toast = document.body.querySelector("div")
    expect(toast?.style.background).toMatch(/(#667eea|rgb\(102,\s*126,\s*234\))/)
  })

  it("applies correct positioning styles", () => {
    showToast({ message: "Positioned toast" })

    const toast = document.body.querySelector("div")
    expect(toast?.style.position).toBe("fixed")
    expect(toast?.style.bottom).toBe("20px")
    expect(toast?.style.right).toBe("20px")
  })

  it("applies correct visual styles", () => {
    showToast({ message: "Styled toast" })

    const toast = document.body.querySelector("div")
    expect(toast?.style.color).toBe("white")
    expect(toast?.style.borderRadius).toBe("6px")
    expect(toast?.style.zIndex).toBe("1000")
  })

  it("fades out after default duration", () => {
    showToast({ message: "Fading toast" })

    const toast = document.body.querySelector("div")
    expect(toast?.style.opacity).toBe("")

    // Advance time to trigger fade
    vi.advanceTimersByTime(2000)
    expect(toast?.style.opacity).toBe("0")
  })

  it("uses custom duration", () => {
    showToast({ message: "Custom duration", duration: 5000 })

    const toast = document.body.querySelector("div")

    // Should not fade yet at 2 seconds
    vi.advanceTimersByTime(2000)
    expect(toast?.style.opacity).toBe("")

    // Should fade at 5 seconds
    vi.advanceTimersByTime(3000)
    expect(toast?.style.opacity).toBe("0")
  })

  it("removes toast from DOM after fade", () => {
    showToast({ message: "Removable toast" })

    expect(document.body.querySelector("div")).not.toBeNull()

    // Advance through fade delay
    vi.advanceTimersByTime(2000)
    // Advance through removal delay
    vi.advanceTimersByTime(300)

    expect(document.body.querySelector("div")).toBeNull()
  })

  it("can show multiple toasts", () => {
    showToast({ message: "Toast 1" })
    showToast({ message: "Toast 2" })

    const toasts = document.body.querySelectorAll("div")
    expect(toasts).toHaveLength(2)
  })
})
