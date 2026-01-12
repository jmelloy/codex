/**
 * Form validation utilities
 */

export interface ValidationResult {
  valid: boolean
  error?: string
}

/**
 * Validate password requirements
 */
export function validatePassword(password: string): ValidationResult {
  if (password.length < 8) {
    return {
      valid: false,
      error: 'Password must be at least 8 characters'
    }
  }
  return { valid: true }
}

/**
 * Validate username requirements
 */
export function validateUsername(username: string): ValidationResult {
  if (username.length < 3) {
    return {
      valid: false,
      error: 'Username must be at least 3 characters'
    }
  }
  if (username.length > 50) {
    return {
      valid: false,
      error: 'Username must be at most 50 characters'
    }
  }
  return { valid: true }
}

/**
 * Validate that two passwords match
 */
export function validatePasswordsMatch(password: string, confirmPassword: string): ValidationResult {
  if (password !== confirmPassword) {
    return {
      valid: false,
      error: 'Passwords do not match'
    }
  }
  return { valid: true }
}

/**
 * Validate email format
 * Uses a pragmatic regex pattern that covers most common email formats.
 * Note: Perfect email validation according to RFC 5322 is extremely complex.
 * This regex balances validation strictness with maintainability.
 * For production, consider using a dedicated validation library like validator.js
 */
export function validateEmail(email: string): ValidationResult {
  // Pragmatic email regex that handles common cases including:
  // - Special chars in local part (.!#$%&'*+/=?^_`{|}~-)
  // - Multiple domain levels
  // - Hyphens in domain names
  const emailRegex = /^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$/
  if (!emailRegex.test(email)) {
    return {
      valid: false,
      error: 'Invalid email format'
    }
  }
  return { valid: true }
}
