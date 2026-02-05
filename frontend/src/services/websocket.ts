/**
 * WebSocket service for real-time file change notifications.
 */

export interface FileChangeEvent {
  type: "file_change"
  notebook_id: number
  event_type: "created" | "modified" | "deleted" | "moved" | "scanned"
  path: string
  old_path?: string
  timestamp: string
}

export interface ConnectionEvent {
  type: "connected"
  notebook_id: number
  message: string
}

export type WebSocketMessage = FileChangeEvent | ConnectionEvent

type MessageHandler = (event: FileChangeEvent) => void
type ConnectionHandler = (connected: boolean, notebookId: number) => void

class WebSocketService {
  private connections: Map<number, WebSocket> = new Map()
  private messageHandlers: Set<MessageHandler> = new Set()
  private connectionHandlers: Set<ConnectionHandler> = new Set()
  private reconnectTimers: Map<number, number> = new Map()
  private pingIntervals: Map<number, number> = new Map()
  private intentionallyDisconnected: Set<number> = new Set()

  /**
   * Get the WebSocket URL for a notebook.
   */
  private getWebSocketUrl(notebookId: number): string {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:"
    const host = window.location.host
    return `${protocol}//${host}/api/v1/ws/notebooks/${notebookId}`
  }

  /**
   * Connect to WebSocket for a notebook.
   */
  connect(notebookId: number): void {
    // Clear intentional disconnect flag
    this.intentionallyDisconnected.delete(notebookId)

    // Already connected
    if (this.connections.has(notebookId)) {
      return
    }

    const url = this.getWebSocketUrl(notebookId)
    const ws = new WebSocket(url)

    ws.onopen = () => {
      console.log(`WebSocket connected for notebook ${notebookId}`)
      this.notifyConnectionHandlers(true, notebookId)

      // Start ping interval to keep connection alive
      const pingInterval = window.setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send("ping")
        }
      }, 30000)
      this.pingIntervals.set(notebookId, pingInterval)
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as WebSocketMessage

        if (data.type === "file_change") {
          this.notifyMessageHandlers(data)
        }
      } catch (e) {
        // Ignore non-JSON messages (like "pong")
        if (event.data !== "pong") {
          console.warn("Failed to parse WebSocket message:", e)
        }
      }
    }

    ws.onclose = () => {
      console.log(`WebSocket disconnected for notebook ${notebookId}`)
      this.cleanup(notebookId)
      this.notifyConnectionHandlers(false, notebookId)

      // Schedule reconnect
      this.scheduleReconnect(notebookId)
    }

    ws.onerror = (error) => {
      console.error(`WebSocket error for notebook ${notebookId}:`, error)
    }

    this.connections.set(notebookId, ws)
  }

  /**
   * Disconnect from WebSocket for a notebook.
   */
  disconnect(notebookId: number): void {
    // Mark as intentionally disconnected to prevent auto-reconnect
    this.intentionallyDisconnected.add(notebookId)

    // Cancel any pending reconnect
    const timer = this.reconnectTimers.get(notebookId)
    if (timer) {
      window.clearTimeout(timer)
      this.reconnectTimers.delete(notebookId)
    }

    const ws = this.connections.get(notebookId)
    if (ws) {
      ws.close()
      this.cleanup(notebookId)
    }
  }

  /**
   * Disconnect all WebSocket connections.
   */
  disconnectAll(): void {
    // Copy keys since disconnect modifies the map
    const notebookIds = [...this.connections.keys()]
    for (const notebookId of notebookIds) {
      this.disconnect(notebookId)
    }
  }

  /**
   * Register a handler for file change events.
   */
  onFileChange(handler: MessageHandler): () => void {
    this.messageHandlers.add(handler)
    return () => {
      this.messageHandlers.delete(handler)
    }
  }

  /**
   * Register a handler for connection state changes.
   */
  onConnectionChange(handler: ConnectionHandler): () => void {
    this.connectionHandlers.add(handler)
    return () => {
      this.connectionHandlers.delete(handler)
    }
  }

  /**
   * Check if connected to a notebook.
   */
  isConnected(notebookId: number): boolean {
    const ws = this.connections.get(notebookId)
    return ws?.readyState === WebSocket.OPEN
  }

  private cleanup(notebookId: number): void {
    this.connections.delete(notebookId)

    const pingInterval = this.pingIntervals.get(notebookId)
    if (pingInterval) {
      window.clearInterval(pingInterval)
      this.pingIntervals.delete(notebookId)
    }
  }

  private scheduleReconnect(notebookId: number): void {
    // Don't reconnect if intentionally disconnected
    if (this.intentionallyDisconnected.has(notebookId)) {
      return
    }

    // Reconnect after 5 seconds
    const timer = window.setTimeout(() => {
      this.reconnectTimers.delete(notebookId)
      // Only reconnect if not intentionally disconnected
      if (!this.intentionallyDisconnected.has(notebookId)) {
        console.log(`Reconnecting WebSocket for notebook ${notebookId}`)
        this.connect(notebookId)
      }
    }, 5000)

    this.reconnectTimers.set(notebookId, timer)
  }

  private notifyMessageHandlers(event: FileChangeEvent): void {
    for (const handler of this.messageHandlers) {
      try {
        handler(event)
      } catch (e) {
        console.error("Error in WebSocket message handler:", e)
      }
    }
  }

  private notifyConnectionHandlers(connected: boolean, notebookId: number): void {
    for (const handler of this.connectionHandlers) {
      try {
        handler(connected, notebookId)
      } catch (e) {
        console.error("Error in WebSocket connection handler:", e)
      }
    }
  }
}

// Export singleton instance
export const websocketService = new WebSocketService()
