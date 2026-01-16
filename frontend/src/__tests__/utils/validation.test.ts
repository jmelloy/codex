import { describe, it, expect } from 'vitest'
import {
  validatePassword,
  validateUsername,
  validatePasswordsMatch,
  validateEmail
} from '../../utils/validation'

describe('validation utilities', () => {
  describe('validatePassword', () => {
    it('should accept passwords with 8 or more characters', () => {
      const result = validatePassword('password123')
      expect(result.valid).toBe(true)
      expect(result.error).toBeUndefined()
    })

    it('should reject passwords shorter than 8 characters', () => {
      const result = validatePassword('pass')
      expect(result.valid).toBe(false)
      expect(result.error).toBe('Password must be at least 8 characters')
    })

    it('should accept passwords with exactly 8 characters', () => {
      const result = validatePassword('12345678')
      expect(result.valid).toBe(true)
    })
  })

  describe('validateUsername', () => {
    it('should accept usernames with 3 or more characters', () => {
      const result = validateUsername('user123')
      expect(result.valid).toBe(true)
      expect(result.error).toBeUndefined()
    })

    it('should reject usernames shorter than 3 characters', () => {
      const result = validateUsername('ab')
      expect(result.valid).toBe(false)
      expect(result.error).toBe('Username must be at least 3 characters')
    })

    it('should reject usernames longer than 50 characters', () => {
      const result = validateUsername('a'.repeat(51))
      expect(result.valid).toBe(false)
      expect(result.error).toBe('Username must be at most 50 characters')
    })

    it('should accept usernames with exactly 3 characters', () => {
      const result = validateUsername('abc')
      expect(result.valid).toBe(true)
    })

    it('should accept usernames with exactly 50 characters', () => {
      const result = validateUsername('a'.repeat(50))
      expect(result.valid).toBe(true)
    })
  })

  describe('validatePasswordsMatch', () => {
    it('should accept matching passwords', () => {
      const result = validatePasswordsMatch('password123', 'password123')
      expect(result.valid).toBe(true)
      expect(result.error).toBeUndefined()
    })

    it('should reject non-matching passwords', () => {
      const result = validatePasswordsMatch('password123', 'different')
      expect(result.valid).toBe(false)
      expect(result.error).toBe('Passwords do not match')
    })

    it('should accept matching empty passwords', () => {
      const result = validatePasswordsMatch('', '')
      expect(result.valid).toBe(true)
    })
  })

  describe('validateEmail', () => {
    it('should accept valid email addresses', () => {
      const validEmails = [
        'test@example.com',
        'user.name@example.com',
        'user+tag@example.co.uk',
        'test123@subdomain.example.com'
      ]

      validEmails.forEach(email => {
        const result = validateEmail(email)
        expect(result.valid).toBe(true)
        expect(result.error).toBeUndefined()
      })
    })

    it('should reject invalid email addresses', () => {
      const invalidEmails = [
        'notanemail',
        '@example.com',
        'test@',
        'test @example.com'
      ]

      invalidEmails.forEach(email => {
        const result = validateEmail(email)
        expect(result.valid).toBe(false)
        expect(result.error).toBe('Invalid email format')
      })
    })
  })
})
