import { describe, it, expect } from "vitest"
import {
  validatePassword,
  validateUsername,
  validatePasswordsMatch,
  validateEmail,
} from "../../utils/validation"

describe("validation utilities", () => {
  describe("validatePassword", () => {
    it.each([
      ["password123", true, undefined],
      ["12345678", true, undefined],
      ["pass", false, "Password must be at least 8 characters"],
    ])("validatePassword('%s') → valid=%s", (password, valid, error) => {
      const result = validatePassword(password)
      expect(result.valid).toBe(valid)
      expect(result.error).toBe(error)
    })
  })

  describe("validateUsername", () => {
    it.each([
      ["user123", true, undefined],
      ["abc", true, undefined],
      ["a".repeat(50), true, undefined],
      ["ab", false, "Username must be at least 3 characters"],
      ["a".repeat(51), false, "Username must be at most 50 characters"],
    ])("validateUsername('%s') → valid=%s", (username, valid, error) => {
      const result = validateUsername(username)
      expect(result.valid).toBe(valid)
      expect(result.error).toBe(error)
    })
  })

  describe("validatePasswordsMatch", () => {
    it.each([
      ["password123", "password123", true],
      ["", "", true],
      ["password123", "different", false],
    ])("validatePasswordsMatch('%s', '%s') → valid=%s", (a, b, valid) => {
      const result = validatePasswordsMatch(a, b)
      expect(result.valid).toBe(valid)
      if (!valid) expect(result.error).toBe("Passwords do not match")
    })
  })

  describe("validateEmail", () => {
    it.each([
      ["test@example.com", true],
      ["user.name@example.com", true],
      ["user+tag@example.co.uk", true],
      ["test123@subdomain.example.com", true],
    ])("accepts valid email '%s'", (email, valid) => {
      expect(validateEmail(email).valid).toBe(valid)
    })

    it.each([
      "notanemail",
      "@example.com",
      "test@",
      "test @example.com",
    ])("rejects invalid email '%s'", (email) => {
      const result = validateEmail(email)
      expect(result.valid).toBe(false)
      expect(result.error).toBe("Invalid email format")
    })
  })
})
