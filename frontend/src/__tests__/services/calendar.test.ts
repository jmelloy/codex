import { describe, it, expect, beforeEach, vi, type Mock } from "vitest"
import apiClient from "../../services/api"
import { calendarService } from "../../services/calendar"

vi.mock("../../services/api", () => ({
  default: {
    get: vi.fn(),
  },
}))

const mockGet = apiClient.get as Mock

const mockCalendars = [
  {
    id: "primary",
    summary: "My Calendar",
    description: "Primary calendar",
    primary: true,
    background_color: "#4285f4",
    foreground_color: "#ffffff",
    access_role: "owner",
  },
  {
    id: "work",
    summary: "Work Calendar",
    description: "Work events",
    primary: false,
    background_color: "#0b8043",
    foreground_color: "#ffffff",
    access_role: "reader",
  },
]

const mockEvents = {
  events: [
    {
      id: "evt1",
      summary: "Team Meeting",
      description: "Weekly standup",
      location: "Room 101",
      start: "2024-01-15T10:00:00Z",
      end: "2024-01-15T11:00:00Z",
      all_day: false,
      status: "confirmed",
      html_link: "https://calendar.google.com/event/evt1",
      creator: { email: "alice@example.com" },
      organizer: { email: "alice@example.com" },
      attendees: [
        { email: "bob@example.com", display_name: "Bob", response_status: "accepted", self: false },
      ],
      recurring_event_id: null,
      color_id: null,
      created: "2024-01-01T00:00:00Z",
      updated: "2024-01-10T00:00:00Z",
    },
  ],
  calendar_id: "primary",
}

describe("Calendar Service", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe("listCalendars", () => {
    it("fetches calendar list", async () => {
      mockGet.mockResolvedValue({ data: mockCalendars })

      const result = await calendarService.listCalendars()

      expect(result).toEqual(mockCalendars)
      expect(mockGet).toHaveBeenCalledWith("/api/v1/calendar/calendars")
    })
  })

  describe("listEvents", () => {
    it("fetches events without params", async () => {
      mockGet.mockResolvedValue({ data: mockEvents })

      const result = await calendarService.listEvents()

      expect(result).toEqual(mockEvents)
      expect(mockGet).toHaveBeenCalledWith("/api/v1/calendar/events", { params: undefined })
    })

    it("fetches events with all params", async () => {
      mockGet.mockResolvedValue({ data: mockEvents })

      const params = {
        calendar_id: "primary",
        time_min: "2024-01-01T00:00:00Z",
        time_max: "2024-01-31T23:59:59Z",
        max_results: 50,
        q: "meeting",
      }

      const result = await calendarService.listEvents(params)

      expect(result).toEqual(mockEvents)
      expect(mockGet).toHaveBeenCalledWith("/api/v1/calendar/events", { params })
    })

    it("fetches events with partial params", async () => {
      mockGet.mockResolvedValue({ data: mockEvents })

      const params = { calendar_id: "work", max_results: 10 }

      await calendarService.listEvents(params)

      expect(mockGet).toHaveBeenCalledWith("/api/v1/calendar/events", { params })
    })
  })

  describe("getEvent", () => {
    it("fetches a single event without calendar id", async () => {
      const event = mockEvents.events[0]
      mockGet.mockResolvedValue({ data: event })

      const result = await calendarService.getEvent("evt1")

      expect(result).toEqual(event)
      expect(mockGet).toHaveBeenCalledWith("/api/v1/calendar/events/evt1", {
        params: undefined,
      })
    })

    it("fetches a single event with calendar id", async () => {
      const event = mockEvents.events[0]
      mockGet.mockResolvedValue({ data: event })

      const result = await calendarService.getEvent("evt1", "primary")

      expect(result).toEqual(event)
      expect(mockGet).toHaveBeenCalledWith("/api/v1/calendar/events/evt1", {
        params: { calendar_id: "primary" },
      })
    })
  })
})
