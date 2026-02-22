import { describe, it, expect, beforeEach, afterEach, vi } from "vitest"
import type { FileChangeEvent } from "../../services/websocket"

// We need to mock WebSocket before importing the service
class MockWebSocket {
  static readonly CONNECTING = 0
  static readonly OPEN = 1
  static readonly CLOSING = 2
  static readonly CLOSED = 3

  readonly CONNECTING = 0
  readonly OPEN = 1
  readonly CLOSING = 2
  readonly CLOSED = 3

  url: string
  readyState: number = MockWebSocket.CONNECTING

  onopen: ((ev: Event) => void) | null = null
  onmessage: ((ev: MessageEvent) => void) | null = null
  onclose: ((ev: CloseEvent) => void) | null = null
  onerror: ((ev: Event) => void) | null = null

  sent: string[] = []
  closed = false

  constructor(url: string) {
    this.url = url
    MockWebSocket.instances.push(this)
  }

  send(data: string) {
    this.sent.push(data)
  }

  close() {
    this.closed = true
    this.readyState = MockWebSocket.CLOSED
    if (this.onclose) {
      this.onclose(new CloseEvent("close"))
    }
  }

  // Helpers for tests
  simulateOpen() {
    this.readyState = MockWebSocket.OPEN
    if (this.onopen) {
      this.onopen(new Event("open"))
    }
  }

  simulateMessage(data: any) {
    if (this.onmessage) {
      this.onmessage(new MessageEvent("message", { data: JSON.stringify(data) }))
    }
  }

  simulateRawMessage(data: string) {
    if (this.onmessage) {
      this.onmessage(new MessageEvent("message", { data }))
    }
  }

  static instances: MockWebSocket[] = []
  static reset() {
    MockWebSocket.instances = []
  }
}

// Install mock before import
vi.stubGlobal("WebSocket", MockWebSocket)

// Dynamic import so the module sees our mock WebSocket
const { websocketService } = await import("../../services/websocket")

describe("WebSocket Service", () => {
  beforeEach(() => {
    MockWebSocket.reset()
    websocketService.disconnectAll()
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it("connects to correct URL based on location", () => {
    // happy-dom defaults: http://localhost:3000
    websocketService.connect(1)

    expect(MockWebSocket.instances).toHaveLength(1)
    const ws = MockWebSocket.instances[0]
    expect(ws.url).toContain("/api/v1/ws/notebooks/1")
  })

  it("does not create duplicate connections", () => {
    websocketService.connect(1)
    websocketService.connect(1)

    expect(MockWebSocket.instances).toHaveLength(1)
  })

  it("reports connection status", () => {
    expect(websocketService.isConnected(1)).toBe(false)

    websocketService.connect(1)
    expect(websocketService.isConnected(1)).toBe(false) // still connecting

    MockWebSocket.instances[0].simulateOpen()
    expect(websocketService.isConnected(1)).toBe(true)
  })

  it("notifies connection handlers on open", () => {
    const handler = vi.fn()
    websocketService.onConnectionChange(handler)

    websocketService.connect(1)
    MockWebSocket.instances[0].simulateOpen()

    expect(handler).toHaveBeenCalledWith(true, 1)
  })

  it("notifies connection handlers on close", () => {
    const handler = vi.fn()
    websocketService.onConnectionChange(handler)

    websocketService.connect(1)
    const ws = MockWebSocket.instances[0]
    ws.simulateOpen()
    handler.mockClear()

    ws.close()

    expect(handler).toHaveBeenCalledWith(false, 1)
  })

  it("dispatches file change events to handlers", () => {
    const handler = vi.fn()
    websocketService.onFileChange(handler)

    websocketService.connect(1)
    const ws = MockWebSocket.instances[0]
    ws.simulateOpen()

    const event: FileChangeEvent = {
      type: "file_change",
      notebook_id: 1,
      event_type: "modified",
      path: "/test.md",
      timestamp: "2024-01-01T00:00:00Z",
    }

    ws.simulateMessage(event)

    expect(handler).toHaveBeenCalledWith(event)
  })

  it("ignores non-file-change messages", () => {
    const handler = vi.fn()
    websocketService.onFileChange(handler)

    websocketService.connect(1)
    const ws = MockWebSocket.instances[0]
    ws.simulateOpen()

    ws.simulateMessage({ type: "connected", notebook_id: 1, message: "connected" })

    expect(handler).not.toHaveBeenCalled()
  })

  it("ignores pong messages without warning", () => {
    const consoleSpy = vi.spyOn(console, "warn").mockImplementation(() => {})

    websocketService.connect(1)
    const ws = MockWebSocket.instances[0]
    ws.simulateOpen()

    ws.simulateRawMessage("pong")

    expect(consoleSpy).not.toHaveBeenCalled()
    consoleSpy.mockRestore()
  })

  it("unsubscribes handlers via returned function", () => {
    const handler = vi.fn()
    const unsub = websocketService.onFileChange(handler)

    unsub()

    websocketService.connect(1)
    const ws = MockWebSocket.instances[0]
    ws.simulateOpen()
    ws.simulateMessage({
      type: "file_change",
      notebook_id: 1,
      event_type: "created",
      path: "/new.md",
      timestamp: "2024-01-01T00:00:00Z",
    })

    expect(handler).not.toHaveBeenCalled()
  })

  it("unsubscribes connection handlers via returned function", () => {
    const handler = vi.fn()
    const unsub = websocketService.onConnectionChange(handler)

    unsub()

    websocketService.connect(1)
    MockWebSocket.instances[0].simulateOpen()

    expect(handler).not.toHaveBeenCalled()
  })

  it("disconnects a specific notebook", () => {
    websocketService.connect(1)
    websocketService.connect(2)

    expect(MockWebSocket.instances).toHaveLength(2)

    websocketService.disconnect(1)

    expect(MockWebSocket.instances[0].closed).toBe(true)
    expect(MockWebSocket.instances[1].closed).toBe(false)
  })

  it("disconnects all notebooks", () => {
    websocketService.connect(1)
    websocketService.connect(2)
    websocketService.connect(3)

    websocketService.disconnectAll()

    for (const ws of MockWebSocket.instances) {
      expect(ws.closed).toBe(true)
    }
  })

  it("does not auto-reconnect after intentional disconnect", () => {
    websocketService.connect(1)
    const ws = MockWebSocket.instances[0]
    ws.simulateOpen()

    websocketService.disconnect(1)

    // Advance past reconnect delay
    vi.advanceTimersByTime(10000)

    // Should still only have the original connection
    expect(MockWebSocket.instances).toHaveLength(1)
  })

  it("schedules reconnect after unexpected close", () => {
    websocketService.connect(1)
    const ws = MockWebSocket.instances[0]
    ws.simulateOpen()

    // Simulate unexpected close (not via disconnect())
    ws.readyState = MockWebSocket.CLOSED
    if (ws.onclose) {
      ws.onclose(new CloseEvent("close"))
    }

    expect(MockWebSocket.instances).toHaveLength(1)

    // Advance past reconnect delay (5 seconds)
    vi.advanceTimersByTime(5000)

    // Should have created a new connection
    expect(MockWebSocket.instances).toHaveLength(2)
  })

  it("starts ping interval on connect", () => {
    websocketService.connect(1)
    const ws = MockWebSocket.instances[0]
    ws.simulateOpen()

    expect(ws.sent).toHaveLength(0)

    // Advance 30 seconds for first ping
    vi.advanceTimersByTime(30000)
    expect(ws.sent).toContain("ping")
  })

  it("handles errors in message handlers gracefully", () => {
    const errorSpy = vi.spyOn(console, "error").mockImplementation(() => {})
    const badHandler = vi.fn().mockImplementation(() => {
      throw new Error("handler error")
    })
    const goodHandler = vi.fn()

    websocketService.onFileChange(badHandler)
    websocketService.onFileChange(goodHandler)

    websocketService.connect(1)
    const ws = MockWebSocket.instances[0]
    ws.simulateOpen()

    ws.simulateMessage({
      type: "file_change",
      notebook_id: 1,
      event_type: "modified",
      path: "/test.md",
      timestamp: "2024-01-01T00:00:00Z",
    })

    // Bad handler threw, but good handler still called
    expect(badHandler).toHaveBeenCalled()
    expect(goodHandler).toHaveBeenCalled()
    expect(errorSpy).toHaveBeenCalled()

    errorSpy.mockRestore()
  })
})
