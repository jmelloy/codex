import apiClient from "./api"

export interface Calendar {
  id: string
  summary: string
  description: string
  primary: boolean
  background_color: string | null
  foreground_color: string | null
  access_role: string | null
}

export interface CalendarEvent {
  id: string | null
  summary: string
  description: string
  location: string
  start: string | null
  end: string | null
  all_day: boolean
  status: string | null
  html_link: string | null
  creator: Record<string, string> | null
  organizer: Record<string, string> | null
  attendees: Array<{
    email?: string
    display_name?: string
    response_status?: string
    self?: boolean
  }>
  recurring_event_id: string | null
  color_id: string | null
  created: string | null
  updated: string | null
}

export interface EventListResponse {
  events: CalendarEvent[]
  calendar_id: string
}

export const calendarService = {
  async listCalendars(): Promise<Calendar[]> {
    const response = await apiClient.get<Calendar[]>("/api/v1/calendar/calendars")
    return response.data
  },

  async listEvents(params?: {
    calendar_id?: string
    time_min?: string
    time_max?: string
    max_results?: number
    q?: string
  }): Promise<EventListResponse> {
    const response = await apiClient.get<EventListResponse>("/api/v1/calendar/events", {
      params,
    })
    return response.data
  },

  async getEvent(eventId: string, calendarId?: string): Promise<CalendarEvent> {
    const response = await apiClient.get<CalendarEvent>(`/api/v1/calendar/events/${eventId}`, {
      params: calendarId ? { calendar_id: calendarId } : undefined,
    })
    return response.data
  },
}
