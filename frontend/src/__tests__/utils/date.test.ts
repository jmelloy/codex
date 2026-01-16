import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { formatRelativeDate } from '../../utils/date'

describe('date utilities', () => {
  beforeEach(() => {
    // Set a fixed date for testing
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2024-01-15T12:00:00Z'))
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  describe('formatRelativeDate', () => {
    it('should return "Today" for dates on the same day', () => {
      const today = new Date('2024-01-15T08:00:00Z')
      expect(formatRelativeDate(today)).toBe('Today')
    })

    it('should return "Yesterday" for dates 1 day ago', () => {
      const yesterday = new Date('2024-01-14T12:00:00Z')
      expect(formatRelativeDate(yesterday)).toBe('Yesterday')
    })

    it('should return "X days ago" for dates within the past week', () => {
      const twoDaysAgo = new Date('2024-01-13T12:00:00Z')
      expect(formatRelativeDate(twoDaysAgo)).toBe('2 days ago')

      const threeDaysAgo = new Date('2024-01-12T12:00:00Z')
      expect(formatRelativeDate(threeDaysAgo)).toBe('3 days ago')

      const sixDaysAgo = new Date('2024-01-09T12:00:00Z')
      expect(formatRelativeDate(sixDaysAgo)).toBe('6 days ago')
    })

    it('should return formatted date for dates 7 or more days ago', () => {
      const sevenDaysAgo = new Date('2024-01-08T12:00:00Z')
      const result = formatRelativeDate(sevenDaysAgo)
      // The exact format depends on locale, so just check it's not relative
      expect(result).not.toContain('days ago')
      expect(result).not.toBe('Today')
      expect(result).not.toBe('Yesterday')
    })

    it('should return formatted date for dates far in the past', () => {
      const longAgo = new Date('2023-01-01T12:00:00Z')
      const result = formatRelativeDate(longAgo)
      expect(result).not.toContain('days ago')
    })
  })
})
