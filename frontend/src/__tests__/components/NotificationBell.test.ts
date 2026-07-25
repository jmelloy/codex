import { describe, it, expect, beforeEach, vi, type Mock } from "vitest"
import { mount } from "@vue/test-utils"
import { setActivePinia, createPinia } from "pinia"
import NotificationBell from "../../components/NotificationBell.vue"
import { notificationService } from "../../services/notifications"
import { websocketService } from "../../services/websocket"

vi.mock("../../services/notifications", () => ({
  notificationService: {
    list: vi.fn(() => Promise.resolve([])),
    unreadCount: vi.fn(() => Promise.resolve(0)),
    markRead: vi.fn(),
    markAllRead: vi.fn(),
  },
}))

vi.mock("../../services/websocket", () => ({
  websocketService: { onNotification: vi.fn(() => vi.fn()) },
}))

const mockOnNotification = websocketService.onNotification as Mock

describe("NotificationBell", () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    ;(notificationService.list as Mock).mockResolvedValue([])
    ;(notificationService.unreadCount as Mock).mockResolvedValue(0)
    mockOnNotification.mockImplementation(() => vi.fn())
  })

  it("subscribes to the notification WebSocket channel on mount", async () => {
    const wrapper = mount(NotificationBell)
    await wrapper.vm.$nextTick()

    expect(mockOnNotification).toHaveBeenCalledTimes(1)
    wrapper.unmount()
  })

  it("tears down the WebSocket subscription on unmount, so remounting re-subscribes", async () => {
    const unsubscribe = vi.fn()
    mockOnNotification.mockImplementation(() => unsubscribe)

    const wrapper = mount(NotificationBell)
    await wrapper.vm.$nextTick()
    wrapper.unmount()

    expect(unsubscribe).toHaveBeenCalledTimes(1)

    const wrapper2 = mount(NotificationBell)
    await wrapper2.vm.$nextTick()

    expect(mockOnNotification).toHaveBeenCalledTimes(2)
    wrapper2.unmount()
  })
})
